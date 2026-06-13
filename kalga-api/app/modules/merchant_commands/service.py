"""
Service d'orchestration des commandes marchand
Point d'entrée unique pour toutes les commandes
"""
from typing import Optional, Dict
import asyncio
import re
import logging

from .session_manager import session_manager, ProductSession
from .schemas import MerchantMessage, CommandResponse, CommandAction, CreationStep
from .handlers import (
    ProductCreationHandler,
    VariantCreationHandler,
    BulkVariantCreationHandler,
    ProductEditionHandler,
    SalesManagementHandler,
    HelpCommandsHandler,
)
from ...database import get_db
from ...database.repositories.waitlist_repo import get_waitlist_repository

# Sessions de dialogue stock marchand (produit épuisé → 3 options)
# Format: {merchant_phone: {"step": str, "product_id": int, "product_code": str, ...}}
_stock_sessions: Dict[str, dict] = {}
_stock_sessions_lock = asyncio.Lock()

logger = logging.getLogger("kalga.merchant_commands")


class MerchantCommandService:
    """
    Orchestre le traitement des commandes marchand.
    Dispatch vers les handlers appropriés selon le contexte.
    """

    def __init__(self):
        self.product_handler = ProductCreationHandler()
        self.variant_handler = VariantCreationHandler()
        self.bulk_variant_handler = BulkVariantCreationHandler()
        self.edition_handler = ProductEditionHandler()
        self.sales_handler = SalesManagementHandler()
        self.help_handler = HelpCommandsHandler()
        self.waitlist_repo = get_waitlist_repository()

    async def process_command(self, msg: MerchantMessage) -> CommandResponse:
        """
        Point d'entrée principal pour traiter une commande marchand.
        """
        logger.debug(
            f"Commande reçue: phone={msg.merchant_phone}, "
            f"message='{msg.message[:50]}', image={msg.image_path is not None}"
        )

        db = await get_db()
        merchant_phone = msg.merchant_phone
        message = msg.message.strip()
        message_lower = message.lower()

        # Nettoyer les sessions expirées
        session_manager.cleanup_expired()

        # Vérifier si le marchand existe
        merchant = await db.get_merchant_by_phone(merchant_phone)
        if not merchant and merchant_phone.startswith('225') and len(merchant_phone) == 12:
            # Fallback: numéro ivoirien sans le 0 (225XXXXXXXXX → 2250XXXXXXXXX)
            merchant = await db.get_merchant_by_phone('225' + '0' + merchant_phone[3:])
        if not merchant:
            return CommandResponse(
                response="Tu n'es pas encore enregistré comme marchand. "
                         "Connecte-toi d'abord via le dashboard.",
                action=CommandAction.ERROR
            )

        # Vérifier si une session de création est en cours
        session = session_manager.get(merchant_phone)

        if session:
            # Permettre d'annuler avec certaines commandes
            if message_lower in ['mes produits', 'liste', 'produits', 'aide', 'help', 'menu', '?']:
                session_manager.delete(merchant_phone)
                logger.info(f"Session annulée automatiquement: {merchant_phone}")
                session = None
            else:
                # Traiter l'étape de création
                return await self._handle_creation_step(
                    session, message, msg.image_path, merchant, db
                )

        # Session dialogue stock en cours (dialogue proactif 3 options)
        async with _stock_sessions_lock:
            if merchant['phone'] in _stock_sessions:
                stock_resp = await self._handle_stock_session(
                    merchant_phone=merchant['phone'],
                    message_lower=message_lower,
                    merchant=merchant,
                    db=db
                )
                if stock_resp is not None:
                    return stock_resp

        # Pas de session active - traiter comme commande normale
        return await self._handle_command(
            message, message_lower, msg.image_path, merchant, db
        )

    async def _handle_creation_step(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        merchant: dict,
        db
    ) -> CommandResponse:
        """Traite une étape de création (produit ou variante)"""
        # Utiliser un verrou pour éviter les race conditions
        lock = await session_manager.get_lock(session.merchant_phone)

        async with lock:
            # Re-vérifier que la session existe
            current_session = session_manager.get(session.merchant_phone)
            if not current_session:
                logger.debug("Session disparue après verrou")
                return CommandResponse(response="", action=CommandAction.IGNORED)

            # Annulation manuelle
            if message.lower() in ['annuler', 'cancel', 'stop']:
                session_manager.delete(session.merchant_phone)
                return CommandResponse(
                    response="❌ Création annulée. Écris *produit* pour recommencer.",
                    action=CommandAction.CANCELLED
                )

            # Dispatch vers le bon handler selon l'étape
            step = current_session.step

            # Étapes de création de produit
            product_steps = {
                CreationStep.NAME, CreationStep.PRICE, CreationStep.MIN_PRICE,
                CreationStep.DESCRIPTION, CreationStep.IMAGE, CreationStep.ASK_VARIANT
            }

            # Étapes de création de variante
            variant_steps = {
                CreationStep.VARIANT_NAME, CreationStep.VARIANT_IMAGE,
                CreationStep.ASK_ANOTHER_VARIANT
            }

            # Étapes de création de variantes en lot
            bulk_variant_steps = {
                CreationStep.VARIANT_BATCH_PHOTOS,
                CreationStep.VARIANT_BATCH_CONFIRM,
            }

            # Étapes de modification de produit
            edit_steps = {
                CreationStep.EDIT_CHOOSE, CreationStep.EDIT_VALUE,
                CreationStep.EDIT_CONFIRM
            }

            if step in product_steps:
                return await self.product_handler.handle(
                    current_session, message, image_path, db
                )
            elif step in variant_steps:
                return await self.variant_handler.handle(
                    current_session, message, image_path, db
                )
            elif step in bulk_variant_steps:
                return await self.bulk_variant_handler.handle(
                    current_session, message, image_path, db
                )
            elif step in edit_steps:
                return await self.edition_handler.handle(
                    current_session, message, image_path, db
                )
            else:
                logger.error(f"Étape inconnue: {step}")
                session_manager.delete(session.merchant_phone)
                return CommandResponse(
                    response="Erreur interne. Écris *produit* pour recommencer.",
                    action=CommandAction.ERROR
                )

    async def _handle_command(
        self,
        message: str,
        message_lower: str,
        image_path: Optional[str],
        merchant: dict,
        db
    ) -> CommandResponse:
        """Traite une commande normale (pas en session de création)"""

        # === COMMANDES DE VENTE ===
        if message_lower in ['!ok', '!livré', '!livre', '!fait', '!done', '!termine', '!terminé']:
            return await self.sales_handler.handle_complete_sale(merchant, db)

        if message_lower in ['!annuler', '!cancel', '!annule']:
            return await self.sales_handler.handle_cancel_sale(merchant, db)

        # === COMMANDES D'AIDE ===
        if message_lower in ['aide', 'help', '?', 'menu']:
            return await self.help_handler.handle_help()

        # === COMMANDES STOCK NATURELLES ===
        # "stock riz 50" / "stock #K001 50"
        stock_update_match = re.search(
            r'^stock\s+(.+?)\s+(\d+)$', message_lower
        )
        if stock_update_match:
            return await self._handle_stock_update_command(
                stock_update_match, merchant, db
            )

        # "épuisé: attiéké" / "epuise attiéké" / "rupture: riz"
        epuise_match = re.search(
            r'^(?:épuisé|epuise|rupture)[:\s]+(.+)$', message_lower
        )
        if epuise_match:
            return await self._handle_mark_out_of_stock(epuise_match, merchant, db)

        # "prix attiéké 500" / "prix #K001 15000"
        prix_match = re.search(
            r'^prix\s+(.+?)\s+(\d[\d\s]*)$', message_lower
        )
        if prix_match:
            return await self._handle_price_update_command(prix_match, merchant, db)

        # === CRÉATION DE PRODUIT ===
        if message_lower in ['produit', 'nouveau', 'nouveau produit', 'ajouter', 'ajouter produit', '/produit']:
            session_manager.create(
                merchant_phone=merchant['phone'],
                step=CreationStep.NAME,
                data={"merchant_id": merchant['id']}
            )
            return CommandResponse(
                response="📦 *Création d'un nouveau produit*\n\n"
                         "Étape 1/5: Quel est le *nom* du produit?",
                action=CommandAction.PRODUCT_CREATE_START
            )

        # === CRÉATION DE VARIANTES EN LOT (liste) — prioritaire sur 'variante' ===
        # La liste doit être sur la MÊME ligne que la commande ([ \t]+, pas \s+ qui
        # avalerait un \n) ; pas de re.DOTALL pour ne pas capturer les lignes suivantes.
        bulk_match = re.search(
            r'variantes?\s+#?(K?\d{3})[ \t]+(.+)', message, re.IGNORECASE
        )
        if bulk_match:
            return await self._start_bulk_variants(bulk_match, merchant, db)

        # === CRÉATION DE VARIANTE ===
        variante_match = re.search(r'variante\s+#?(K?\d{3})', message_lower, re.IGNORECASE)
        if variante_match:
            return await self._start_variant_creation(
                variante_match, merchant, db
            )

        # === MODIFICATION DE PRODUIT ===
        modifier_match = re.search(r'modifier\s+#?(K?\d{3})', message_lower, re.IGNORECASE)
        if modifier_match:
            return await self._start_product_edition(modifier_match, merchant, db)

        # === LISTE DES PRODUITS ===
        if message_lower in ['mes produits', 'liste', 'produits', 'mes articles', '/liste']:
            return await self.help_handler.handle_list_products(merchant, db)

        # === SUPPRESSION DE PRODUIT ===
        if message_lower.startswith('supprimer') or message_lower.startswith('retirer'):
            return await self.help_handler.handle_delete_product(message, merchant, db)

        # === ORPHELINS DE SESSION (bug terrain n°11) ===
        # Les sessions vivent en mémoire : un redémarrage de l'API les efface.
        # Une photo ou « fini »/« annuler » hors session = un marchand au milieu
        # d'un flux perdu → lui répondre TOUJOURS (le bridge jette les UNKNOWN).
        if image_path and not message:
            return CommandResponse(
                response=(
                    "📸 J'ai bien reçu ta photo, mais aucune création n'est en cours "
                    "(la session a peut-être expiré).\n\n"
                    "• Écris *produit* pour créer un produit\n"
                    "• Écris *variante #K0xx* pour ajouter une variante\n"
                    "Puis renvoie tes photos 👍"
                ),
                action=CommandAction.ERROR
            )

        if message_lower in ['fini', 'fin', 'terminé', 'termine']:
            return CommandResponse(
                response=(
                    "⚠️ Aucun envoi de photos en cours (la session a peut-être expiré).\n\n"
                    "Recommence : écris *produit*, puis réponds *photos* à la dernière "
                    "étape et renvoie tes images."
                ),
                action=CommandAction.ERROR
            )

        if message_lower in ['annuler', 'cancel', 'stop']:
            return CommandResponse(
                response="Rien à annuler — aucune création en cours. 👍",
                action=CommandAction.CANCELLED
            )

        # === COMMANDE NON RECONNUE ===
        return CommandResponse(
            response="Je n'ai pas compris. Écris *aide* pour voir les commandes disponibles.",
            action=CommandAction.UNKNOWN
        )

    async def _find_product_by_name_or_code(
        self,
        query: str,
        merchant_id: int,
        db
    ):
        """Cherche un produit par code (#K001) ou par nom approximatif"""
        query = query.strip()
        # Par code
        if re.match(r'#?k?\d{3}', query, re.IGNORECASE):
            code = query.upper()
            if not code.startswith('#'):
                code = f"#{code}"
            if not code.startswith('#K'):
                code = f"#K{code[1:]}"
            return await db.get_product_by_code(code)
        # Par nom (recherche partielle)
        products = await db.get_products_by_merchant(merchant_id)
        query_lower = query.lower()
        for p in products:
            if query_lower in p['name'].lower():
                return p
        return None

    async def _handle_stock_update_command(
        self,
        match: re.Match,
        merchant: dict,
        db
    ) -> CommandResponse:
        """Traite: 'stock [produit] [quantité]'"""
        product_query = match.group(1).strip()
        quantity = int(match.group(2))

        product = await self._find_product_by_name_or_code(product_query, merchant['id'], db)
        if not product or product['merchant_id'] != merchant['id']:
            return CommandResponse(
                response=f"❌ Produit '{product_query}' non trouvé. Vérifie le nom ou le code.",
                action=CommandAction.ERROR
            )

        # Mettre à jour le stock
        await db.update_product(product['id'], stock_quantity=quantity)

        # Logger l'événement stock
        try:
            await self.waitlist_repo.log_stock_event(
                merchant_id=merchant['id'],
                product_id=product['id'],
                event_type='restock',
                quantity_delta=quantity,
                quantity_after=quantity,
                notes=f"Commande WhatsApp: stock {product_query} {quantity}"
            )
        except Exception:
            pass

        # Waitlist : notifier si clients en attente
        waitlist_count = await self.waitlist_repo.get_waitlist_count(product['id'])
        waitlist_text = ""
        if waitlist_count > 0 and quantity > 0:
            waitlist_text = (
                f"\n\n📢 *{waitlist_count} client{'s' if waitlist_count > 1 else ''} "
                f"en attente* seront notifiés automatiquement."
            )
            # Déclencher le broadcast (non-bloquant)
            import asyncio
            from ...services.stock_alert_service import get_stock_alert_service
            store_name = merchant.get('business_name') or merchant.get('name') or ''
            asyncio.create_task(
                get_stock_alert_service().broadcast_waitlist_on_restock(
                    merchant_id=merchant['id'],
                    merchant_phone=merchant['phone'],
                    product_id=product['id'],
                    product_name=product['name'],
                    product_code=product['code'],
                    new_quantity=quantity,
                    store_name=store_name
                )
            )

        return CommandResponse(
            response=(
                f"✅ Stock mis à jour!\n\n"
                f"📦 *{product['name']}* ({product['code']})\n"
                f"🔢 Nouveau stock: *{quantity}* unité{'s' if quantity > 1 else ''}"
                f"{waitlist_text}"
            ),
            action=CommandAction.PRODUCT_EDITED
        )

    async def _handle_mark_out_of_stock(
        self,
        match: re.Match,
        merchant: dict,
        db
    ) -> CommandResponse:
        """Traite: 'épuisé: [produit]'"""
        product_query = match.group(1).strip()
        product = await self._find_product_by_name_or_code(product_query, merchant['id'], db)
        if not product or product['merchant_id'] != merchant['id']:
            return CommandResponse(
                response=f"❌ Produit '{product_query}' non trouvé.",
                action=CommandAction.ERROR
            )

        await db.update_product(product['id'], stock_quantity=0)

        try:
            await self.waitlist_repo.log_stock_event(
                merchant_id=merchant['id'],
                product_id=product['id'],
                event_type='out_of_stock',
                quantity_delta=0,
                quantity_after=0,
                notes="Marqué épuisé via WhatsApp marchand"
            )
        except Exception:
            pass

        return CommandResponse(
            response=(
                f"✅ *{product['name']}* ({product['code']}) marqué comme épuisé.\n\n"
                f"Le bot informera les prochains clients et leur proposera la liste d'attente."
            ),
            action=CommandAction.PRODUCT_EDITED
        )

    async def _handle_price_update_command(
        self,
        match: re.Match,
        merchant: dict,
        db
    ) -> CommandResponse:
        """Traite: 'prix [produit] [montant]'"""
        product_query = match.group(1).strip()
        price_str = match.group(2).replace(' ', '')
        try:
            new_price = float(price_str)
        except ValueError:
            return CommandResponse(
                response="❌ Prix invalide. Exemple: *prix attiéké 1500*",
                action=CommandAction.ERROR
            )

        product = await self._find_product_by_name_or_code(product_query, merchant['id'], db)
        if not product or product['merchant_id'] != merchant['id']:
            return CommandResponse(
                response=f"❌ Produit '{product_query}' non trouvé.",
                action=CommandAction.ERROR
            )

        await db.update_product(product['id'], price=new_price)

        return CommandResponse(
            response=(
                f"✅ Prix mis à jour!\n\n"
                f"📦 *{product['name']}* ({product['code']})\n"
                f"💰 Nouveau prix: *{new_price:,.0f} F*"
            ),
            action=CommandAction.PRODUCT_EDITED
        )

    async def _handle_stock_session(
        self,
        merchant_phone: str,
        message_lower: str,
        merchant: dict,
        db
    ):
        """
        Gère le dialogue proactif 3 options pour un produit épuisé.
        Session créée par StockAlertService._send_merchant_stock_dialogue().
        """
        session = _stock_sessions.get(merchant_phone)
        if not session:
            return None

        step = session.get('step')
        product_id = session.get('product_id')
        product_code = session.get('product_code')
        product_name = session.get('product_name', 'ce produit')

        if step == 'awaiting_choice':
            if message_lower in ['1', 'oui', 'yes', 'ok', 'ouais']:
                # Le stock revient → demander la quantité
                _stock_sessions[merchant_phone] = {**session, 'step': 'awaiting_quantity'}
                return CommandResponse(
                    response=(
                        f"✅ Super!\n\nQuelle est la nouvelle quantité en stock pour "
                        f"*{product_name}* ({product_code}) ?"
                    ),
                    action=CommandAction.PRODUCT_EDIT_STEP
                )
            elif message_lower in ['2', 'non', 'no', 'pas encore', 'nan']:
                del _stock_sessions[merchant_phone]
                return CommandResponse(
                    response="Ok, je te re-sollicite dans quelques jours si c'est toujours épuisé.",
                    action=CommandAction.IGNORED
                )
            elif message_lower in ['3', 'supprimer', 'delete', 'retirer']:
                del _stock_sessions[merchant_phone]
                # Désactiver le produit
                await db.update_product(product_id, is_available=0)
                return CommandResponse(
                    response=f"✅ *{product_name}* ({product_code}) a été supprimé.",
                    action=CommandAction.DELETE
                )
            else:
                return CommandResponse(
                    response="Réponds *1* (oui), *2* (non) ou *3* (supprimer).",
                    action=CommandAction.ASK_AGAIN
                )

        elif step == 'awaiting_quantity':
            try:
                quantity = int(re.search(r'\d+', message_lower).group())
            except Exception:
                return CommandResponse(
                    response="Envoie juste un nombre. Ex: *50*",
                    action=CommandAction.ASK_AGAIN
                )

            del _stock_sessions[merchant_phone]

            # Mettre à jour le stock
            await db.update_product(product_id, stock_quantity=quantity)

            # Notifier la waitlist
            waitlist_count = await self.waitlist_repo.get_waitlist_count(product_id)
            waitlist_text = ""
            if waitlist_count > 0:
                import asyncio
                from ...services.stock_alert_service import get_stock_alert_service
                store_name = merchant.get('business_name') or merchant.get('name') or ''
                asyncio.create_task(
                    get_stock_alert_service().broadcast_waitlist_on_restock(
                        merchant_id=merchant['id'],
                        merchant_phone=merchant['phone'],
                        product_id=product_id,
                        product_name=product_name,
                        product_code=product_code,
                        new_quantity=quantity,
                        store_name=store_name
                    )
                )
                waitlist_text = (
                    f"\n\n📢 *{waitlist_count} client{'s' if waitlist_count > 1 else ''} "
                    f"en attente* seront notifiés!"
                )

            return CommandResponse(
                response=(
                    f"✅ Stock mis à jour!\n\n"
                    f"📦 *{product_name}* ({product_code})\n"
                    f"🔢 Nouveau stock: *{quantity}* unité{'s' if quantity > 1 else ''}"
                    f"{waitlist_text}"
                ),
                action=CommandAction.PRODUCT_EDITED
            )

        return None

    async def _start_bulk_variants(
        self, match: re.Match, merchant: dict, db
    ) -> CommandResponse:
        """Crée plusieurs variantes d'un coup : 'variantes #K001 rouge, bleu, noir'."""
        from .handlers.bulk_variant_creation import parse_variant_list
        code = f"#K{match.group(1).replace('K', '').replace('k', '')}"
        names = parse_variant_list(match.group(2))
        product = await db.get_product_by_code(code)
        if not product or product['merchant_id'] != merchant['id']:
            return CommandResponse(
                response=f"Produit {code} non trouvé ou non autorisé.",
                action=CommandAction.ERROR,
            )
        if not names:
            return CommandResponse(
                response="Donne au moins une variante. Ex: *variantes #K001 rouge, bleu*",
                action=CommandAction.ERROR,
            )
        group_id = product.get('group_id')
        if not group_id:
            group_id = await db.generate_group_id()
            await db.update_product(product['id'], group_id=group_id)
        session_manager.create(
            merchant_phone=merchant['phone'],
            step=CreationStep.VARIANT_BATCH_CONFIRM,
            data={
                "merchant_id": merchant['id'], "name": product['name'],
                "price": product['price'], "min_price": product['min_price'],
                "description": product.get('description'), "group_id": group_id,
                "original_code": code,
                "pending_variants": [
                    {"variant_name": n, "image_path": None} for n in names
                ],
            },
        )
        session = session_manager.get(merchant['phone'])
        return await self.bulk_variant_handler.handle(session, "ok", None, db)

    async def _start_variant_creation(
        self,
        match: re.Match,
        merchant: dict,
        db
    ) -> CommandResponse:
        """Démarre la création d'une variante pour un produit existant"""
        code = f"#K{match.group(1).replace('K', '').replace('k', '')}"
        product = await db.get_product_by_code(code)

        if not product:
            return CommandResponse(
                response=f"Produit {code} non trouvé.",
                action=CommandAction.ERROR
            )

        if product['merchant_id'] != merchant['id']:
            return CommandResponse(
                response="Ce produit ne t'appartient pas.",
                action=CommandAction.ERROR
            )

        # Générer ou récupérer le group_id
        group_id = product.get('group_id')
        if not group_id:
            group_id = await db.generate_group_id()
            await db.update_product(product['id'], group_id=group_id)

        # Créer la session
        session_manager.create(
            merchant_phone=merchant['phone'],
            step=CreationStep.VARIANT_NAME,
            data={
                "merchant_id": merchant['id'],
                "group_id": group_id,
                "name": product['name'],
                "price": product['price'],
                "min_price": product['min_price'],
                "description": product.get('description'),
                "is_variant": True,
                "original_code": code,
                "variant_created": False,
                "image_path": None
            }
        )

        return CommandResponse(
            response=f"📦 *Ajout d'une variante pour {product['name']} ({code})*\n\n"
                     "Quel est le *nom de cette variante*? (ex: Rouge, Bleu, XL, etc.)",
            action=CommandAction.VARIANT_CREATE_START
        )

    async def _start_product_edition(
        self,
        match: re.Match,
        merchant: dict,
        db
    ) -> CommandResponse:
        """Démarre la modification d'un produit existant"""
        code = f"#K{match.group(1).replace('K', '').replace('k', '')}"
        product = await db.get_product_by_code(code)

        if not product:
            return CommandResponse(
                response=f"Produit {code} non trouvé.",
                action=CommandAction.ERROR
            )

        if product['merchant_id'] != merchant['id']:
            return CommandResponse(
                response="Ce produit ne t'appartient pas.",
                action=CommandAction.ERROR
            )

        # Créer la session de modification
        session_manager.create(
            merchant_phone=merchant['phone'],
            step=CreationStep.EDIT_CHOOSE,
            data={
                "merchant_id": merchant['id'],
                "product_id": product['id'],
                "product_code": code,
                "current_price": product['price'],
                "current_min_price": product['min_price'],
            }
        )

        desc = product.get('description') or "Aucune"
        img = "Oui 📷" if product.get('image_path') else "Non"

        return CommandResponse(
            response=(
                f"✏️ *Modification de {product['name']} ({code})*\n\n"
                f"📦 Nom: *{product['name']}*\n"
                f"💰 Prix: *{product['price']:,.0f} F*\n"
                f"💰 Prix minimum: *{product['min_price']:,.0f} F*\n"
                f"📝 Description: {desc}\n"
                f"📷 Image: {img}\n\n"
                "Que veux-tu modifier?\n\n"
                "1️⃣ *nom*\n2️⃣ *prix*\n3️⃣ *prix minimum*\n4️⃣ *description*\n5️⃣ *image*"
            ),
            action=CommandAction.PRODUCT_EDIT_START
        )


async def register_stock_dialogue_session(
    merchant_phone: str,
    product_id: int,
    product_code: str,
    product_name: str
) -> None:
    """
    Enregistre une session de dialogue stock proactif.
    Appelé par StockAlertService après envoi du message 3 options.
    """
    async with _stock_sessions_lock:
        _stock_sessions[merchant_phone] = {
            'step': 'awaiting_choice',
            'product_id': product_id,
            'product_code': product_code,
            'product_name': product_name
        }


# Instance singleton pour injection de dépendances
_service: Optional[MerchantCommandService] = None


def get_merchant_command_service() -> MerchantCommandService:
    """Factory pour l'injection de dépendances FastAPI"""
    global _service
    if _service is None:
        _service = MerchantCommandService()
    return _service
