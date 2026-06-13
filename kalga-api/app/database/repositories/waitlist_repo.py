"""
Repository pour la gestion de la waitlist et des événements de stock.

Phase E2 : délègue à Convex. Les opérations hot-path passent par
`internal/waitlist:*` (addToWaitlist/getWaitlistCount/isClientInWaitlist/
logStockEvent) ; le reste (dashboard + scheduler) par `internal/stockjournal:*`.
Signatures publiques inchangées.
"""
from typing import Optional, List, Dict, Any

from app.infrastructure.convex_client import get_convex
from app.infrastructure.convex_repo_adapters import ms_to_iso


def _iso_dates(rows: List[Dict[str, Any]], keys) -> List[Dict[str, Any]]:
    """Convertit les epoch ms -> ISO sur les clés données (parité SQLite)."""
    out = []
    for r in (rows or []):
        r = dict(r)
        for k in keys:
            if isinstance(r.get(k), (int, float)):
                r[k] = ms_to_iso(r[k])
        out.append(r)
    return out


class WaitlistRepository:
    """Gère les opérations sur product_waitlist et stock_events (backend Convex)."""

    # === WAITLIST ===

    async def add_to_waitlist(
        self,
        merchant_id: int,
        product_id: int,
        client_phone: str,
        client_name: str = None,
        conversation_id: int = None,
        offered_price: float = None,
        expires_days: int = 7
    ) -> Optional[Dict[str, Any]]:
        """Ajoute un client à la waitlist (idempotent). Renvoie {added, position}."""
        args: Dict[str, Any] = {
            "merchantId": merchant_id,
            "productId": product_id,
            "clientPhone": client_phone,
            "expiresDays": expires_days,
        }
        if client_name is not None:
            args["clientName"] = client_name
        if conversation_id is not None:
            args["conversationId"] = conversation_id
        if offered_price is not None:
            args["offeredPrice"] = offered_price
        return await get_convex().mutation("internal/waitlist:addToWaitlist", args)

    async def get_waitlist_for_product(
        self,
        product_id: int,
        status: str = 'waiting'
    ) -> List[Dict[str, Any]]:
        """Récupère tous les clients en attente pour un produit."""
        rows = await get_convex().query("internal/stockjournal:getWaitlistForProduct", {
            "productId": product_id,
            "status": status,
        })
        return _iso_dates(rows, ("expires_at", "notified_at", "created_at", "updated_at"))

    async def get_waitlist_count(self, product_id: int) -> int:
        """Nombre de clients en attente pour un produit."""
        # getWaitlistCount exige merchantId côté Convex (signature hot-path) ;
        # on le résout via le produit pour préserver la signature historique.
        product = await get_convex().query("internal/catalog:getById", {
            "productId": product_id,
        })
        if not product:
            return 0
        return await get_convex().query("internal/waitlist:getWaitlistCount", {
            "merchantId": product["merchantId"],
            "productId": product_id,
        })

    async def get_merchant_waitlist_summary(
        self,
        merchant_id: int
    ) -> List[Dict[str, Any]]:
        """Résumé waitlist par produit pour un marchand."""
        rows = await get_convex().query("internal/stockjournal:getMerchantWaitlistSummary", {
            "merchantId": merchant_id,
        })
        return _iso_dates(rows, ("oldest_wait_date",))

    async def mark_notified(
        self,
        waitlist_ids: List[int]
    ) -> int:
        """Marque des entrées waitlist comme notifiées."""
        if not waitlist_ids:
            return 0
        result = await get_convex().mutation("internal/stockjournal:markNotified", {
            "waitlistIds": waitlist_ids,
        })
        return result.get("updated", 0) if result else 0

    async def clear_waitlist(self, product_id: int) -> int:
        """Vide la waitlist d'un produit après broadcast."""
        result = await get_convex().mutation("internal/stockjournal:clearWaitlist", {
            "productId": product_id,
        })
        return result.get("cleared", 0) if result else 0

    async def is_client_in_waitlist(
        self,
        product_id: int,
        client_phone: str
    ) -> bool:
        """Vérifie si un client est déjà en waitlist pour un produit."""
        product = await get_convex().query("internal/catalog:getById", {
            "productId": product_id,
        })
        if not product:
            return False
        return await get_convex().query("internal/waitlist:isClientInWaitlist", {
            "merchantId": product["merchantId"],
            "productId": product_id,
            "clientPhone": client_phone,
        })

    # === STOCK EVENTS ===

    async def log_stock_event(
        self,
        merchant_id: int,
        product_id: int,
        event_type: str,
        quantity_delta: int,
        quantity_after: int,
        conversation_id: int = None,
        notes: str = None
    ) -> None:
        """Enregistre un événement de stock (journal append-only)."""
        args: Dict[str, Any] = {
            "merchantId": merchant_id,
            "productId": product_id,
            "eventType": event_type,
            "quantityDelta": quantity_delta,
            "quantityAfter": quantity_after,
        }
        if conversation_id is not None:
            args["conversationId"] = conversation_id
        if notes is not None:
            args["notes"] = notes
        await get_convex().mutation("internal/waitlist:logStockEvent", args)

    async def get_stock_history(
        self,
        product_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Historique des événements de stock d'un produit sur N jours."""
        from datetime import datetime, timedelta
        since_ms = (datetime.now() - timedelta(days=days)).timestamp() * 1000.0
        rows = await get_convex().query("internal/stockjournal:getStockHistory", {
            "productId": product_id,
            "sinceMs": since_ms,
        })
        return _iso_dates(rows, ("created_at",))

    async def get_lost_revenue_estimate(
        self,
        merchant_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """Calcule les revenus potentiels perdus sur les N derniers jours."""
        from datetime import datetime, timedelta
        since_ms = (datetime.now() - timedelta(days=days)).timestamp() * 1000.0
        return await get_convex().query("internal/stockjournal:getLostRevenueEstimate", {
            "merchantId": merchant_id,
            "sinceMs": since_ms,
            "days": days,
        })

    async def get_products_out_of_stock_since(
        self,
        merchant_id: int,
        days: int
    ) -> List[Dict[str, Any]]:
        """Produits épuisés depuis au moins N jours (dialogue proactif marchand)."""
        from datetime import datetime, timedelta
        now = datetime.now()
        since_ms = (now - timedelta(days=days)).timestamp() * 1000.0
        cooldown_ms = (now - timedelta(days=1)).timestamp() * 1000.0
        rows = await get_convex().query("internal/stockjournal:getProductsOutOfStockSince", {
            "merchantId": merchant_id,
            "sinceMs": since_ms,
            "alertCooldownMs": cooldown_ms,
        })
        return _iso_dates(rows, ("out_since", "last_stock_alert_at"))


# Instance globale
_waitlist_repo: Optional[WaitlistRepository] = None


def get_waitlist_repository() -> WaitlistRepository:
    global _waitlist_repo
    if _waitlist_repo is None:
        _waitlist_repo = WaitlistRepository()
    return _waitlist_repo
