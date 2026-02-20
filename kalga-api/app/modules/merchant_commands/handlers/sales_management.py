"""
Handler pour la gestion des ventes
Gère: confirmation de vente (!ok), annulation (!annuler)
"""
from typing import Any
import logging

from .base import BaseHandler
from ..schemas import CommandResponse, CommandAction

logger = logging.getLogger("kalga.handlers.sales")


class SalesManagementHandler(BaseHandler):
    """Gère les commandes de gestion des ventes"""

    async def handle(self, *args, **kwargs) -> CommandResponse:
        """Non utilisé - ce handler a des méthodes spécifiques"""
        raise NotImplementedError("Utilisez les méthodes spécifiques")

    async def handle_complete_sale(self, merchant: dict, db: Any) -> CommandResponse:
        """
        Marque une vente comme terminée.
        Commandes: !ok, !livré, !fait, !done, !termine
        """
        pending = await db.get_pending_conversations(merchant['id'])

        if not pending:
            return self._response(
                "Tu n'as pas de vente en attente actuellement.",
                CommandAction.NO_PENDING
            )

        # Prendre la plus récente
        conv = pending[0]
        await db.update_conversation(conv['id'], status="completed")

        logger.info(
            f"Vente complétée: conv={conv['id']}, "
            f"merchant={merchant['phone']}, "
            f"price={conv.get('current_offer')}"
        )

        return self._response(
            f"✅ Vente terminée!\n\n"
            f"{conv.get('product_name', 'Produit')} vendu à {conv.get('current_offer', 0):,.0f} F\n"
            f"Client: {conv['client_phone']}",
            CommandAction.SALE_COMPLETED
        )

    async def handle_cancel_sale(self, merchant: dict, db: Any) -> CommandResponse:
        """
        Annule une vente en attente.
        Commandes: !annuler, !cancel, !annule
        """
        pending = await db.get_pending_conversations(merchant['id'])

        if not pending:
            return self._response(
                "Tu n'as pas de vente en attente à annuler.",
                CommandAction.NO_PENDING
            )

        conv = pending[0]
        await db.update_conversation(conv['id'], status="abandoned")

        logger.info(
            f"Vente annulée: conv={conv['id']}, "
            f"merchant={merchant['phone']}"
        )

        return self._response(
            f"❌ Vente annulée.\n\n"
            f"{conv.get('product_name', 'Produit')} - Client: {conv['client_phone']}\n\n"
            "Le produit est de nouveau disponible.",
            CommandAction.SALE_CANCELLED
        )
