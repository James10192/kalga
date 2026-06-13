"""
Repository pour la gestion des commandes vitrine web.

Phase E2 : délègue à Convex (`internal/storefront:*`). Signatures inchangées.
"""
from typing import Optional, List, Dict, Any

from app.infrastructure.convex_client import get_convex
from app.infrastructure.convex_repo_adapters import adapt_storefront_order


class StorefrontOrderRepository:
    """Gère les commandes passées via la vitrine web (backend Convex)."""

    async def create(
        self,
        merchant_id: int,
        product_id: int,
        client_name: str,
        client_phone: str,
        message: str = None
    ) -> Dict[str, Any]:
        """Crée une nouvelle commande vitrine."""
        args: Dict[str, Any] = {
            "merchantId": merchant_id,
            "productId": product_id,
            "clientName": client_name,
            "clientPhone": client_phone,
        }
        if message is not None:
            args["message"] = message
        doc = await get_convex().mutation("internal/storefront:createOrder", args)
        return adapt_storefront_order(doc)

    async def get_by_merchant(
        self,
        merchant_id: int,
        status: str = None
    ) -> List[Dict[str, Any]]:
        """Récupère les commandes d'un marchand (enrichies infos produit)."""
        args: Dict[str, Any] = {"merchantId": merchant_id}
        if status:
            args["status"] = status
        docs = await get_convex().query("internal/storefront:listByMerchant", args)
        return [adapt_storefront_order(d) for d in (docs or [])]

    async def update_status(self, order_id: int, status: str) -> bool:
        """Met à jour le statut d'une commande."""
        result = await get_convex().mutation("internal/storefront:updateStatus", {
            "orderId": order_id,
            "status": status,
        })
        return bool(result and result.get("updated"))


# Instance globale
_storefront_order_repo: Optional[StorefrontOrderRepository] = None


def get_storefront_order_repository() -> StorefrontOrderRepository:
    """Retourne l'instance globale du repository"""
    global _storefront_order_repo
    if _storefront_order_repo is None:
        _storefront_order_repo = StorefrontOrderRepository()
    return _storefront_order_repo
