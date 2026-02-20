"""
Handler pour la création de variantes de produits
Gère le flux: nom variante → image → demande autre variante
"""
from typing import Optional, Any
import logging

from .base import BaseHandler
from ..session_manager import ProductSession, session_manager
from ..schemas import CommandResponse, CommandAction, CreationStep

logger = logging.getLogger("kalga.handlers.variant")


class VariantCreationHandler(BaseHandler):
    """Gère le flux de création de variantes"""

    STEPS = {
        CreationStep.VARIANT_NAME: "_handle_variant_name",
        CreationStep.VARIANT_IMAGE: "_handle_variant_image",
        CreationStep.ASK_ANOTHER_VARIANT: "_handle_ask_another_variant",
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
            logger.warning(f"Étape non gérée par VariantCreationHandler: {step}")
            return self._error("Erreur interne: étape non reconnue")

        handler = getattr(self, handler_name)
        return await handler(session, message, image_path, db)

    async def _handle_variant_name(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Étape: Nom de la variante"""
        variant_name = message.strip()
        if not variant_name or len(variant_name) < 1:
            return self._error("Le nom de la variante ne peut pas être vide")

        session.set_data("variant_name", variant_name)
        session.update_step(CreationStep.VARIANT_IMAGE)

        return self._response(
            f"✅ Variante: *{variant_name}*\n\n"
            "Envoie *UNE* photo de cette variante (ou écris *passer* si pas d'image)\n\n"
            "⚠️ Une seule image à la fois!",
            CommandAction.VARIANT_STEP
        )

    async def _handle_variant_image(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Étape: Image de la variante et création"""
        # Protection anti-doublon
        if session.get_data("variant_created"):
            logger.debug("Variante déjà créée, message tardif ignoré")
            return self._ignored()

        # Image dupliquée
        if session.get_data("image_path") and image_path and not message.strip():
            logger.debug("Image variante déjà reçue, ignorant le doublon")
            return self._ignored()

        # Traiter l'image ou "passer"
        if image_path:
            session.set_data("image_path", image_path)
        elif message.lower() not in ['passer', 'skip', 'non', '-']:
            return self._error(
                "Envoie une *photo* ou écris *passer* pour continuer sans image"
            )

        # Marquer comme en cours de création
        session.set_data("variant_created", True)

        # Créer la variante
        try:
            product = await db.create_product(
                merchant_id=session.get_data("merchant_id"),
                name=f"{session.get_data('name')} - {session.get_data('variant_name')}",
                price=session.get_data("price"),
                min_price=session.get_data("min_price"),
                description=session.get_data("description"),
                image_path=session.get_data("image_path"),
                group_id=session.get_data("group_id"),
                variant_name=session.get_data("variant_name")
            )

            img_msg = "📷 Image enregistrée!\n" if session.get_data("image_path") else ""

            # Préparer pour une autre variante potentielle
            session.update_step(CreationStep.ASK_ANOTHER_VARIANT)
            session.set_data("last_variant_code", product['code'])
            session.set_data("image_path", None)  # Reset pour prochaine variante

            return self._response(
                "✅ *Variante créée!*\n\n"
                f"📦 *{product['name']}*\n"
                f"🏷️ Code: *{product['code']}*\n"
                f"{img_msg}"
                "🎨 Tu veux ajouter *une autre couleur/modèle*?\n\n"
                "Réponds *oui* pour continuer\n"
                "Réponds *non* pour terminer",
                CommandAction.VARIANT_CREATED,
                product_code=product['code']
            )

        except Exception as e:
            logger.error(f"Erreur création variante: {e}")
            session_manager.delete(session.merchant_phone)
            return self._error(f"Erreur lors de la création: {str(e)}")

    async def _handle_ask_another_variant(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Demande si le marchand veut ajouter une autre variante"""
        msg_lower = message.lower().strip()

        if msg_lower in ['oui', 'yes', 'o', 'y', 'ok', 'ouais', '1']:
            # Continuer avec une nouvelle variante
            session.update_step(CreationStep.VARIANT_NAME)
            session.set_data("variant_created", False)
            session.set_data("image_path", None)

            return self._response(
                f"📦 *Ajout d'une autre variante pour {session.get_data('name')}*\n\n"
                "Quel est le *nom de cette variante*?\n"
                "(ex: Noir, Rose, Taille M, etc.)",
                CommandAction.VARIANT_CONTINUE
            )

        elif msg_lower in ['non', 'no', 'n', 'nope', 'nan', '0', 'stop', 'fini', 'terminer']:
            original_code = session.get_data("original_code")
            session_manager.delete(session.merchant_phone)

            return self._response(
                "✅ *Toutes les variantes ont été ajoutées!*\n\n"
                f"👉 Ajoute *{original_code}* dans ton Status WhatsApp.\n"
                "Les clients pourront demander les autres couleurs!\n\n"
                f"💡 Pour ajouter des variantes plus tard:\n"
                f"Écris *variante {original_code}*",
                CommandAction.VARIANTS_COMPLETE
            )

        else:
            return self._response(
                "Réponds *oui* pour ajouter une autre variante\n"
                "Ou *non* pour terminer",
                CommandAction.ASK_AGAIN
            )
