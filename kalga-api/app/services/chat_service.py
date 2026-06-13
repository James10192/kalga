"""
Service de chat
Orchestre le flux de conversation entre clients et marchands
"""
import json
import logging
from typing import Optional, List, Dict, Any, Tuple

from ..models.schemas import IncomingMessage, BotResponse
from ..infrastructure.convex_client import get_convex
from .convex_adapters import adapt_context, adapt_product
from .notification_service import NotificationService
from .ai import extract_product_code, analyze_conversation_health, FallbackResponses
from .ai.detectors import detect_other_products_request, count_low_offers
from .ai.debug_tracer import DebugTracer

logger = logging.getLogger("kalga.chat")


class ChatService:
    """
    Service qui orchestre le flux de chat.
    Sépare la logique métier de la couche HTTP.
    """

    def __init__(
        self,
        notification_service: NotificationService = None
    ):
        # Hot-path = Convex uniquement (plan 004). Plus aucun repo SQLite ici :
        # lectures via `internal/chat:getContext`, écritures via les mutations
        # grossières (`commitTurn`, `recordSale`, `decrementStock`, ...).
        self.cx = get_convex()
        self.notifications = notification_service or NotificationService()

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

        # === 1. LECTURE GROSSIERE : un seul round-trip Convex (getContext) ===
        # Remplace ~10 lectures SQLite (marchand, dispo, produit, conversation,
        # historique, stock, faits memoire). Tous les ids restent des STRINGS.
        ctx_args: Dict[str, Any] = {
            "merchantPhone": message.merchant_phone,
            "clientPhone": message.client_phone,
        }
        # productCode optionnel cote Convex (v.optional(v.string())) : ne JAMAIS
        # passer null/None — on omet la cle quand aucun code n'est detecte.
        product_code = message.product_code or extract_product_code(message.message)
        if product_code:
            ctx_args["productCode"] = product_code
        raw_ctx = await self.cx.query("internal/chat:getContext", ctx_args)
        ctx = adapt_context(raw_ctx)
        merchant = ctx["merchant"]

        if not merchant:
            logger.error(f"Marchand {message.merchant_phone} non trouve!")
            return BotResponse(
                message="", conversation_id="",
                should_notify_merchant=False, no_response=True
            )

        # 1.5 Mode absence (parite is_merchant_available)
        if ctx["away"]:
            logger.info(f"Marchand {message.merchant_phone} indisponible - Mode absence actif")
            return BotResponse(
                message=merchant.get('away_message') or "",
                conversation_id="",
                should_notify_merchant=False,
                away_mode=True
            )

        product = ctx["product"]
        conversation = ctx["conversation"]
        history = ctx["history"]
        stock_status = ctx["stock_status"]
        memory_facts_raw = ctx["memory_facts"]

        # Pas de conversation active ET pas de produit (pas de #code) -> silence.
        if not conversation and not product:
            logger.info(f"Pas de conversation active pour {message.client_phone}")
            return BotResponse(
                message="", conversation_id="",
                should_notify_merchant=False, no_response=True
            )

        merchant_id = merchant['id']
        # `is_first_message` : aucune conversation existante (a creer) OU au plus le
        # message client courant deja present. getContext renvoie l'historique
        # AVANT ce tour, donc une conversation neuve a un historique vide.
        is_first_message = len(history) <= 1
        conversation_id = conversation['id'] if conversation else None
        product_id_for_create = product['id'] if (product and not conversation) else None

        # === 2. RUPTURE DE STOCK (nouvelle conversation, produit epuise) ===
        if is_first_message and product and stock_status and stock_status.get('isOutOfStock'):
            out_mode = product.get('out_of_stock_mode', 'waitlist')
            if out_mode == 'waitlist':
                waitlist_count = await self.cx.query("internal/waitlist:getWaitlistCount", {
                    "merchantId": merchant_id, "productId": product['id']})
                already_in = await self.cx.query("internal/waitlist:isClientInWaitlist", {
                    "merchantId": merchant_id, "productId": product['id'],
                    "clientPhone": message.client_phone})
                if already_in:
                    bot_message = (
                        f"\U0001f60a Le *{product['name']}* est toujours en rupture de stock, "
                        f"mais tu es deja sur la liste d'attente ! "
                        f"Je te previens des qu'il revient."
                    )
                else:
                    queue_text = (
                        f" ({waitlist_count} client{'s' if waitlist_count > 1 else ''} avant toi)"
                        if waitlist_count > 0 else ""
                    )
                    bot_message = (
                        f"\U0001f615 Le *{product['name']}* est momentanement epuise.\n\n"
                        f"Souhaites-tu etre notifie des qu'il sera disponible ?{queue_text}\n\n"
                        f"Reponds *OUI* pour rejoindre la liste prioritaire \U0001f514"
                    )
            else:
                bot_message = (
                    f"Desole, le {product['name']} est actuellement en rupture de stock. "
                    f"Je te contacte des qu'il est de nouveau disponible!"
                )
            # Persistance atomique du tour (cree la conversation si besoin).
            commit = await self._commit_turn(
                merchant_id=merchant_id, conversation_id=conversation_id,
                product_id=product_id_for_create, client_phone=message.client_phone,
                client_message=message.message, bot_message=bot_message,
            )
            return BotResponse(
                message=bot_message,
                conversation_id=commit["conversationId"],
                should_notify_merchant=True,
                notification_reason=f"Client interesse par {product['code']} (RUPTURE)"
            )

        # === 3. REPONSE OUI A LA WAITLIST (conversation existante) ===
        if not is_first_message and conversation and product:
            waitlist_response = await self._check_waitlist_reply(
                message=message, conversation=conversation,
                product=product, merchant=merchant, history=history,
                stock_status=stock_status,
            )
            if waitlist_response:
                return waitlist_response

        # === 4. Variante selectionnee (reply photo) — avant les cas speciaux ===
        current_status = conversation.get('status', 'active') if conversation else 'active'
        selected_variant_id = None  # transmis a commitTurn si trouve
        if conversation and current_status not in ('pending_pickup', 'pending_delivery'):
            selected_variant_id = await self._find_selected_variant(
                conversation=conversation, product=product,
                message_text=message.message,
            )

        # === 5. CAS SPECIAUX (catalogue autres produits) ===
        if current_status not in ('pending_pickup', 'pending_delivery') and product and conversation:
            special_response = await self._handle_special_requests(
                message=message, conversation=conversation, product=product,
                merchant_id=merchant_id,
            )
            if special_response:
                return special_response

        if tracer:
            tracer.event("CHAT", "ai_generate_start",
                conversation_status=current_status,
                history_len=len(history),
                has_negotiation_context=bool(memory_facts_raw)
            )

        # === 6. CERVEAU V2 (seul cerveau — plus de toggle, plus de v1) ===
        from .dialogue.engine import respond as dialogue_respond

        # Memoire long-terme : faits connus du client -> personnalisent la voix.
        v2_memory = None
        try:
            facts = json.loads(memory_facts_raw) if memory_facts_raw else []
            fact_lines = [f.get("fact") for f in facts[:3] if isinstance(f, dict) and f.get("fact")]
            if fact_lines:
                v2_memory = "Ce qu'on sait du client : " + " ; ".join(fact_lines)
        except Exception as e:
            logger.debug(f"LTM v2 indisponible (non bloquant): {e}")

        # Catalogue marchand (variantes + autres produits) charge UNE fois via Convex,
        # passe au cerveau v2 pour resolution images / catalogue (plus de ProductRepository).
        catalog = None
        if product:
            try:
                catalog = await self._load_catalog(merchant_id)
            except Exception as e:
                logger.debug(f"Chargement catalogue v2 (non bloquant): {e}")

        # Le cerveau v2 a besoin d'une conversation dict ; si aucune n'existe encore
        # (1er message sur #code), on en simule une (creation reelle en commitTurn).
        conv_for_brain = conversation or {
            "id": None, "status": "active",
            "current_offer": None, "selected_variant_id": selected_variant_id,
        }
        if selected_variant_id and conversation:
            conv_for_brain = {**conversation, "selected_variant_id": selected_variant_id}

        engine_v2 = await dialogue_respond(
            client_message=message.message,
            conversation=conv_for_brain,
            product=product or {},
            merchant=merchant,
            history=history,
            memory_extra=v2_memory,
            catalog=catalog,
        )
        if tracer:
            tracer.event("CHAT", "dialogue_v2",
                         used=engine_v2 is not None,
                         facts=engine_v2.facts if engine_v2 else None)

        # === 7. Repli : v2 -> None => FallbackResponses (PLUS de v1) ===
        images_to_send = None
        human_takeover = False
        use_voice = "[\U0001f3a4 Vocal transcrit" in (message.message or "")
        if engine_v2 is not None:
            bot_response = engine_v2.message
            price_offer = engine_v2.new_offer
            new_status = engine_v2.new_status
            send_location = engine_v2.send_location
            images_to_send = engine_v2.images_to_send
            human_takeover = engine_v2.human_takeover

            # Prise de main marchand — notifications explicites du moteur v2.
            if engine_v2.notify_reason == "delivery_address" and product:
                await self.notifications.notify_sale(
                    merchant_phone=message.merchant_phone,
                    product_name=product['name'],
                    price=engine_v2.new_offer or conv_for_brain.get('current_offer') or product['price'],
                    client_phone=message.client_phone,
                    product_code=product.get('code', ''),
                    delivery_type="delivery",
                    client_name=message.client_name or "",
                    delivery_address=engine_v2.delivery_address or "",
                )
            elif engine_v2.notify_reason == "human_request" and product:
                await self.notifications.send_message(
                    merchant_phone=message.merchant_phone,
                    to=message.merchant_phone,
                    message=(f"\U0001f64b *Le client {message.client_phone} demande a te parler "
                             f"directement* ({product['name']}). Prends le relais !"),
                )
        else:
            # Moteur de secours statique (mots-cles). Aucun appel LLM, aucune DB.
            low_offers = count_low_offers(history, product.get('min_price', 0)) if product else 0
            bot_response, price_offer, _accepted, new_status = FallbackResponses.generate_response(
                client_message=message.message,
                product_name=product.get('name', '') if product else '',
                price=product.get('price', 0) if product else 0,
                min_price=product.get('min_price', 0) if product else 0,
                current_offer=conv_for_brain.get('current_offer'),
                is_first_message=is_first_message,
                low_offers_count=low_offers,
                product_description=product.get('description') if product else None,
            )
            send_location = False

        logger.info(f"Reponse IA: {bot_response[:80] if bot_response else 'NONE'}... | Status: {new_status} | Location: {send_location}")
        if tracer:
            tracer.event("CHAT", "ai_generate_done",
                new_status=new_status, send_location=send_location,
                response_len=len(bot_response) if bot_response else 0
            )

        # === 8. PERSISTANCE ATOMIQUE DU TOUR (commitTurn) ===
        # Cree la conversation si elle n'existait pas (productId fourni), insere
        # message client + message bot, met a jour statut + offre + variante.
        commit = await self._commit_turn(
            merchant_id=merchant_id,
            conversation_id=conversation_id,
            product_id=product_id_for_create,
            client_phone=message.client_phone,
            client_message=message.message,
            bot_message=bot_response if bot_response else None,
            new_status=new_status,
            current_offer=price_offer,
            selected_variant_id=selected_variant_id,
        )
        conversation_id = commit["conversationId"]

        # Si pas de reponse (conversation terminee muette)
        if bot_response is None:
            return BotResponse(
                message="", conversation_id=conversation_id,
                should_notify_merchant=False, no_response=True
            )

        # === 9. Boucle d'apprentissage — auto-flag des questions sans reponse ===
        if not is_first_message and product:
            await self._auto_flag_unanswered(
                conversation_id=conversation_id, merchant_id=merchant_id,
                client_phone=message.client_phone, client_message=message.message,
                bot_response=bot_response, history=history, product=product,
            )

        # === 10. Notifications marchand + vente (decrementStock/recordSale) ===
        should_notify, notification = await self._handle_notifications(
            message=message, merchant=merchant, product=product,
            conversation_id=conversation_id, current_offer=conv_for_brain.get('current_offer'),
            current_status=current_status, new_status=new_status, price_offer=price_offer,
        )

        # 10.5 Double-check localisation en pending_pickup
        if not send_location and new_status == "pending_pickup":
            from ..services.ai.detectors import detect_location_request
            if detect_location_request(message.message):
                send_location = True
                logger.info(f"[LOCATION] Force send_location=True via double-check pour pending_pickup")

        # Localisation a passer au bridge
        merchant_location = None
        if send_location:
            latitude = merchant.get('latitude')
            longitude = merchant.get('longitude')
            address = merchant.get('address', '')
            logger.info(f"[LOCATION] Donnees preparees pour le bridge: lat={latitude}, lng={longitude}, addr={address}")
            if latitude and longitude:
                name = merchant.get('business_name') or merchant.get('name') or 'Ma boutique'
                merchant_location = {
                    "latitude": latitude, "longitude": longitude,
                    "name": name, "address": address,
                }
            elif address:
                merchant_location = {"address": address}
            else:
                logger.warning(f"[LOCATION] Aucune donnee de localisation disponible pour {message.merchant_phone}")
                send_location = False
                human_takeover = True

        # === 11. Message de fin de transaction (goodbye) ===
        is_transaction_end = (
            new_status in ("pending_delivery", "pending_pickup")
            and current_status not in ("pending_delivery", "pending_pickup")
        )
        goodbye_message = None
        if is_transaction_end:
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
                    f"\U0001f6cd️ Decouvre tous les produits de {store_name} ici :\n"
                    f"\U0001f449 {storefront_url}"
                )
            # Auto-apprentissage : sauvegarder l'echange final en KB.
            await self._auto_learn_from_deal(
                merchant_id=merchant_id,
                client_message=message.message,
                bot_response=bot_response,
            )

        # === 12. Relances automatiques ===
        await self._handle_follow_ups(
            conversation_id=conversation_id, merchant=merchant,
            product=product, message=message, new_status=new_status,
        )

        # === 13. TTS — vocal si demande ===
        audio_base64 = None
        if use_voice and bot_response:
            try:
                import base64
                from .tts_service import text_to_ogg
                lang = "fr"
                if message.message and "[\U0001f3a4 Vocal transcrit" in message.message:
                    import re as _re
                    m = _re.search(r"\[\U0001f3a4 Vocal transcrit \((\w+)\)\]", message.message)
                    if m:
                        lang = m.group(1)
                ogg_bytes = await text_to_ogg(bot_response, lang=lang)
                if ogg_bytes:
                    audio_base64 = base64.b64encode(ogg_bytes).decode("utf-8")
                    logger.info(f"TTS vocal genere: {len(ogg_bytes)} bytes OGG (lang={lang})")
                else:
                    logger.warning("TTS: generation OGG echouee — reponse texte envoyee")
            except Exception as e:
                logger.error(f"Erreur TTS dans chat_service: {e}")

        return BotResponse(
            message=bot_response,
            conversation_id=conversation_id,
            should_notify_merchant=should_notify,
            notification_reason=notification,
            send_location=send_location,
            merchant_location=merchant_location,
            goodbye_message=goodbye_message,
            human_takeover=human_takeover,
            images_to_send=images_to_send,
            audio_base64=audio_base64,
        )

    async def _commit_turn(
        self,
        merchant_id: str,
        conversation_id: Optional[str],
        product_id: Optional[str],
        client_phone: str,
        client_message: str,
        bot_message: Optional[str] = None,
        new_status: Optional[str] = None,
        current_offer: Optional[float] = None,
        selected_variant_id: Optional[str] = None,
        close_conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Wrapper de `internal/chat:commitTurn`. Construit dynamiquement les args
        (jamais d'`undefined`/None superflu envoye a Convex) : upsert conversation
        + insert messages + maj statut/offre/variante, atomique cote Convex.
        """
        args: Dict[str, Any] = {
            "merchantId": merchant_id,
            "clientPhone": client_phone,
            "clientMessage": client_message,
        }
        if conversation_id:
            args["conversationId"] = conversation_id
        if product_id:
            args["productId"] = product_id
        if bot_message:
            args["botMessage"] = bot_message
        if new_status:
            args["newStatus"] = new_status
        if current_offer is not None:
            args["currentOffer"] = current_offer
        if selected_variant_id:
            args["selectedVariantId"] = selected_variant_id
        if close_conversation_id:
            args["closeConversationId"] = close_conversation_id
        return await self.cx.mutation("internal/chat:commitTurn", args)

    async def _load_catalog(self, merchant_id: str) -> List[Dict]:
        """
        Catalogue complet du marchand via Convex (parite product_repo.get_by_merchant),
        adapte en dicts snake_case (ids = strings). Sert au cerveau v2 pour resoudre
        photos/variantes/catalogue sans toucher SQLite.
        """
        raw = await self.cx.query("internal/inventory:listProductsForTools", {
            "merchantId": merchant_id})
        out = []
        for doc in raw or []:
            p = adapt_product(doc)
            if p:
                out.append(p)
        return out

    async def _handle_special_requests(
        self,
        message: IncomingMessage,
        conversation: Dict,
        product: Dict,
        merchant_id: str,
    ) -> Optional[BotResponse]:
        """
        Gere uniquement les demandes de catalogue (autres produits du marchand).
        Le catalogue vient de Convex (listProductsForTools). Le tour est persiste
        atomiquement via commitTurn (message client + message bot).
        """
        import re

        raw_text = re.sub(r'^\[Répond à[^\]]*\]\s*', '', message.message)

        if detect_other_products_request(raw_text):
            all_products = await self._load_catalog(merchant_id)
            other_products = [p for p in all_products if p['id'] != product['id']]

            if other_products:
                product_lines = []
                for p in other_products[:5]:
                    price_str = f"{p['price']:,.0f}".replace(",", " ")
                    product_lines.append(f"• {p['name']} — {price_str} F ({p['code']})")
                products_text = "\n".join(product_lines)
                bot_message = f"Oui, on a aussi d'autres articles:\n\n{products_text}\n\nLequel t'interesse?"
            else:
                bot_message = f"Pour l'instant c'est surtout le {product['name']} qu'on a en stock. Si tu veux je te le reserve?"

            await self._commit_turn(
                merchant_id=merchant_id,
                conversation_id=conversation['id'],
                product_id=None,
                client_phone=message.client_phone,
                client_message=message.message,
                bot_message=bot_message,
            )
            return BotResponse(
                message=bot_message,
                conversation_id=conversation['id'],
                should_notify_merchant=False
            )

        return None

    async def _handle_notifications(
        self,
        message: IncomingMessage,
        merchant: Dict,
        product: Optional[Dict],
        conversation_id: str,
        current_offer: Optional[float],
        current_status: str,
        new_status: str,
        price_offer: Optional[float]
    ) -> Tuple[bool, Optional[str]]:
        """
        Gere les notifications au marchand selon le changement de statut + la
        comptabilisation de vente (recordSale + decrementStock cote Convex).
        Retourne (should_notify, notification_message).
        """
        should_notify = False
        notification = None
        if not product:
            return should_notify, notification

        merchant_id = merchant['id']
        final_price = price_offer or current_offer or product['price']

        # === VENTE CONFIRMEE (livraison ou pickup) ===
        is_sale = (
            (new_status == "pending_delivery" and current_status != "pending_delivery") or
            (new_status == "pending_pickup" and current_status != "pending_pickup")
        )

        if is_sale:
            # 1. Comptabilisation atomique de la vente (stats jour + historique
            #    client + event analytics) — parite record_sale/record_purchase.
            try:
                await self.cx.mutation("internal/chat:recordSale", {
                    "merchantId": merchant_id,
                    "conversationId": conversation_id,
                    "productId": product['id'],
                    "clientPhone": message.client_phone,
                    "amount": final_price,
                    "originalPrice": product['price'],
                    "finalPrice": final_price,
                    **({"category": product['category']} if product.get('category') else {}),
                })
            except Exception as e:
                logger.warning(f"Erreur recordSale: {e}")

            # 2. Decrement de stock atomique (+ journal stockEvents sale/out_of_stock).
            try:
                dec = await self.cx.mutation("internal/inventory:decrementStock", {
                    "productId": product['id'],
                    "quantity": 1,
                    "conversationId": conversation_id,
                })
                status = (dec or {}).get("stockStatus") if dec else None
                if status and status.get('isLow'):
                    await self.notifications.notify_low_stock(
                        merchant_phone=message.merchant_phone,
                        product_name=product['name'],
                        product_code=product['code'],
                        remaining=status['quantity']
                    )
                if status and status.get('isOutOfStock'):
                    await self.notifications.notify_out_of_stock(
                        merchant_phone=message.merchant_phone,
                        product_name=product['name'],
                        product_code=product['code']
                    )
            except Exception as e:
                logger.debug(f"decrementStock (non bloquant): {e}")

        # Notification pour livraison
        if new_status == "pending_delivery" and current_status != "pending_delivery":
            should_notify = True
            notification = f"\U0001f6d2 Vente! {product['name']} a {final_price:,.0f} F - Client: {message.client_name or message.client_phone}"
            await self.notifications.notify_sale(
                merchant_phone=message.merchant_phone,
                product_name=product['name'],
                price=final_price,
                client_phone=message.client_phone,
                product_code=product.get('code', ''),
                delivery_type="delivery",
                client_name=message.client_name or ""
            )

        # Notification pour recuperation au magasin
        if new_status == "pending_pickup" and current_status != "pending_pickup":
            should_notify = True
            notification = f"\U0001f3ea Vente! {product['name']} a {final_price:,.0f} F - Client vient chercher: {message.client_name or message.client_phone}"
            await self.notifications.notify_sale(
                merchant_phone=message.merchant_phone,
                product_name=product['name'],
                price=final_price,
                client_phone=message.client_phone,
                product_code=product.get('code', ''),
                delivery_type="pickup",
                client_name=message.client_name or ""
            )

        return should_notify, notification

    async def _handle_follow_ups(
        self,
        conversation_id: str,
        merchant: Dict,
        product: Optional[Dict],
        message: IncomingMessage,
        new_status: str
    ) -> None:
        """
        Relances automatiques via Convex (scheduleFollowup/cancelFollowups).
        - Annule les relances pending quand le client repond.
        - Planifie une nouvelle relance si la conversation n'est pas terminee.
        """
        try:
            # Annuler les relances en attente (le client a repondu).
            await self.cx.mutation("internal/followups:cancelFollowups", {
                "conversationId": conversation_id})

            terminal_statuses = ['completed', 'abandoned', 'ended', 'expired']
            pending_statuses = ['pending_delivery', 'pending_pickup']
            if new_status in terminal_statuses or new_status in pending_statuses:
                return
            if not product:
                return

            await self.cx.mutation("internal/followups:scheduleFollowup", {
                "conversationId": conversation_id,
                "merchantId": merchant['id'],
                "merchantPhone": message.merchant_phone,
                "clientPhone": message.client_phone,
                "productName": product['name'],
                "step": 1,
            })
        except Exception as e:
            logger.warning(f"Erreur gestion relances: {e}")

    # === Methodes utilitaires ===

    async def _find_selected_variant(
        self,
        conversation: Dict,
        product: Optional[Dict],
        message_text: str
    ) -> Optional[str]:
        """
        Detecte si le client a repondu a la photo d'une variante specifique
        (prefixe WhatsApp reply). Si oui, renvoie l'id (STRING) de la variante a
        memoriser (transmis a commitTurn via selectedVariantId). Sinon None.

        Format attendu: [Répond à la photo: "Modèle Autre format"] ...
        """
        import re
        match = re.search(r'\[Répond à la photo: "Modèle ([^"]+)"\]', message_text)
        if not match or not product:
            return None

        variant_name_from_reply = match.group(1).strip()
        group_id = product.get('group_id')
        if not group_id:
            return None

        try:
            # Catalogue marchand -> variantes du meme groupe.
            all_products = await self._load_catalog(product['merchant_id'])
            group_variants = [p for p in all_products if p.get('group_id') == group_id]
            for v in group_variants:
                v_label = (v.get('variant_name') or v['name']).strip()
                if v_label.lower() == variant_name_from_reply.lower() or \
                   variant_name_from_reply.lower() in v_label.lower():
                    logger.info(f"Variante selectionnee detectee: {v_label} (id={v['id']})")
                    return v['id']
        except Exception as e:
            logger.debug(f"Memorisation variante (non bloquant): {e}")
        return None

    async def _auto_learn_from_deal(
        self,
        merchant_id: str,
        client_message: str,
        bot_response: str
    ) -> None:
        """
        Boucle d'apprentissage — Sauvegarde en KB l'echange final qui a mene a un
        accord (deal close) via Convex saveKnowledgeEntry. Non bloquant.
        """
        try:
            await self.cx.mutation("internal/memory:saveKnowledgeEntry", {
                "merchantId": merchant_id,
                "question": client_message,
                "answer": bot_response,
                "source": "auto_learned_deal",
            })
            logger.info(f"Auto-apprentissage: deal close -> KB enrichie (merchant {merchant_id})")
        except Exception as e:
            logger.debug(f"Auto-learn deal (non bloquant): {e}")

    async def _check_waitlist_reply(
        self,
        message,
        conversation: dict,
        product: dict,
        merchant: dict,
        history: List[Dict],
        stock_status: Optional[Dict],
    ):
        """
        Detecte si le client repond OUI a une offre de waitlist (dernier message
        bot = question waitlist, stock toujours a 0). Inscrit en waitlist via
        Convex et persiste le tour atomiquement (commitTurn).
        `history` et `stock_status` sont fournis par le getContext du tour courant.
        """
        text_lower = message.message.strip().lower()
        oui_patterns = ['oui', 'yes', 'ok', 'ouais', 'yep', '1', 'o', 'oki', 'dac', "d'accord"]
        if text_lower not in oui_patterns and not any(p in text_lower for p in oui_patterns[:4]):
            return None

        # Le dernier message bot doit etre une offre de waitlist.
        bot_messages = [m for m in (history or []) if not m.get('is_from_client')]
        if not bot_messages:
            return None
        last_bot = bot_messages[-1].get('content', '')
        if 'liste prioritaire' not in last_bot and 'waitlist' not in last_bot.lower() and 'notifi' not in last_bot.lower():
            return None

        # Stock toujours en rupture.
        if not stock_status or not stock_status.get('isOutOfStock'):
            return None

        merchant_id = merchant['id']
        # Inscription waitlist (idempotente cote Convex : added=False si deja la).
        add_args = {
            "merchantId": merchant_id,
            "productId": product['id'],
            "clientPhone": message.client_phone,
        }
        if message.client_name:
            add_args["clientName"] = message.client_name
        if conversation.get('id'):
            add_args["conversationId"] = conversation['id']
        if conversation.get('current_offer') is not None:
            add_args["offeredPrice"] = conversation['current_offer']
        res = await self.cx.mutation("internal/waitlist:addToWaitlist", add_args)
        position = (res or {}).get("position") or await self.cx.query(
            "internal/waitlist:getWaitlistCount",
            {"merchantId": merchant_id, "productId": product['id']})

        bot_message = (
            f"✅ C'est note ! Tu es sur la liste prioritaire pour *{product['name']}*.\n\n"
            f"{'Tu es le premier sur la liste !' if position == 1 else f'Tu es {position}e sur la liste.'}\n\n"
            f"_Je t'enverrai un message WhatsApp des que le stock revient._ \U0001f514"
        )
        await self._commit_turn(
            merchant_id=merchant_id,
            conversation_id=conversation['id'],
            product_id=None,
            client_phone=message.client_phone,
            client_message=message.message,
            bot_message=bot_message,
        )
        return BotResponse(
            message=bot_message,
            conversation_id=conversation['id'],
            should_notify_merchant=False
        )

    async def _auto_flag_unanswered(
        self,
        conversation_id: str,
        merchant_id: str,
        client_phone: str,
        client_message: str,
        bot_response: str,
        history: List[Dict],
        product: Dict
    ) -> None:
        """
        Boucle d'apprentissage — flag automatiquement les questions que le bot n'a
        pas traitees correctement, via Convex flagUnanswered (anti-spam : une seule
        entree auto_flagged par conversation, gere cote Convex). Non bloquant.
        """
        try:
            full_history = list(history) + [{'content': bot_response, 'is_from_client': False}]
            health = analyze_conversation_health(full_history, client_message, product)
            if not health['unanswered_question']:
                return
            await self.cx.mutation("internal/chat:flagUnanswered", {
                "merchantId": merchant_id,
                "conversationId": conversation_id,
                "clientPhone": client_phone,
                "question": client_message,
                "botResponse": bot_response,
            })
            logger.debug(f"Auto-flag: question sans reponse enregistree (merchant {merchant_id})")
        except Exception as e:
            logger.debug(f"Auto-flag (non bloquant): {e}")

    async def get_conversations(
        self,
        merchant_phone: str,
        status: str = "active"
    ) -> List[Dict]:
        """
        Récupère les conversations d'un marchand (lecture dashboard, HORS hot-path).
        Encore sur SQLite — migré en Phase F (le hot-path /incoming est Convex).
        Repos importés localement pour garder le hot-path 100% Convex.
        """
        from ..database.repositories import MerchantRepository, ConversationRepository
        merchants = MerchantRepository()
        conversations = ConversationRepository()
        merchant = await merchants.get_by_phone(merchant_phone)
        if not merchant:
            return []
        # "pending" = pending_delivery + pending_pickup
        if status == "pending":
            return await conversations.get_pending(merchant['id'])
        return await conversations.get_by_merchant(merchant['id'], status)

    async def get_conversation_messages(self, conversation_id: int) -> List[Dict]:
        """Récupère les messages d'une conversation (lecture dashboard, HORS hot-path)."""
        from ..database.repositories import ConversationRepository
        return await ConversationRepository().get_messages(conversation_id)


# Instance globale
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Retourne l'instance globale du service de chat"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
