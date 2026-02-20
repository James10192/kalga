"""
Service d'orchestration des commandes marchand
Point d'entrée unique pour toutes les commandes
"""
from typing import Optional
import re
import logging

from .session_manager import session_manager, ProductSession
from .schemas import MerchantMessage, CommandResponse, CommandAction, CreationStep
from .handlers import (
    ProductCreationHandler,
    VariantCreationHandler,
    ProductEditionHandler,
    SalesManagementHandler,
    HelpCommandsHandler,
)
from ...database import get_db

logger = logging.getLogger("kalga.merchant_commands")


class MerchantCommandService:
    """
    Orchestre le traitement des commandes marchand.
    Dispatch vers les handlers appropriés selon le contexte.
    """

    def __init__(self):
        self.product_handler = ProductCreationHandler()
        self.variant_handler = VariantCreationHandler()
        self.edition_handler = ProductEditionHandler()
        self.sales_handler = SalesManagementHandler()
        self.help_handler = HelpCommandsHandler()

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

        # === COMMANDE NON RECONNUE ===
        return CommandResponse(
            response="Je n'ai pas compris. Écris *aide* pour voir les commandes disponibles.",
            action=CommandAction.UNKNOWN
        )

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
            from ...database.connection import get_connection
            async with get_connection() as conn:
                await conn.execute(
                    "UPDATE products SET group_id = ? WHERE id = ?",
                    (group_id, product['id'])
                )
                await conn.commit()

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


# Instance singleton pour injection de dépendances
_service: Optional[MerchantCommandService] = None


def get_merchant_command_service() -> MerchantCommandService:
    """Factory pour l'injection de dépendances FastAPI"""
    global _service
    if _service is None:
        _service = MerchantCommandService()
    return _service
