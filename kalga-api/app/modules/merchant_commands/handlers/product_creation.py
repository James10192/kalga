"""
Handler pour la création de nouveaux produits
Gère le flux complet: nom → prix → prix min → description → image
"""
from typing import Optional, Any
import logging

from .base import BaseHandler, PriceExtractor
from ..session_manager import ProductSession, session_manager
from ..schemas import CommandResponse, CommandAction, CreationStep

logger = logging.getLogger("kalga.handlers.product")


class ProductCreationHandler(BaseHandler):
    """Gère le flux de création d'un nouveau produit"""

    STEPS = {
        CreationStep.NAME: "_handle_name",
        CreationStep.PRICE: "_handle_price",
        CreationStep.MIN_PRICE: "_handle_min_price",
        CreationStep.DESCRIPTION: "_handle_description",
        CreationStep.IMAGE: "_handle_image",
        CreationStep.ASK_VARIANT: "_handle_ask_variant",
    }

    async def handle(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Dispatch vers le handler approprié selon l'étape"""
        step = session.step
        handler_name = self.STEPS.get(step)

        if not handler_name:
            logger.warning(f"Étape non gérée par ProductCreationHandler: {step}")
            return self._error("Erreur interne: étape non reconnue")

        handler = getattr(self, handler_name)
        return await handler(session, message, image_path, db)

    async def _handle_name(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Étape 1: Nom du produit"""
        name = message.strip()
        if not name or len(name) < 2:
            return self._error("Le nom doit contenir au moins 2 caractères")

        session.set_data("name", name)
        session.update_step(CreationStep.PRICE)

        return self._response(
            f"✅ Nom: *{name}*\n\n"
            "Étape 2/5: Quel est le *prix de vente*? (en FCFA)\n\n"
            "Exemple: 15000 ou 15k",
            CommandAction.PRODUCT_STEP
        )

    async def _handle_price(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Étape 2: Prix de vente"""
        price = PriceExtractor.extract(message)

        if not price or price < 100:
            return self._error(
                "Prix invalide. Entre un montant valide.\n\n"
                "Exemple: 15000 ou 15k"
            )

        session.set_data("price", price)
        session.update_step(CreationStep.MIN_PRICE)

        return self._response(
            f"✅ Prix: *{price:,.0f} F*\n\n"
            "Étape 3/5: Quel est le *prix minimum* que tu acceptes?\n\n"
            "Exemple: 12000 ou 12k",
            CommandAction.PRODUCT_STEP
        )

    async def _handle_min_price(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Étape 3: Prix minimum"""
        min_price = PriceExtractor.extract(message)
        price = session.get_data("price")

        if not min_price or min_price < 100:
            return self._error(
                "Prix invalide. Entre un montant valide.\n\n"
                "Exemple: 12000 ou 12k"
            )

        if min_price > price:
            return self._error(
                f"Le prix minimum doit être inférieur au prix de vente ({price:,.0f} F).\n\n"
                "Entre un prix minimum:"
            )

        session.set_data("min_price", min_price)
        session.update_step(CreationStep.DESCRIPTION)

        return self._response(
            f"✅ Prix minimum: *{min_price:,.0f} F*\n\n"
            "Étape 4/5: Ajoute une *description* (ou écris *passer* pour ignorer)",
            CommandAction.PRODUCT_STEP
        )

    async def _handle_description(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Étape 4: Description"""
        if message.lower() not in ['passer', 'skip', 'non', '-']:
            session.set_data("description", message.strip())
        else:
            session.set_data("description", None)

        session.update_step(CreationStep.IMAGE)

        return self._response(
            "✅ Description enregistrée!\n\n"
            "Étape 5/5: Envoie *UNE* photo du produit (ou écris *passer* si pas d'image)\n\n"
            "⚠️ Une seule image à la fois!",
            CommandAction.PRODUCT_STEP
        )

    async def _handle_image(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Étape 5: Image et création du produit"""
        # Protection anti-doublon
        if session.get_data("product_created"):
            logger.debug("Produit déjà créé, message tardif ignoré")
            return self._ignored()

        # Image dupliquée (WhatsApp envoie parfois plusieurs fois)
        if session.get_data("image_path") and image_path and not message.strip():
            logger.debug("Image déjà reçue, ignorant le doublon")
            return self._ignored()

        # Traiter l'image ou "passer"
        if image_path:
            session.set_data("image_path", image_path)
        elif message.lower() not in ['passer', 'skip', 'non', '-']:
            return self._error(
                "Envoie une *photo* ou écris *passer* pour continuer sans image"
            )

        # Marquer comme en cours de création
        session.set_data("product_created", True)

        # Créer le produit
        try:
            product = await db.create_product(
                merchant_id=session.get_data("merchant_id"),
                name=session.get_data("name"),
                price=session.get_data("price"),
                min_price=session.get_data("min_price"),
                description=session.get_data("description"),
                image_path=session.get_data("image_path")
            )

            img_msg = "📷 Image enregistrée!\n" if session.get_data("image_path") else ""

            # Passer à la question des variantes
            session.update_step(CreationStep.ASK_VARIANT)
            session.set_data("product_code", product['code'])
            session.set_data("product_id", product['id'])

            return self._response(
                f"✅ *Produit créé!*\n\n"
                f"📦 *{product['name']}*\n"
                f"🏷️ Code: *{product['code']}*\n"
                f"💰 Prix: {product['price']:,.0f} F\n"
                f"{img_msg}"
                "🎨 Tu as *d'autres variantes* (couleurs, tailles, modèles)?\n\n"
                "• Tape la liste : ex. *rouge, bleu, noir* → créées d'un coup\n"
                "• Ou écris *photos* pour envoyer un lot (je détecte les couleurs)\n"
                "• Ou *oui* pour les ajouter une par une\n"
                "• Ou *non* pour terminer",
                CommandAction.PRODUCT_CREATED,
                product_code=product['code']
            )

        except Exception as e:
            logger.error(f"Erreur création produit: {e}")
            session_manager.delete(session.merchant_phone)
            return self._error(f"Erreur lors de la création: {str(e)}")

    async def _handle_ask_variant(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Demande si le marchand veut ajouter des variantes"""
        msg_lower = message.lower().strip()

        # Mode lot — liste de variantes (présence d'une virgule = liste explicite)
        if "," in message:
            from .bulk_variant_creation import parse_variant_list, BulkVariantCreationHandler
            names = parse_variant_list(message)
            if names:
                group_id = await self._ensure_group_id(session, db)
                session.update_step(CreationStep.VARIANT_BATCH_CONFIRM)
                session.set_data("group_id", group_id)
                session.set_data("original_code", session.get_data("product_code"))
                session.set_data(
                    "pending_variants",
                    [{"variant_name": n, "image_path": None} for n in names],
                )
                return await BulkVariantCreationHandler().handle(session, "ok", None, db)

        # Mode lot — envoi de photos
        if msg_lower in ("photos", "photo"):
            group_id = await self._ensure_group_id(session, db)
            session.update_step(CreationStep.VARIANT_BATCH_PHOTOS)
            session.set_data("group_id", group_id)
            session.set_data("original_code", session.get_data("product_code"))
            session.set_data("batch_photos", [])
            return self._response(
                "📸 Envoie tes photos une par une, puis écris *fini*.\n"
                "Je détecte la couleur de chacune automatiquement.",
                CommandAction.VARIANT_BATCH_STEP,
            )

        if msg_lower in ['oui', 'yes', 'o', 'y', 'ok', 'ouais', '1']:
            # Préparer pour la création de variante
            product_code = session.get_data("product_code")
            product = await db.get_product_by_code(product_code)

            if not product:
                session_manager.delete(session.merchant_phone)
                return self._error("Erreur: produit non trouvé.")

            # Générer ou récupérer le group_id
            group_id = product.get('group_id')
            if not group_id:
                group_id = await db.generate_group_id()
                # Mettre à jour le produit avec le group_id
                await db.update_product(product['id'], group_id=group_id)

            # Configurer la session pour les variantes
            session.update_step(CreationStep.VARIANT_NAME)
            session.set_data("group_id", group_id)
            session.set_data("original_code", product_code)
            session.set_data("is_variant", True)
            session.set_data("variant_created", False)
            session.set_data("image_path", None)

            return self._response(
                f"📦 *Ajout d'une variante pour {session.get_data('name')}*\n\n"
                "Quel est le *nom de cette variante*?\n"
                "(ex: Rouge, Bleu, Taille XL, etc.)",
                CommandAction.VARIANT_CREATE_START
            )

        elif msg_lower in ['non', 'no', 'n', 'nope', 'nan', '0', 'stop', 'fini', 'terminer']:
            product_code = session.get_data("product_code")
            session_manager.delete(session.merchant_phone)

            return self._response(
                "✅ *Parfait!*\n\n"
                f"👉 Ajoute *{product_code}* dans ton Status WhatsApp pour commencer à vendre!\n\n"
                f"💡 Pour ajouter des variantes plus tard:\n"
                f"Écris *variante {product_code}*",
                CommandAction.PRODUCT_COMPLETE
            )

        else:
            return self._response(
                "Réponds *oui* pour ajouter une autre couleur/modèle\n"
                "Ou *non* pour terminer",
                CommandAction.ASK_AGAIN
            )

    async def _ensure_group_id(self, session: ProductSession, db: Any) -> str:
        """Retourne le group_id du produit de base, en le générant si absent."""
        product_code = session.get_data("product_code")
        product = await db.get_product_by_code(product_code)
        group_id = product.get("group_id") if product else None
        if not group_id:
            group_id = await db.generate_group_id()
            # Persister le group_id sur le produit de base uniquement s'il existe encore
            # (le produit a pu être supprimé entre le wizard et cette réponse).
            if product:
                await db.update_product(product["id"], group_id=group_id)
        return group_id
