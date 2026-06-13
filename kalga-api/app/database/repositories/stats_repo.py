"""
Repository pour les statistiques et analytics.

Phase E2 : délègue à Convex (`internal/stats:*`). Signatures inchangées.
Les agrégats SQL (SUM/AVG/GROUP BY) sont recalculés côté Convex (JS) ou,
pour `get_summary_stats`, agrégés ici à partir de la plage quotidienne.
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta, timezone
import json

from app.infrastructure.convex_client import get_convex


def _start_ms(days: int) -> float:
    """Borne basse epoch ms = (today - days) à minuit local."""
    start = date.today() - timedelta(days=days)
    return datetime(start.year, start.month, start.day).timestamp() * 1000.0


class StatsRepository:
    """Gère les opérations pour les statistiques et analytics (backend Convex)."""

    # === STATISTIQUES QUOTIDIENNES ===

    async def get_or_create_daily_stats(self, merchant_id: int, stat_date: date = None) -> Dict[str, Any]:
        """Récupère ou crée les stats du jour pour un marchand."""
        if stat_date is None:
            stat_date = date.today()
        return await get_convex().mutation("internal/stats:getOrCreateDailyStats", {
            "merchantId": merchant_id,
            "date": stat_date.isoformat(),
        })

    async def increment_conversations(self, merchant_id: int) -> None:
        """Incrémente le compteur de conversations du jour."""
        await get_convex().mutation("internal/stats:bumpDailyStats", {
            "merchantId": merchant_id,
            "date": date.today().isoformat(),
            "conversationsDelta": 1,
        })

    async def increment_messages(self, merchant_id: int, count: int = 1) -> None:
        """Incrémente le compteur de messages du jour."""
        await get_convex().mutation("internal/stats:bumpDailyStats", {
            "merchantId": merchant_id,
            "date": date.today().isoformat(),
            "messagesDelta": count,
        })

    async def record_sale(self, merchant_id: int, amount: float) -> None:
        """Enregistre une vente."""
        await get_convex().mutation("internal/stats:bumpDailyStats", {
            "merchantId": merchant_id,
            "date": date.today().isoformat(),
            "salesDelta": 1,
            "revenueDelta": amount,
        })

    async def update_unique_clients(self, merchant_id: int, count: int) -> None:
        """Met à jour le nombre de clients uniques du jour."""
        await get_convex().mutation("internal/stats:bumpDailyStats", {
            "merchantId": merchant_id,
            "date": date.today().isoformat(),
            "uniqueClients": count,
        })

    # === RÉCUPÉRATION DES STATS ===

    async def get_stats_range(
        self,
        merchant_id: int,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Récupère les stats pour une période."""
        rows = await get_convex().query("internal/stats:getStatsRange", {
            "merchantId": merchant_id,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        })
        return rows or []

    async def get_summary_stats(
        self,
        merchant_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Récumé des stats sur une période (agrégé depuis la plage quotidienne)."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        rows = await self.get_stats_range(merchant_id, start_date, end_date)

        total_conv = sum(r.get("conversations_count", 0) for r in rows)
        total_msg = sum(r.get("messages_count", 0) for r in rows)
        total_sales = sum(r.get("sales_count", 0) for r in rows)
        total_rev = sum(r.get("revenue", 0) for r in rows)
        n = len(rows)

        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_conversations": total_conv,
            "total_messages": total_msg,
            "total_sales": total_sales,
            "total_revenue": total_rev,
            "avg_daily_conversations": round(total_conv / n, 1) if n else 0,
            "avg_daily_sales": round(total_sales / n, 1) if n else 0,
        }

    async def get_top_products(
        self,
        merchant_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Récupère les produits les plus vendus."""
        rows = await get_convex().query("internal/stats:getTopProducts", {
            "merchantId": merchant_id,
            "limit": limit,
        })
        return rows or []

    async def get_conversion_rate(self, merchant_id: int, days: int = 30) -> Dict[str, Any]:
        """Calcule le taux de conversion."""
        return await get_convex().query("internal/stats:getConversionRate", {
            "merchantId": merchant_id,
            "startMs": _start_ms(days),
        })

    async def get_hourly_activity(self, merchant_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Récupère l'activité par heure de la journée."""
        # SQLite stockait l'heure locale ; on passe le décalage local (minutes).
        offset = datetime.now().astimezone().utcoffset() or timedelta()
        tz_offset_minutes = int(offset.total_seconds() // 60)
        rows = await get_convex().query("internal/stats:getHourlyActivity", {
            "merchantId": merchant_id,
            "startMs": _start_ms(days),
            "tzOffsetMinutes": tz_offset_minutes,
        })
        return rows or []

    # === ÉVÉNEMENTS ANALYTICS ===

    async def log_event(
        self,
        merchant_id: int,
        event_type: str,
        product_id: int = None,
        conversation_id: int = None,
        client_phone: str = None,
        data: dict = None
    ) -> int:
        """Enregistre un événement analytics."""
        args: Dict[str, Any] = {
            "merchantId": merchant_id,
            "eventType": event_type,
        }
        if product_id is not None:
            args["productId"] = product_id
        if conversation_id is not None:
            args["conversationId"] = conversation_id
        if client_phone is not None:
            args["clientPhone"] = client_phone
        if data is not None:
            args["data"] = json.dumps(data)
        result = await get_convex().mutation("internal/stats:logEvent", args)
        return result.get("eventId") if result else None

    async def get_recent_events(
        self,
        merchant_id: int,
        event_type: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Récupère les événements récents."""
        args: Dict[str, Any] = {"merchantId": merchant_id, "limit": limit}
        if event_type:
            args["eventType"] = event_type
        docs = await get_convex().query("internal/stats:getRecentEvents", args)
        result = []
        for doc in (docs or []):
            item = {
                "id": doc.get("_id"),
                "merchant_id": doc.get("merchantId"),
                "event_type": doc.get("eventType"),
                "product_id": doc.get("productId"),
                "conversation_id": doc.get("conversationId"),
                "client_phone": doc.get("clientPhone"),
                "data": doc.get("data"),
            }
            if item.get("data"):
                try:
                    item["data"] = json.loads(item["data"])
                except (json.JSONDecodeError, TypeError):
                    pass
            result.append(item)
        return result


# Instance singleton
_stats_repo = None


def get_stats_repository() -> StatsRepository:
    """Retourne l'instance du repository stats"""
    global _stats_repo
    if _stats_repo is None:
        _stats_repo = StatsRepository()
    return _stats_repo
