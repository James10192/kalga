"""
Repository pour la gestion des conversations et messages.

Phase E2 : délègue à Convex (`internal/conversation:*`). Signatures inchangées.
Le hot-path chat principal passe par `internal/chat:getContext`/`commitTurn` ;
ce repo couvre les reads dashboard + la maintenance (cleanup) + les écritures
résiduelles encore appelées via la façade `db` (update/add_message).
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from app.infrastructure.convex_client import get_convex


class ConversationRepository:
    """Gère les opérations CRUD pour les conversations et messages (backend Convex)."""

    async def get_active(
        self,
        merchant_id: int,
        client_phone: str,
        product_id: int = None
    ) -> Optional[Dict[str, Any]]:
        """Récupère une conversation vivante entre un marchand et un client."""
        args: Dict[str, Any] = {
            "merchantId": merchant_id,
            "clientPhone": client_phone,
        }
        if product_id:
            args["productId"] = product_id
        return await get_convex().query("internal/conversation:getActive", args)

    async def get_recent_closed(
        self,
        merchant_id: int,
        client_phone: str,
        within_hours: int = 48
    ) -> Optional[Dict[str, Any]]:
        """Dernière conversation récemment clôturée (hot-path : voir internal/chat)."""
        return await get_convex().query("internal/chat:getRecentClosed", {
            "merchantId": merchant_id,
            "clientPhone": client_phone,
            "withinHours": within_hours,
        })

    async def create(
        self,
        merchant_id: int,
        product_id: int,
        client_phone: str
    ) -> Dict[str, Any]:
        """Crée une nouvelle conversation."""
        return await get_convex().mutation("internal/conversation:create", {
            "merchantId": merchant_id,
            "productId": product_id,
            "clientPhone": client_phone,
        })

    async def update(self, conversation_id: int, **kwargs) -> bool:
        """Met à jour une conversation avec les champs fournis."""
        if not kwargs:
            return False
        args: Dict[str, Any] = {"conversationId": conversation_id}
        if "status" in kwargs and kwargs["status"] is not None:
            args["status"] = kwargs["status"]
        if "current_offer" in kwargs:
            args["currentOffer"] = kwargs["current_offer"]
        if "selected_variant_id" in kwargs and kwargs["selected_variant_id"] is not None:
            args["selectedVariantId"] = kwargs["selected_variant_id"]
        result = await get_convex().mutation("internal/conversation:update", args)
        return bool(result and result.get("updated"))

    async def get_by_merchant(
        self,
        merchant_id: int,
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """Récupère les conversations d'un marchand par statut."""
        rows = await get_convex().query("internal/conversation:getByMerchant", {
            "merchantId": merchant_id,
            "status": status,
        })
        return rows or []

    async def get_pending(self, merchant_id: int) -> List[Dict[str, Any]]:
        """Récupère les conversations en attente (pending_delivery ou pending_pickup)."""
        rows = await get_convex().query("internal/conversation:getPending", {
            "merchantId": merchant_id,
        })
        return rows or []

    # === Gestion des messages ===

    async def add_message(
        self,
        conversation_id: int,
        content: str,
        is_from_client: bool
    ) -> Dict[str, Any]:
        """Ajoute un message à une conversation."""
        return await get_convex().mutation("internal/conversation:addMessage", {
            "conversationId": conversation_id,
            "content": content,
            "isFromClient": bool(is_from_client),
        })

    async def get_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
        """Récupère tous les messages d'une conversation."""
        rows = await get_convex().query("internal/conversation:getMessages", {
            "conversationId": conversation_id,
        })
        return rows or []

    # === Nettoyage ===

    async def cleanup_expired(self, days: int = 7) -> int:
        """Marque les conversations inactives depuis X jours comme expirées."""
        cutoff_ms = (datetime.now() - timedelta(days=days)).timestamp() * 1000.0
        result = await get_convex().mutation("internal/conversation:cleanupExpired", {
            "cutoffMs": cutoff_ms,
        })
        return result.get("cleaned", 0) if result else 0


# Instance globale
_conversation_repo: Optional['ConversationRepository'] = None


def get_conversation_repository() -> 'ConversationRepository':
    """Retourne l'instance globale du repository"""
    global _conversation_repo
    if _conversation_repo is None:
        _conversation_repo = ConversationRepository()
    return _conversation_repo
