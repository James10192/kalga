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
from ..models.schemas import IncomingMessage, BotResponse
from .notification_service import NotificationService
from .followup_service import get_followup_service
from .conversation_ai import generate_response, extract_product_code, detect_variant_request, detect_photo_request
from .ai.memory import ltm as ltm_module
from .ai.memory import episodic as episodic_module
from .ai.deepseek_client import get_deepseek_client

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

    async def handle_incoming_message(self, message: IncomingMessage) -> BotResponse:
        """
        Traite un message entrant depuis WhatsApp.
        Point d'entrée principal du flux de chat.
        """
        logger.info(f"=== MESSAGE ENTRANT ===")
        logger.info(f"Marchand: {message.merchant_phone} | Client: {message.client_phone}")
        logger.info(f"Message: {message.message[:80]}...")

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

        # 5. Vérifier les cas spéciaux (photos, variantes)
        # Ne pas intercepter en pending_pickup/pending_delivery (le client parle au bot de suivi)
        current_conv_status = conversation.get('status', 'active')
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

        # Récupérer le contexte épisodique (mémoire inter-sessions)
        episodic_context = await episodic_module.get_episodic_context(
            repo=self.client_history,
            merchant_id=merchant['id'],
            client_phone=message.client_phone,
            product_name=product['name']
        )

        bot_response, price_offer, deal_accepted, new_status, send_location = await generate_response(
            client_message=message.message,
            product=product,
            conversation_history=history,
            current_offer=conversation.get('current_offer'),
            conversation_status=current_status,
            negotiation_context=negotiation_context,
            episodic_context=episodic_context
        )

        logger.info(f"Réponse IA: {bot_response[:50] if bot_response else 'NONE'}... | Status: {new_status} | Location: {send_location}")

        # 6. Mettre à jour la conversation
        update_data = {"status": new_status}
        if price_offer:
            update_data["current_offer"] = price_offer
        await self.conversations.update(conversation['id'], **update_data)

        # Si pas de réponse (conversation terminée)
        if bot_response is None:
            # LTM: extraire les faits si la conversation se termine sans vente
            if new_status in ("ended", "abandoned"):
                conv_history = await self.conversations.get_messages(conversation['id'])
                asyncio.create_task(ltm_module.extract_and_save(
                    repo=self.client_history,
                    merchant_id=merchant['id'],
                    client_phone=message.client_phone,
                    history=conv_history,
                    product={"name": product['name'], "price": product['price']},
                    outcome="ended",
                    deepseek_client=get_deepseek_client()
                ))
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

        # 7.5 Envoyer la localisation si demandée (y compris re-demande en pending_pickup)
        # Double-check: si on est en pending_pickup et le message parle de localisation, forcer l'envoi
        if not send_location and new_status == "pending_pickup":
            from ..services.ai.detectors import detect_location_request
            if detect_location_request(message.message):
                send_location = True
                logger.info(f"[LOCATION] Force send_location=True via double-check pour pending_pickup")

        if send_location:
            logger.info(f"[LOCATION] Tentative envoi localisation: merchant={message.merchant_phone}, client={message.client_phone}")
            logger.info(f"[LOCATION] Données marchand: lat={merchant.get('latitude')}, lng={merchant.get('longitude')}, addr={merchant.get('address')}")
            try:
                location_sent = await self.notifications.send_merchant_location_to_client(
                    merchant_phone=message.merchant_phone,
                    client_phone=message.client_phone,
                    merchant_data=merchant
                )
                if location_sent:
                    logger.info(f"[LOCATION] Localisation envoyée avec succès au client {message.client_phone}")
                    await self.notifications.notify_location_sent(
                        merchant_phone=message.merchant_phone,
                        client_phone=message.client_phone,
                        product_name=product['name']
                    )
                else:
                    logger.warning(f"[LOCATION] Échec envoi - send_merchant_location_to_client retourné False pour {message.merchant_phone}")
                    await self.notifications.notify_location_needed(
                        merchant_phone=message.merchant_phone,
                        client_phone=message.client_phone,
                        product_name=product['name']
                    )
            except Exception as e:
                logger.error(f"[LOCATION] Exception lors de l'envoi: {e}", exc_info=True)

        # 7.6 Envoyer le lien vitrine en fin de conversation réussie
        is_transaction_end = (
            (new_status in ("pending_delivery", "pending_pickup") and current_status not in ("pending_delivery", "pending_pickup"))
        )
        if is_transaction_end:
            try:
                await self.notifications.send_storefront_goodbye(
                    merchant_phone=message.merchant_phone,
                    to=message.client_phone,
                    merchant_data=merchant
                )
            except Exception as e:
                logger.warning(f"Erreur envoi lien vitrine: {e}")

        # 8. Gérer les relances automatiques
        await self._handle_follow_ups(
            conversation=conversation,
            merchant=merchant,
            product=product,
            message=message,
            new_status=new_status
        )

        return BotResponse(
            message=bot_response,
            conversation_id=conversation['id'],
            should_notify_merchant=should_notify,
            notification_reason=notification
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
        code = product_code or extract_product_code(message_text)
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

                # Si la conversation existante est en pending_pickup/pending_delivery,
                # le client revient sur le même produit = nouvelle intention d'achat.
                # Fermer l'ancienne et en créer une nouvelle.
                if conversation and conversation.get('status') in ('pending_pickup', 'pending_delivery'):
                    logger.info(f"Conversation {conversation['id']} en {conversation['status']}, "
                                f"client renvoie #code => fermer et créer nouvelle conversation")
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
        Gère les demandes spéciales (photos, variantes).
        Retourne une BotResponse si traité, None sinon.

        IMPORTANT: L'ordre de vérification est crucial!
        1. Variantes EN PREMIER (car "autre photo" = demande de variante, pas de photo du même produit)
        2. Photos du produit principal ensuite
        """
        history = await self.conversations.get_messages(conversation['id'])

        # === 1. VARIANTES EN PREMIER ===
        # Doit être vérifié AVANT les photos car "autre photo" = demande de variante
        if detect_variant_request(message.message):
            group_id = product.get('group_id')
            if group_id:
                variants = await self.products.get_other_variants(product['id'], group_id)
                if variants:
                    images_to_send = []
                    variant_names = []
                    for v in variants:
                        variant_label = v.get('variant_name') or v['name']
                        if v.get('image_path'):
                            # Caption simple et naturel (sans code produit)
                            images_to_send.append({
                                "image_path": v['image_path'],
                                "caption": f"Modèle {variant_label}"
                            })
                        variant_names.append(f"• {variant_label}")

                    variants_text = "\n".join(variant_names)
                    bot_message = f"Voici les autres modèles disponibles:\n\n{variants_text}\n\nLequel t'intéresse?"
                    await self.conversations.add_message(conversation['id'], bot_message, False)

                    logger.info(f"Envoi de {len(images_to_send)} images de variantes au client")

                    return BotResponse(
                        message=bot_message,
                        conversation_id=conversation['id'],
                        should_notify_merchant=False,
                        images_to_send=images_to_send if images_to_send else None
                    )

            # Pas de variantes disponibles
            bot_message = "Ce produit n'est disponible que dans ce modèle pour l'instant."
            await self.conversations.add_message(conversation['id'], bot_message, False)
            return BotResponse(
                message=bot_message,
                conversation_id=conversation['id'],
                should_notify_merchant=False
            )

        # === 2. PHOTO DU PRODUIT PRINCIPAL ===
        if detect_photo_request(message.message):
            # Vérifier si déjà envoyé
            photo_sent = any(
                "Voici le" in msg.get('content', '') or "Voici la" in msg.get('content', '')
                for msg in history if not msg.get('is_from_client')
            )

            if photo_sent:
                bot_message = "Je t'ai déjà envoyé la photo plus haut! Tu peux la regarder. Tu veux autre chose?"
                await self.conversations.add_message(conversation['id'], bot_message, False)
                return BotResponse(
                    message=bot_message,
                    conversation_id=conversation['id'],
                    should_notify_merchant=False
                )

            if product.get('image_path'):
                bot_message = f"Voici le {product['name']}!"
                await self.conversations.add_message(conversation['id'], bot_message, False)
                return BotResponse(
                    message=bot_message,
                    conversation_id=conversation['id'],
                    should_notify_merchant=False,
                    images_to_send=[{
                        "image_path": product['image_path'],
                        "caption": f"{product['name']} - {product['code']} - {product['price']:,.0f} F"
                    }]
                )
            else:
                bot_message = "Désolé, je n'ai pas de photo pour ce produit. Mais tu peux passer au magasin pour le voir!"
                await self.conversations.add_message(conversation['id'], bot_message, False)
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

                    # LTM: extraire les faits de la conversation (non-bloquant)
                    conv_history = await self.conversations.get_messages(conversation['id'])
                    asyncio.create_task(ltm_module.extract_and_save(
                        repo=self.client_history,
                        merchant_id=merchant_obj['id'],
                        client_phone=message.client_phone,
                        history=conv_history,
                        product={"name": product['name'], "price": product['price']},
                        outcome="sale",
                        deepseek_client=get_deepseek_client()
                    ))
            except Exception as e:
                logger.warning(f"Erreur stats vente: {e}")

            # Décrémenter le stock
            updated_product = await self.products.decrement_stock(product['id'])
            if updated_product:
                stock_status = await self.products.check_stock_status(product['id'])

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
