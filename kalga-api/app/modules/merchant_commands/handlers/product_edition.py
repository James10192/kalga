"""
Handler pour la modification de produits existants
Gère le flux: choix du champ → saisie nouvelle valeur → confirmation
"""
from typing import Optional, Any
import logging

from .base import BaseHandler, PriceExtractor
from ..session_manager import ProductSession, session_manager
from ..schemas import CommandResponse, CommandAction, CreationStep

logger = logging.getLogger("kalga.handlers.edition")

# Mapping des choix utilisateur vers les champs DB
EDITABLE_FIELDS = {
    "nom": "name",
    "prix minimum": "min_price",
    "prix min": "min_price",
    "prix": "price",
    "description": "description",
    "image": "image",
}

NUMBER_MAP = {
    "1": "name",
    "2": "price",
    "3": "min_price",
    "4": "description",
    "5": "image",
}

FIELD_DISPLAY_NAMES = {
    "name": "Nom",
    "price": "Prix de vente",
    "min_price": "Prix minimum",
    "description": "Description",
    "image": "Image",
}


class ProductEditionHandler(BaseHandler):
    """Gère le flux de modification d'un produit existant"""

    STEPS = {
        CreationStep.EDIT_CHOOSE: "_handle_choose_field",
        CreationStep.EDIT_VALUE: "_handle_new_value",
        CreationStep.EDIT_CONFIRM: "_handle_confirm_another",
    }

    async def handle(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        step = session.step
        handler_name = self.STEPS.get(step)

        if not handler_name:
            logger.warning(f"Étape non gérée par ProductEditionHandler: {step}")
            return self._error("Erreur interne: étape non reconnue.")

        handler = getattr(self, handler_name)
        return await handler(session, message, image_path, db)

    async def _handle_choose_field(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Le marchand choisit quel champ modifier"""
        msg_lower = message.lower().strip()

        # Chercher par numéro d'abord
        matched_field = NUMBER_MAP.get(msg_lower)

        # Sinon chercher par mot-clé (prix minimum avant prix pour éviter conflit)
        if not matched_field:
            for keyword, field_name in EDITABLE_FIELDS.items():
                if keyword in msg_lower:
                    matched_field = field_name
                    break

        if not matched_field:
            return self._response(
                "Je n'ai pas compris. Choisis ce que tu veux modifier:\n\n"
                "1️⃣ *nom*\n2️⃣ *prix*\n3️⃣ *prix minimum*\n4️⃣ *description*\n5️⃣ *image*",
                CommandAction.PRODUCT_EDIT_STEP
            )

        session.set_data("edit_field", matched_field)
        session.update_step(CreationStep.EDIT_VALUE)

        prompts = {
            "name": "Quel est le *nouveau nom* du produit?",
            "price": "Quel est le *nouveau prix de vente*? (en FCFA)\n\nExemple: 15000 ou 15k",
            "min_price": "Quel est le *nouveau prix minimum*? (en FCFA)\n\nExemple: 12000 ou 12k",
            "description": "Quelle est la *nouvelle description*?\n\n(ou écris *passer* pour supprimer la description)",
            "image": "Envoie la *nouvelle photo* du produit 📷",
        }

        return self._response(
            f"✏️ Modification: *{FIELD_DISPLAY_NAMES[matched_field]}*\n\n"
            f"{prompts[matched_field]}",
            CommandAction.PRODUCT_EDIT_STEP
        )

    async def _handle_new_value(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Le marchand entre la nouvelle valeur"""
        edit_field = session.get_data("edit_field")
        product_code = session.get_data("product_code")
        product_id = session.get_data("product_id")

        update_kwargs = {}

        if edit_field == "name":
            name = message.strip()
            if not name or len(name) < 2:
                return self._error("Le nom doit contenir au moins 2 caractères.")
            update_kwargs["name"] = name
            display_value = name

        elif edit_field == "price":
            price = PriceExtractor.extract(message)
            if not price or price < 100:
                return self._error("Prix invalide. Entre un montant valide.\n\nExemple: 15000 ou 15k")
            current_min_price = session.get_data("current_min_price")
            if current_min_price and price < current_min_price:
                return self._error(
                    f"Le prix de vente doit être supérieur ou égal au prix minimum ({current_min_price:,.0f} F)."
                )
            update_kwargs["price"] = price
            display_value = f"{price:,.0f} F"

        elif edit_field == "min_price":
            min_price = PriceExtractor.extract(message)
            if not min_price or min_price < 100:
                return self._error("Prix invalide. Entre un montant valide.\n\nExemple: 12000 ou 12k")
            current_price = session.get_data("current_price")
            if current_price and min_price > current_price:
                return self._error(
                    f"Le prix minimum doit être inférieur au prix de vente ({current_price:,.0f} F)."
                )
            update_kwargs["min_price"] = min_price
            display_value = f"{min_price:,.0f} F"

        elif edit_field == "description":
            if message.lower().strip() in ['passer', 'skip', 'supprimer', '-']:
                update_kwargs["description"] = None
                display_value = "(supprimée)"
            else:
                update_kwargs["description"] = message.strip()
                desc_preview = message.strip()[:50]
                display_value = desc_preview + ("..." if len(message.strip()) > 50 else "")

        elif edit_field == "image":
            if not image_path:
                return self._error("Envoie une *photo* pour modifier l'image 📷")
            update_kwargs["image_path"] = image_path
            display_value = "Nouvelle image ✅"

        else:
            return self._error("Erreur interne: champ non reconnu.")

        # Sauvegarder en base
        try:
            success = await db.update_product(product_id, **update_kwargs)
            if not success:
                return self._error("Erreur: le produit n'a pas pu être mis à jour.")
        except Exception as e:
            logger.error(f"Erreur modification produit {product_code}: {e}")
            session_manager.delete(session.merchant_phone)
            return self._error(f"Erreur lors de la modification: {str(e)}")

        # Mettre à jour les valeurs courantes dans la session
        if edit_field == "price":
            session.set_data("current_price", update_kwargs["price"])
        elif edit_field == "min_price":
            session.set_data("current_min_price", update_kwargs["min_price"])

        session.update_step(CreationStep.EDIT_CONFIRM)

        return self._response(
            f"✅ *{FIELD_DISPLAY_NAMES[edit_field]}* mis à jour: *{display_value}*\n\n"
            f"Tu veux *modifier autre chose* sur {product_code}?\n\n"
            "Réponds *oui* pour continuer ou *non* pour terminer",
            CommandAction.PRODUCT_EDITED,
            product_code=product_code
        )

    async def _handle_confirm_another(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Demande si le marchand veut modifier autre chose"""
        msg_lower = message.lower().strip()
        product_code = session.get_data("product_code")

        if msg_lower in ['oui', 'yes', 'o', 'y', 'ok', 'ouais', '1']:
            session.update_step(CreationStep.EDIT_CHOOSE)
            return self._response(
                f"✏️ *Modification de {product_code}*\n\n"
                "Que veux-tu modifier?\n\n"
                "1️⃣ *nom*\n2️⃣ *prix*\n3️⃣ *prix minimum*\n4️⃣ *description*\n5️⃣ *image*",
                CommandAction.PRODUCT_EDIT_STEP
            )

        elif msg_lower in ['non', 'no', 'n', 'nope', 'nan', '0', 'stop', 'fini', 'terminer']:
            session_manager.delete(session.merchant_phone)
            return self._response(
                f"✅ *Modifications terminées pour {product_code}!*",
                CommandAction.PRODUCT_EDITED,
                product_code=product_code
            )

        else:
            return self._response(
                "Réponds *oui* pour modifier autre chose ou *non* pour terminer.",
                CommandAction.PRODUCT_EDIT_STEP
            )
