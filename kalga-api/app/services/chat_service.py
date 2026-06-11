"""
Service de chat
Orchestre le flux de conversation entre clients et marchands
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any, Tuple

from ..database.repositories import MerchantRepository, ProductRepository, ConversationRepository
from ..database.repositories.stats_repo import get_stats_repository
from ..database.repositories.client_history_repo import get_client_history_repository
from ..database.repositories.knowledge_repo import KnowledgeBaseRepository
from ..database.repositories.waitlist_repo import get_waitlist_repository
from ..models.schemas import IncomingMessage, BotResponse
from .notification_service import NotificationService
from .followup_service import get_followup_service
from .conversation_ai import generate_response, extract_product_code, analyze_conversation_health
from .ai.conversation_ai import is_tool_call, parse_tool_call
from .ai.memory import ltm as ltm_module
from .ai.deepseek_client import get_deepseek_client
from .ai.detectors import detect_other_products_request, detect_same_variant_photo_request
from .ai.debug_tracer import DebugTracer

logger = logging.getLogger("kalga.chat")


class ChatService:
    """
    Service qui orchestre le flux de chat.
    Sépare la logique métier de la couche HTTP.
    """

    def __init__(
        self,
        merchant_repo: MerchantRepository = None,
        product_repo: ProductRepository = None,
        conversation_repo: ConversationRepository = None,
        notification_service: NotificationService = None
    ):
        self.merchants = merchant_repo or MerchantRepository()
        self.products = product_repo or ProductRepository()
        self.conversations = conversation_repo or ConversationRepository()
        self.notifications = notification_service or NotificationService()
        self.stats = get_stats_repository()
        self.followups = get_followup_service()
        self.client_history = get_client_history_repository()
        self.waitlist = get_waitlist_repository()

    async def handle_incoming_message(self, message: IncomingMessage, tracer: Optional[DebugTracer] = None) -> BotResponse:
        """
        Traite un message entrant depuis WhatsApp.
        Point d'entrée principal du flux de chat.
        """
        logger.info(f"=== MESSAGE ENTRANT ===")
        logger.info(f"Marchand: {message.merchant_phone} | Client: {message.client_phone}")
        logger.info(f"Message: {message.message[:80]}...")
        if tracer:
            tracer.event("CHAT", "message_received",
                merchant_phone=message.merchant_phone,
                client_phone=message.client_phone,
                message_len=len(message.message),
                product_code=message.product_code
            )

        # 1. Identifier le marchand
        merchant = await self.merchants.get_by_phone(message.merchant_phone)
        if not merchant:
            # Fallback: numéro ivoirien sans le 0 (225XXXXXXXXX → 2250XXXXXXXXX)
            phone = message.merchant_phone
            if phone.startswith('225') and len(phone) == 12:
                corrected = '225' + '0' + phone[3:]
                merchant = await self.merchants.get_by_phone(corrected)
                if merchant:
                    logger.info(f"Marchand trouvé avec numéro corrigé: {corrected}")
        if not merchant:
            logger.error(f"Marchand {message.merchant_phone} non trouvé!")
            return BotResponse(
                message="",
                conversation_id=0,
                should_notify_merchant=False,
                no_response=True
            )

        # 1.5 Vérifier si le marchand est disponible (mode absence)
        is_available, away_message = await self.merchants.is_merchant_available(merchant['id'])
        if not is_available:
            logger.info(f"Marchand {message.merchant_phone} indisponible - Mode absence actif")
            return BotResponse(
                message=away_message,
                conversation_id=0,
                should_notify_merchant=False,
                away_mode=True
            )

        # 2. Trouver ou créer la conversation
        conversation, product = await self._get_or_create_conversation(
            merchant=merchant,
            client_phone=message.client_phone,
            message_text=message.message,
            product_code=message.product_code
        )

        if not conversation:
            # Pas de conversation active et pas de code produit
            logger.info(f"Pas de conversation active pour {message.client_phone}")
            return BotResponse(
                message="",
                conversation_id=0,
                should_notify_merchant=False,
                no_response=True
            )

        # 3. Enregistrer le message du client
        await self.conversations.add_message(
            conversation_id=conversation['id'],
            content=message.message,
            is_from_client=True
        )

        # 3.5 Enregistrer les stats
        try:
            await self.stats.increment_messages(merchant['id'], 1)
        except Exception as e:
            logger.warning(f"Erreur stats messages: {e}")

        # 4. Vérifier le stock (pour les nouvelles conversations)
        is_first_message = len(await self.conversations.get_messages(conversation['id'])) <= 1
        if is_first_message:
            stock_status = await self.products.check_stock_status(product['id'])
            if stock_status and stock_status.get('is_out_of_stock'):
                # Vérifier le mode rupture du produit
                out_mode = product.get('out_of_stock_mode', 'waitlist')

                if out_mode == 'waitlist':
                    waitlist_count = await self.waitlist.get_waitlist_count(product['id'])
                    already_in = await self.waitlist.is_client_in_waitlist(
                        product['id'], message.client_phone
                    )
                    if already_in:
                        bot_message = (
                            f"😊 Le *{product['name']}* est toujours en rupture de stock, "
                            f"mais tu es déjà sur la liste d'attente ! "
                            f"Je te préviens dès qu'il revient."
                        )
                    else:
                        queue_text = (
                            f" ({waitlist_count} client{'s' if waitlist_count > 1 else ''} avant toi)"
                            if waitlist_count > 0 else ""
                        )
                        bot_message = (
                            f"😕 Le *{product['name']}* est momentanément épuisé.\n\n"
                            f"Souhaites-tu être notifié dès qu'il sera disponible ?{queue_text}\n\n"
                            f"Réponds *OUI* pour rejoindre la liste prioritaire 🔔"
                        )
                    await self.conversations.add_message(conversation['id'], bot_message, False)
                    # Enregistrer l'événement analytics
                    try:
                        await self.stats.log_event(
                            merchant_id=merchant['id'],
                            event_type='out_of_stock_inquiry',
                            product_id=product['id'],
                            conversation_id=conversation['id'],
                            client_phone=message.client_phone
                        )
                    except Exception:
                        pass
                    return BotResponse(
                        message=bot_message,
                        conversation_id=conversation['id'],
                        should_notify_merchant=True,
                        notification_reason=f"Client intéressé par {product['code']} (RUPTURE)"
                    )
                else:
                    # Mode suspend ou autre : message simple
                    bot_message = (
                        f"Désolé, le {product['name']} est actuellement en rupture de stock. "
                        f"Je te contacte dès qu'il est de nouveau disponible!"
                    )
                    await self.conversations.add_message(conversation['id'], bot_message, False)
                    return BotResponse(
                        message=bot_message,
                        conversation_id=conversation['id'],
                        should_notify_merchant=True,
                        notification_reason=f"Client intéressé par {product['code']} (RUPTURE)"
                    )

        # 4.1 Détecter la réponse OUI à la waitlist
        if not is_first_message:
            waitlist_response = await self._check_waitlist_reply(
                message=message,
                conversation=conversation,
                product=product,
                merchant=merchant
            )
            if waitlist_response:
                return waitlist_response

        # 4.5 Mémoriser la variante sélectionnée si le client répond à une photo de variante
        # Doit être fait AVANT les cas spéciaux pour que selected_variant_id soit à jour
        current_conv_status = conversation.get('status', 'active')
        if current_conv_status not in ('pending_pickup', 'pending_delivery'):
            await self._find_and_save_selected_variant(
                conversation=conversation,
                product=product,
                message_text=message.message
            )

        # 5. Vérifier les cas spéciaux (photos, variantes)
        # Ne pas intercepter en pending_pickup/pending_delivery (le client parle au bot de suivi)
        if current_conv_status not in ('pending_pickup', 'pending_delivery'):
            special_response = await self._handle_special_requests(
                message=message,
                conversation=conversation,
                product=product
            )
            if special_response:
                return special_response

        # 6. Générer la réponse IA (avec contexte de négociation)
        history = await self.conversations.get_messages(conversation['id'])
        current_status = conversation.get('status', 'active')

        # Récupérer le contexte de négociation basé sur l'historique client
        negotiation_context = await self._get_negotiation_context(
            merchant_id=merchant['id'],
            client_phone=message.client_phone,
            product=product
        )

        if tracer:
            tracer.event("CHAT", "ai_generate_start",
                conversation_status=current_status,
                history_len=len(history),
                has_negotiation_context=bool(negotiation_context)
            )

        # === MOTEUR V2 (drapeau DIALOGUE_ENGINE) — spec refonte 2026-06-11 ===
        # v2 remplace UNIQUEMENT le cerveau+voix ; tout l'aval (persistance,
        # notifications, localisation, goodbye, relances) reste le chemin commun.
        # Défensif : v2 → None ⇒ v1 reprend la main, rien ne casse.
        engine_v2 = None
        from ..core.config import settings as _settings
        if _settings.dialogue_engine == "v2":
            from .dialogue.engine import respond as dialogue_respond

            # Geste fidélité (logique v1 portée) : client connu → plancher abaissé
            v2_floor = None
            if (negotiation_context and negotiation_context.get('loyalty_discount', 0) > 0
                    and negotiation_context.get('is_returning')):
                base_min = product.get('effective_min_price') or product['min_price']
                price_range = product['price'] - base_min
                v2_floor = max(
                    base_min - price_range * (negotiation_context['loyalty_discount'] / 100),
                    base_min * 0.95,
                )
                logger.info(f"Client fidèle (v2): plancher ajusté à {v2_floor:,.0f} F")

            # Mémoire long-terme : les faits connus du client personnalisent la voix
            v2_memory = None
            try:
                facts = await self.client_history.get_memory_facts(
                    merchant['id'], message.client_phone) or []
                fact_lines = [f["fact"] for f in facts[:3] if f.get("fact")]
                if fact_lines:
                    v2_memory = "Ce qu'on sait du client : " + " ; ".join(fact_lines)
            except Exception as e:
                logger.debug(f"LTM v2 indisponible (non bloquant): {e}")

            engine_v2 = await dialogue_respond(
                client_message=message.message,
                conversation=conversation,
                product=product,
                merchant=merchant,
                history=history,
                floor_override=v2_floor,
                memory_extra=v2_memory,
            )
            if tracer:
                tracer.event("CHAT", "dialogue_v2",
                             used=engine_v2 is not None,
                             facts=engine_v2.facts if engine_v2 else None)

        images_v2 = None
        human_takeover_v2 = False
        if engine_v2 is not None:
            bot_response = engine_v2.message
            price_offer = engine_v2.new_offer
            new_status = engine_v2.new_status
            send_location = engine_v2.send_location
            use_voice = False
            deal_accepted = new_status in ("agreed", "pending_delivery", "pending_pickup")
            images_v2 = engine_v2.images_to_send
            human_takeover_v2 = engine_v2.human_takeover

            # Prise de main du marchand — notifications explicites du moteur v2.
            # (Le passage en pending_* est déjà couvert par _handle_notifications ;
            # ici : l'adresse collectée = vente bouclée, le marchand prend le relais.)
            if engine_v2.notify_reason == "delivery_address":
                await self.notifications.notify_sale(
                    merchant_phone=message.merchant_phone,
                    product_name=product['name'],
                    price=engine_v2.new_offer or conversation.get('current_offer') or product['price'],
                    client_phone=message.client_phone,
                    product_code=product.get('code', ''),
                    delivery_type="delivery",
                    client_name=message.client_name or "",
                    delivery_address=engine_v2.delivery_address or "",
                )
            elif engine_v2.notify_reason == "human_request":
                await self.notifications.send_message(
                    merchant_phone=message.merchant_phone,
                    to=message.merchant_phone,
                    message=(f"\U0001f64b *Le client {message.client_phone} demande à te parler "
                             f"directement* ({product['name']}). Prends le relais !"),
                )
        else:
            bot_response, price_offer, deal_accepted, new_status, send_location, use_voice = await generate_response(
                client_message=message.message,
                product=product,
                conversation_history=history,
                current_offer=conversation.get('current_offer'),
                conversation_status=current_status,
                negotiation_context=negotiation_context,
                merchant_data=merchant,
                tracer=tracer,
                client_phone=message.client_phone
            )

        logger.info(f"Réponse IA: {bot_response[:80] if bot_response else 'NONE'}... | Status: {new_status} | Location: {send_location}")
        if tracer:
            tracer.event("CHAT", "ai_generate_done",
                new_status=new_status,
                send_location=send_location,
                response_len=len(bot_response) if bot_response else 0
            )

        # 6.1 Dispatcher le tool_call si DeepSeek a choisi une action (chemin v1 uniquement)
        images_to_send = images_v2
        if engine_v2 is None and bot_response and is_tool_call(bot_response):
            tool = parse_tool_call(bot_response)
            if tool:
                bot_response, new_status, send_location, images_to_send = await self._execute_tool(
                    tool=tool,
                    conversation=conversation,
                    product=product,
                    merchant=merchant,
                    current_status=current_status,
                    current_offer=conversation.get('current_offer'),
                    min_price=product.get('effective_min_price', product['min_price']),
                    tracer=tracer
                )
                # LTM: lancer extraction + tracer après tool call si conversation terminée
                if new_status in ("pending_pickup", "pending_delivery", "ended", "agreed") or send_location:
                    try:
                        asyncio.create_task(ltm_module.extract_and_save(
                            repo=self.client_history,
                            merchant_id=merchant['id'],
                            client_phone=message.client_phone,
                            history=history,
                            product=product,
                            outcome="ended",
                            deepseek_client=get_deepseek_client()
                        ))
                        if tracer:
                            existing_facts = await self.client_history.get_memory_facts(
                                merchant['id'], message.client_phone) or []
                            existing_prefs = await self.client_history.get_preferences(
                                merchant['id'], message.client_phone)
                            tracer.set_ltm(facts=existing_facts, preferences=existing_prefs)
                            tracer.event("MEMORY", "ltm_extraction_scheduled",
                                history_len=len(history) if history else 0)
                    except Exception as e:
                        logger.debug(f"LTM post-tool scheduling skipped: {e}")

        # 6. Mettre à jour la conversation
        update_data = {"status": new_status}
        if price_offer:
            update_data["current_offer"] = price_offer
        await self.conversations.update(conversation['id'], **update_data)

        # Si pas de réponse (conversation terminée)
        if bot_response is None:
            return BotResponse(
                message="",
                conversation_id=conversation['id'],
                should_notify_merchant=False,
                no_response=True
            )

        # Enregistrer la réponse du bot
        await self.conversations.add_message(
            conversation_id=conversation['id'],
            content=bot_response,
            is_from_client=False
        )

        # 6.5 Boucle d'apprentissage — auto-flag des questions sans réponse
        if not is_first_message:
            await self._auto_flag_unanswered(
                conversation_id=conversation['id'],
                merchant_id=merchant['id'],
                client_phone=message.client_phone,
                client_message=message.message,
                bot_response=bot_response,
                history=history,
                product=product
            )

        # 7. Gérer les notifications au marchand
        should_notify, notification = await self._handle_notifications(
            message=message,
            merchant=merchant,
            product=product,
            conversation=conversation,
            current_status=current_status,
            new_status=new_status,
            price_offer=price_offer
        )

        # 7.5 Préparer la localisation si demandée (envoi délégué au bridge, APRÈS le texte)
        # Double-check: si on est en pending_pickup et le message parle de localisation, forcer l'envoi
        if not send_location and new_status == "pending_pickup":
            from ..services.ai.detectors import detect_location_request
            if detect_location_request(message.message):
                send_location = True
                logger.info(f"[LOCATION] Force send_location=True via double-check pour pending_pickup")

        # Construire les données de localisation à passer au bridge
        merchant_location = None
        human_takeover = human_takeover_v2
        if send_location:
            latitude = merchant.get('latitude')
            longitude = merchant.get('longitude')
            address = merchant.get('address', '')
            logger.info(f"[LOCATION] Données préparées pour le bridge: lat={latitude}, lng={longitude}, addr={address}")
            if latitude and longitude:
                name = merchant.get('business_name') or merchant.get('name') or 'Ma boutique'
                merchant_location = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "name": name,
                    "address": address
                }
            elif address:
                merchant_location = {"address": address}
            else:
                logger.warning(f"[LOCATION] Aucune donnée de localisation disponible pour {message.merchant_phone}")
                send_location = False
                # Localisation demandée mais non configurée → human takeover
                human_takeover = True

        # 7.6 Préparer le message de fin de transaction (sera envoyé par le bridge APRÈS la réponse principale)
        is_transaction_end = (
            (new_status in ("pending_delivery", "pending_pickup") and current_status not in ("pending_delivery", "pending_pickup"))
        )
        goodbye_message = None
        if is_transaction_end:
            # Construire le goodbye inline (le bridge l'envoie en dernier, après le texte + localisation)
            from ..config import settings
            store_name = merchant.get('business_name') or merchant.get('name') or 'notre boutique'
            if 'localhost' in settings.storefront_base_url or '127.0.0.1' in settings.storefront_base_url:
                goodbye_message = (
                    f"\U0001f64f Merci pour ton achat chez {store_name} !\n"
                    f"N'hesite pas a revenir \U0001f60a"
                )
            else:
                storefront_url = f"{settings.storefront_base_url}/boutique/boutique.html?m={message.merchant_phone}"
                goodbye_message = (
                    f"\U0001f64f Merci pour ton achat !\n"
                    f"\U0001f6cd\ufe0f Decouvre tous les produits de {store_name} ici :\n"
                    f"\U0001f449 {storefront_url}"
                )

            # Boucle d'apprentissage — auto-sauvegarder l'échange final en KB
            await self._auto_learn_from_deal(
                merchant_id=merchant['id'],
                client_message=message.message,
                bot_response=bot_response
            )

        # 8. Gérer les relances automatiques
        await self._handle_follow_ups(
            conversation=conversation,
            merchant=merchant,
            product=product,
            message=message,
            new_status=new_status
        )

        # 9. TTS — générer le vocal si use_voice demandé par l'IA
        audio_base64 = None
        if use_voice and bot_response:
            try:
                import base64
                from .tts_service import text_to_ogg
                # Détecter la langue depuis le message client ou utiliser 'fr' par défaut
                lang = "fr"
                if message.message and "[🎤 Vocal transcrit" in message.message:
                    import re as _re
                    m = _re.search(r"\[🎤 Vocal transcrit \((\w+)\)\]", message.message)
                    if m:
                        lang = m.group(1)
                ogg_bytes = await text_to_ogg(bot_response, lang=lang)
                if ogg_bytes:
                    audio_base64 = base64.b64encode(ogg_bytes).decode("utf-8")
                    logger.info(f"TTS vocal généré: {len(ogg_bytes)} bytes OGG (lang={lang})")
                else:
                    logger.warning("TTS: génération OGG échouée — réponse texte envoyée")
            except Exception as e:
                logger.error(f"Erreur TTS dans chat_service: {e}")

        return BotResponse(
            message=bot_response,
            conversation_id=conversation['id'],
            should_notify_merchant=should_notify,
            notification_reason=notification,
            send_location=send_location,
            merchant_location=merchant_location,
            goodbye_message=goodbye_message,
            human_takeover=human_takeover,
            images_to_send=images_to_send,
            audio_base64=audio_base64,
        )

    async def _get_or_create_conversation(
        self,
        merchant: Dict,
        client_phone: str,
        message_text: str,
        product_code: str = None
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Récupère ou crée une conversation.
        Retourne (conversation, product) ou (None, None) si pas de contexte.
        """
        # Extraire le code produit si pas fourni
        code_from_text = extract_product_code(message_text)
        code = product_code or code_from_text
        logger.info(f"Code produit: {code}")

        product = None
        conversation = None

        if code:
            # Nouveau produit mentionné
            product = await self.products.get_by_code(code)
            if product and product['merchant_id'] == merchant['id']:
                # Chercher conversation existante
                conversation = await self.conversations.get_active(
                    merchant['id'],
                    client_phone,
                    product['id']
                )

                # Si la conversation existante est en pending_pickup/pending_delivery ET
                # que le code vient du texte du message (pas d'un paramètre explicite),
                # le client mentionne explicitement le produit = nouvelle intention d'achat.
                # Fermer l'ancienne et en créer une nouvelle.
                if (conversation and conversation.get('status') in ('pending_pickup', 'pending_delivery')
                        and code_from_text):
                    logger.info(f"Conversation {conversation['id']} en {conversation['status']}, "
                                f"client renvoie #code dans le texte => fermer et créer nouvelle conversation")
                    await self.conversations.update(conversation['id'], status='completed')
                    conversation = None

                if not conversation:
                    conversation = await self.conversations.create(
                        merchant_id=merchant['id'],
                        product_id=product['id'],
                        client_phone=client_phone
                    )
                    logger.info(f"Nouvelle conversation créée: {conversation['id']}")

                    # Enregistrer les stats pour nouvelle conversation
                    try:
                        await self.stats.increment_conversations(merchant['id'])
                        await self.stats.log_event(
                            merchant_id=merchant['id'],
                            event_type='new_conversation',
                            product_id=product['id'],
                            conversation_id=conversation['id'],
                            client_phone=client_phone
                        )
                    except Exception as e:
                        logger.warning(f"Erreur stats conversation: {e}")
        else:
            # Pas de code - chercher conversation existante
            conversation = await self.conversations.get_active(
                merchant['id'],
                client_phone
            )
            if not conversation:
                # Client qui revient après une clôture récente : ré-ouvrir son
                # contexte (photos, SAV, nouvelle négo) au lieu du silence.
                conversation = await self.conversations.get_recent_closed(
                    merchant['id'], client_phone
                )
                if conversation:
                    logger.info(
                        f"Conversation {conversation['id']} ré-ouverte "
                        f"(retour client après clôture)"
                    )
            if conversation:
                product = await self.products.get_by_id(conversation['product_id'])

        return conversation, product

    async def _handle_special_requests(
        self,
        message: IncomingMessage,
        conversation: Dict,
        product: Dict
    ) -> Optional[BotResponse]:
        """
        Gère uniquement les demandes de catalogue (autres produits du marchand).
        Les photos, variantes, localisation sont désormais gérées par DeepSeek agentique
        via _execute_tool().
        """
        import re

        raw_text = re.sub(r'^\[Répond à[^\]]*\]\s*', '', message.message)

        # === AUTRES PRODUITS DU MARCHAND (catalogue multi-produits) ===
        # Cas déterministe : le client veut voir d'autres produits (pas des variantes du même)
        if detect_other_products_request(raw_text):
            merchant_obj = await self.merchants.get_by_phone(message.merchant_phone)
            if merchant_obj:
                all_products = await self.products.get_by_merchant(merchant_obj['id'])
                other_products = [p for p in all_products if p['id'] != product['id']]

                if other_products:
                    product_lines = []
                    for p in other_products[:5]:
                        price_str = f"{p['price']:,.0f}".replace(",", " ")
                        product_lines.append(f"• {p['name']} — {price_str} F ({p['code']})")
                    products_text = "\n".join(product_lines)
                    bot_message = f"Oui, on a aussi d'autres articles:\n\n{products_text}\n\nLequel t'intéresse?"
                else:
                    bot_message = f"Pour l'instant c'est surtout le {product['name']} qu'on a en stock. Si tu veux je te le réserve?"

                await self.conversations.add_message(conversation['id'], bot_message, False)
                return BotResponse(
                    message=bot_message,
                    conversation_id=conversation['id'],
                    should_notify_merchant=False
                )

        return None

    async def _execute_tool(
        self,
        tool: Dict,
        conversation: Dict,
        product: Dict,
        merchant: Dict,
        current_status: str,
        current_offer: Optional[float],
        min_price: float,
        tracer=None
    ):
        """
        Exécute l'action décidée par DeepSeek (function calling).

        Retourne (bot_response, new_status, send_location, images_to_send).
        """
        name = tool["name"]
        args = tool.get("args", {})
        message_text = args.get("message", "")
        send_location = False
        images_to_send = None
        new_status = current_status

        # ── send_photo : photo du produit actuel ou de la variante sélectionnée ──
        if name == "send_photo":
            selected_variant_id = conversation.get('selected_variant_id')
            target = None
            if selected_variant_id:
                target = await self.products.get_by_id(selected_variant_id)

            if target and target.get('image_path'):
                variant_label = target.get('variant_name') or target['name']
                images_to_send = [{"image_path": target['image_path'], "caption": f"Modèle {variant_label}"}]
                bot_response = message_text or f"Voici la photo du modèle {variant_label}!"
            elif product.get('image_path'):
                images_to_send = [{"image_path": product['image_path'],
                                   "caption": f"{product['name']} - {product['code']} - {product['price']:,.0f} F"}]
                bot_response = message_text or f"Voici le {product['name']}!"
            else:
                bot_response = "Désolé, je n'ai pas de photo pour ce produit. Passe au magasin pour le voir!"

        # ── send_variants : toutes les autres variantes du groupe ──
        elif name == "send_variants":
            group_id = product.get('group_id')
            if group_id:
                variants = await self.products.get_other_variants(product['id'], group_id)
                if variants:
                    seen_names = set()
                    unique_variants = []
                    for v in variants:
                        label = (v.get('variant_name') or v['name']).strip().lower()
                        if label not in seen_names:
                            seen_names.add(label)
                            unique_variants.append(v)

                    images_to_send = []
                    variant_names = []
                    for v in unique_variants:
                        variant_label = v.get('variant_name') or v['name']
                        if v.get('image_path'):
                            images_to_send.append({"image_path": v['image_path'], "caption": f"Modèle {variant_label}"})
                        variant_names.append(f"• {variant_label}")

                    variants_text = "\n".join(variant_names)
                    bot_response = message_text or f"Voici les autres modèles disponibles:\n\n{variants_text}\n\nLequel t'intéresse?"
                    if not images_to_send:
                        images_to_send = None
                else:
                    bot_response = "Ce produit n'est disponible que dans ce modèle pour l'instant."
            else:
                bot_response = "Ce produit n'est disponible que dans ce modèle pour l'instant."

        # ── send_location : GPS du marchand ──
        elif name == "send_location":
            send_location = True
            bot_response = message_text or "Je t'envoie la localisation!"

        # ── accept_deal : confirmer la vente ──
        elif name == "accept_deal":
            delivery_type = args.get("delivery_type", "ask")
            deal_price = args.get("price") or current_offer or product['price']

            # Garde-fou prix minimum
            if deal_price < min_price:
                logger.warning(f"accept_deal rejeté par _execute_tool: {deal_price} < min {min_price}")
                min_f = f"{int(min_price):,}".replace(",", " ")
                bot_response = f"Je peux faire {min_f} F, c'est mon dernier prix!"
                new_status = "negotiating"
            else:
                if delivery_type == "delivery":
                    new_status = "pending_delivery"
                    send_location = False
                elif delivery_type == "pickup":
                    new_status = "pending_pickup"
                    send_location = True
                else:
                    new_status = "agreed"
                bot_response = message_text or "Super! Livraison ou tu passes chercher?"

        # ── counter_offer : contre-offre prix ──
        elif name == "counter_offer":
            counter_price = args.get("price", 0)
            if counter_price and counter_price < min_price:
                counter_price = min_price
            bot_response = message_text or f"Je peux faire {int(counter_price):,} F!".replace(",", " ")
            if current_status in ("active", "negotiating"):
                new_status = "negotiating"

        # ── end_conversation ──
        elif name == "end_conversation":
            new_status = "ended"
            bot_response = message_text or "Pas de souci, reviens quand tu veux!"

        # ── request_human_takeover ──
        elif name == "request_human_takeover":
            bot_response = message_text or "Je transmets ton message au vendeur, il te répond très vite!"

        # ── send_payment_info ──
        elif name == "send_payment_info":
            payment_info = merchant.get('payment_info') or merchant.get('payment_methods', '')
            if payment_info:
                bot_response = f"{message_text or 'Voici comment payer !'}\n{payment_info}"
            else:
                bot_response = "Pour les infos de paiement, contacte directement le vendeur!"

        # ── collect_delivery_address ──
        elif name == "collect_delivery_address":
            address = args.get("address", "")
            if address:
                new_status = "pending_delivery"
                bot_response = message_text or f"Noté! On livrera à: {address}"
            else:
                bot_response = message_text or "Parfait! Donne-moi ton adresse de livraison?"

        # ── tool inconnu (ne devrait pas arriver) ──
        else:
            logger.warning(f"_execute_tool: tool inconnu '{name}'")
            bot_response = message_text or ""

        logger.info(f"_execute_tool({name}): status={new_status}, location={send_location}, images={len(images_to_send) if images_to_send else 0}")
        if tracer:
            tracer.add_tool_call(name, reason="DeepSeek tool call dispatched", args={**tool.get("args", {}), "_result_status": new_status, "_send_location": send_location})
        return bot_response, new_status, send_location, images_to_send

    async def _handle_notifications(
        self,
        message: IncomingMessage,
        merchant: Dict,
        product: Dict,
        conversation: Dict,
        current_status: str,
        new_status: str,
        price_offer: Optional[float]
    ) -> Tuple[bool, Optional[str]]:
        """
        Gère les notifications au marchand selon le changement de statut.
        Retourne (should_notify, notification_message).
        """
        should_notify = False
        notification = None

        final_price = price_offer or conversation.get('current_offer') or product['price']

        # === VENTE CONFIRMÉE (livraison ou pickup) ===
        is_sale = (
            (new_status == "pending_delivery" and current_status != "pending_delivery") or
            (new_status == "pending_pickup" and current_status != "pending_pickup")
        )

        if is_sale:
            # Enregistrer la vente dans les stats
            try:
                merchant_obj = await self.merchants.get_by_phone(message.merchant_phone)
                if merchant_obj:
                    await self.stats.record_sale(merchant_obj['id'], final_price)
                    await self.stats.log_event(
                        merchant_id=merchant_obj['id'],
                        event_type='sale',
                        product_id=product['id'],
                        conversation_id=conversation['id'],
                        client_phone=message.client_phone,
                        data={'price': final_price, 'delivery_type': new_status}
                    )

                    # Enregistrer dans l'historique client pour futures négociations
                    await self._record_client_purchase(
                        merchant_id=merchant_obj['id'],
                        client_phone=message.client_phone,
                        product=product,
                        final_price=final_price
                    )
            except Exception as e:
                logger.warning(f"Erreur stats vente: {e}")

            # Décrémenter le stock
            updated_product = await self.products.decrement_stock(product['id'])
            if updated_product:
                stock_status = await self.products.check_stock_status(product['id'])
                new_qty = stock_status['quantity'] if stock_status else 0

                # Journal stock_events (append-only)
                try:
                    await self.waitlist.log_stock_event(
                        merchant_id=merchant['id'],
                        product_id=product['id'],
                        event_type='sale',
                        quantity_delta=-1,
                        quantity_after=new_qty,
                        conversation_id=conversation['id']
                    )
                    if stock_status and stock_status.get('is_out_of_stock'):
                        await self.waitlist.log_stock_event(
                            merchant_id=merchant['id'],
                            product_id=product['id'],
                            event_type='out_of_stock',
                            quantity_delta=0,
                            quantity_after=0,
                            conversation_id=conversation['id']
                        )
                except Exception as e:
                    logger.debug(f"stock_events log (non bloquant): {e}")

                # Alerte stock bas
                if stock_status and stock_status.get('is_low'):
                    await self.notifications.notify_low_stock(
                        merchant_phone=message.merchant_phone,
                        product_name=product['name'],
                        product_code=product['code'],
                        remaining=stock_status['quantity']
                    )

                # Alerte rupture de stock
                if stock_status and stock_status.get('is_out_of_stock'):
                    await self.notifications.notify_out_of_stock(
                        merchant_phone=message.merchant_phone,
                        product_name=product['name'],
                        product_code=product['code']
                    )

        # Notification pour livraison
        if new_status == "pending_delivery" and current_status != "pending_delivery":
            should_notify = True
            notification = f"🛒 Vente! {product['name']} à {final_price:,.0f} F - Client: {message.client_name or message.client_phone}"
            await self.notifications.notify_sale(
                merchant_phone=message.merchant_phone,
                product_name=product['name'],
                price=final_price,
                client_phone=message.client_phone,
                product_code=product.get('code', ''),
                delivery_type="delivery",
                client_name=message.client_name or ""
            )

        # Notification pour récupération au magasin
        if new_status == "pending_pickup" and current_status != "pending_pickup":
            should_notify = True
            notification = f"🏪 Vente! {product['name']} à {final_price:,.0f} F - Client vient chercher: {message.client_name or message.client_phone}"
            await self.notifications.notify_sale(
                merchant_phone=message.merchant_phone,
                product_name=product['name'],
                price=final_price,
                client_phone=message.client_phone,
                product_code=product.get('code', ''),
                delivery_type="pickup",
                client_name=message.client_name or ""
            )

            # NOTE: La localisation est envoyée dans la section 7.5 (send_location flag)
            # Ne PAS l'envoyer ici aussi pour éviter le double envoi

        return should_notify, notification

    async def _handle_follow_ups(
        self,
        conversation: Dict,
        merchant: Dict,
        product: Dict,
        message: IncomingMessage,
        new_status: str
    ) -> None:
        """
        Gère les relances automatiques.
        - Annule les relances existantes quand le client répond
        - Planifie une nouvelle relance si la conversation n'est pas terminée
        """
        try:
            # Annuler les relances en attente (le client a répondu)
            await self.followups.cancel_follow_ups(conversation['id'])

            # Statuts qui ne nécessitent pas de relance
            terminal_statuses = ['completed', 'abandoned', 'ended', 'expired']
            pending_statuses = ['pending_delivery', 'pending_pickup']

            # Si conversation terminée ou en attente de livraison, pas de relance
            if new_status in terminal_statuses or new_status in pending_statuses:
                return

            # Planifier une nouvelle relance
            await self.followups.schedule_follow_up(
                conversation_id=conversation['id'],
                merchant_id=merchant['id'],
                merchant_phone=message.merchant_phone,
                client_phone=message.client_phone,
                product_name=product['name'],
                step=1
            )

        except Exception as e:
            logger.warning(f"Erreur gestion relances: {e}")

    # === Méthodes utilitaires ===

    async def _get_negotiation_context(
        self,
        merchant_id: int,
        client_phone: str,
        product: Dict
    ) -> Optional[Dict]:
        """
        Récupère le contexte de négociation pour un client.
        """
        try:
            context = await self.client_history.get_negotiation_context(
                merchant_id=merchant_id,
                client_phone=client_phone,
                product_price=product['price'],
                min_price=product['min_price']
            )
            logger.info(f"Contexte négociation: {context.get('recommendation')}")
            return context
        except Exception as e:
            logger.warning(f"Erreur récupération contexte négociation: {e}")
            return None

    async def _find_and_save_selected_variant(
        self,
        conversation: Dict,
        product: Dict,
        message_text: str
    ) -> None:
        """
        Détecte si le client a répondu à la photo d'une variante spécifique (préfixe WhatsApp reply).
        Si oui, sauvegarde selected_variant_id dans la conversation ET dans le dict local.

        Format attendu: [Répond à la photo: "Modèle Autre format"] ...
        """
        import re
        match = re.search(r'\[Répond à la photo: "Modèle ([^"]+)"\]', message_text)
        if not match:
            return

        variant_name_from_reply = match.group(1).strip()
        group_id = product.get('group_id')
        if not group_id:
            return

        try:
            all_variants = await self.products.get_all_in_group(group_id)
            for v in all_variants:
                v_label = (v.get('variant_name') or v['name']).strip()
                if v_label.lower() == variant_name_from_reply.lower() or \
                   variant_name_from_reply.lower() in v_label.lower():
                    if v['id'] != conversation.get('selected_variant_id'):
                        await self.conversations.update(conversation['id'], selected_variant_id=v['id'])
                        conversation['selected_variant_id'] = v['id']  # Mettre à jour le dict local
                        logger.info(f"Variante sélectionnée mémorisée: {v_label} (id={v['id']})")
                    return
        except Exception as e:
            logger.debug(f"Mémorisation variante (non bloquant): {e}")

    async def _record_client_purchase(
        self,
        merchant_id: int,
        client_phone: str,
        product: Dict,
        final_price: float
    ) -> None:
        """
        Enregistre un achat dans l'historique client.
        """
        try:
            await self.client_history.record_purchase(
                merchant_id=merchant_id,
                client_phone=client_phone,
                amount=final_price,
                original_price=product['price'],
                final_price=final_price,
                category=product.get('category')
            )
            logger.info(f"Achat enregistré pour {client_phone}: {final_price} F")
        except Exception as e:
            logger.warning(f"Erreur enregistrement achat: {e}")

    async def _auto_learn_from_deal(
        self,
        merchant_id: int,
        client_message: str,
        bot_response: str
    ) -> None:
        """
        Boucle d'apprentissage — Sauvegarde automatiquement en KB l'échange final
        qui a mené à un accord (deal closé). Non bloquant.

        Chaque vente réussie enrichit la KB avec le message client déclencheur
        et la réponse bot qui a confirmé le deal (source='auto_learned_deal').
        """
        try:
            kb_repo = KnowledgeBaseRepository()
            await kb_repo.save_entry(
                merchant_id=merchant_id,
                question=client_message,
                answer=bot_response,
                source="auto_learned_deal"
            )
            logger.info(f"Auto-apprentissage: deal closé → KB enrichie (merchant {merchant_id})")
        except Exception as e:
            logger.debug(f"Auto-learn deal (non bloquant): {e}")

    async def _check_waitlist_reply(
        self,
        message,
        conversation: dict,
        product: dict,
        merchant: dict
    ):
        """
        Détecte si le client répond OUI à une offre de waitlist.
        Le dernier message bot doit être une question de waitlist.
        """
        import re
        text_lower = message.message.strip().lower()
        oui_patterns = ['oui', 'yes', 'ok', 'ouais', 'yep', '1', 'o', 'oki', 'dac', "d'accord"]
        if text_lower not in oui_patterns and not any(p in text_lower for p in oui_patterns[:4]):
            return None

        # Vérifier que le dernier message bot était une offre de waitlist
        history = await self.conversations.get_messages(conversation['id'])
        bot_messages = [m for m in history if not m.get('is_from_client')]
        if not bot_messages:
            return None
        last_bot = bot_messages[-1].get('content', '')
        if 'liste prioritaire' not in last_bot and 'waitlist' not in last_bot.lower() and 'notifié' not in last_bot:
            return None

        # Vérifier stock toujours à 0
        stock_status = await self.products.check_stock_status(product['id'])
        if not stock_status or not stock_status.get('is_out_of_stock'):
            return None

        # Enregistrer en waitlist
        already_in = await self.waitlist.is_client_in_waitlist(product['id'], message.client_phone)
        if not already_in:
            await self.waitlist.add_to_waitlist(
                merchant_id=merchant['id'],
                product_id=product['id'],
                client_phone=message.client_phone,
                client_name=message.client_name or None,
                conversation_id=conversation['id'],
                offered_price=conversation.get('current_offer')
            )

        position = await self.waitlist.get_waitlist_count(product['id'])
        bot_message = (
            f"✅ C'est noté ! Tu es sur la liste prioritaire pour *{product['name']}*.\n\n"
            f"{'Tu es le premier sur la liste !' if position == 1 else f'Tu es {position}e sur la liste.'}\n\n"
            f"_Je t'enverrai un message WhatsApp dès que le stock revient._ 🔔"
        )
        await self.conversations.add_message(conversation['id'], bot_message, False)
        return BotResponse(
            message=bot_message,
            conversation_id=conversation['id'],
            should_notify_merchant=False
        )

    async def _auto_flag_unanswered(
        self,
        conversation_id: int,
        merchant_id: int,
        client_phone: str,
        client_message: str,
        bot_response: str,
        history: List[Dict],
        product: Dict
    ) -> None:
        """
        Boucle d'apprentissage — Détecte et flag automatiquement les questions
        que le bot n'a pas traitées correctement. Non bloquant.

        Crée une entrée 'auto_flagged' dans conversation_feedback si la santé
        conversationnelle détecte unanswered_question=True.
        Anti-spam : une seule entrée auto_flagged par conversation.
        """
        try:
            # Inclure la réponse bot actuelle dans l'historique pour une analyse complète
            full_history = list(history) + [{'content': bot_response, 'is_from_client': False}]
            health = analyze_conversation_health(full_history, client_message, product)
            if not health['unanswered_question']:
                return

            from ..database.connection import get_connection
            async with get_connection() as db:
                # Anti-spam : une seule entrée par conversation
                cur = await db.execute(
                    """SELECT COUNT(*) as cnt FROM conversation_feedback
                       WHERE merchant_id = ? AND conversation_id = ?
                         AND feedback_type = 'auto_flagged'""",
                    (merchant_id, conversation_id)
                )
                row = await cur.fetchone()
                if row['cnt'] > 0:
                    return

                await db.execute(
                    """INSERT INTO conversation_feedback
                       (conversation_id, merchant_id, client_phone, client_message,
                        bot_response, feedback_type, notes, kb_entry_id)
                       VALUES (?, ?, ?, ?, ?, 'auto_flagged',
                               'Auto-détecté: question sans réponse adéquate', NULL)""",
                    (conversation_id, merchant_id, client_phone,
                     client_message, bot_response)
                )
                await db.commit()
            logger.debug(f"Auto-flag: question sans réponse enregistrée (merchant {merchant_id})")
        except Exception as e:
            logger.debug(f"Auto-flag (non bloquant): {e}")

    async def get_conversations(
        self,
        merchant_phone: str,
        status: str = "active"
    ) -> List[Dict]:
        """Récupère les conversations d'un marchand"""
        merchant = await self.merchants.get_by_phone(merchant_phone)
        if not merchant:
            return []
        # "pending" = pending_delivery + pending_pickup
        if status == "pending":
            return await self.conversations.get_pending(merchant['id'])
        return await self.conversations.get_by_merchant(merchant['id'], status)

    async def get_conversation_messages(self, conversation_id: int) -> List[Dict]:
        """Récupère les messages d'une conversation"""
        return await self.conversations.get_messages(conversation_id)


# Instance globale
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Retourne l'instance globale du service de chat"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
