"""
Repository pour les statistiques et analytics
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
import json
from .base import BaseRepository
from ..connection import get_connection


class StatsRepository(BaseRepository):
    """Gère les opérations pour les statistiques et analytics"""

    def __init__(self):
        super().__init__("daily_stats")

    # === STATISTIQUES QUOTIDIENNES ===

    async def get_or_create_daily_stats(self, merchant_id: int, stat_date: date = None) -> Dict[str, Any]:
        """Récupère ou crée les stats du jour pour un marchand"""
        if stat_date is None:
            stat_date = date.today()

        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM daily_stats WHERE merchant_id = ? AND date = ?",
                (merchant_id, stat_date.isoformat())
            )
            row = await cursor.fetchone()

            if row:
                return dict(row)

            # Créer les stats du jour
            cursor = await db.execute(
                """
                INSERT INTO daily_stats (merchant_id, date)
                VALUES (?, ?)
                """,
                (merchant_id, stat_date.isoformat())
            )
            await db.commit()

            return {
                "id": cursor.lastrowid,
                "merchant_id": merchant_id,
                "date": stat_date.isoformat(),
                "conversations_count": 0,
                "messages_count": 0,
                "sales_count": 0,
                "revenue": 0,
                "unique_clients": 0,
                "avg_response_time": None
            }

    async def increment_conversations(self, merchant_id: int) -> None:
        """Incrémente le compteur de conversations du jour"""
        today = date.today().isoformat()
        async with get_connection() as db:
            await db.execute(
                """
                INSERT INTO daily_stats (merchant_id, date, conversations_count)
                VALUES (?, ?, 1)
                ON CONFLICT(merchant_id, date)
                DO UPDATE SET conversations_count = conversations_count + 1
                """,
                (merchant_id, today)
            )
            await db.commit()

    async def increment_messages(self, merchant_id: int, count: int = 1) -> None:
        """Incrémente le compteur de messages du jour"""
        today = date.today().isoformat()
        async with get_connection() as db:
            await db.execute(
                """
                INSERT INTO daily_stats (merchant_id, date, messages_count)
                VALUES (?, ?, ?)
                ON CONFLICT(merchant_id, date)
                DO UPDATE SET messages_count = messages_count + ?
                """,
                (merchant_id, today, count, count)
            )
            await db.commit()

    async def record_sale(self, merchant_id: int, amount: float) -> None:
        """Enregistre une vente"""
        today = date.today().isoformat()
        async with get_connection() as db:
            await db.execute(
                """
                INSERT INTO daily_stats (merchant_id, date, sales_count, revenue)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(merchant_id, date)
                DO UPDATE SET
                    sales_count = sales_count + 1,
                    revenue = revenue + ?
                """,
                (merchant_id, today, amount, amount)
            )
            await db.commit()

    async def update_unique_clients(self, merchant_id: int, count: int) -> None:
        """Met à jour le nombre de clients uniques du jour"""
        today = date.today().isoformat()
        async with get_connection() as db:
            await db.execute(
                """
                INSERT INTO daily_stats (merchant_id, date, unique_clients)
                VALUES (?, ?, ?)
                ON CONFLICT(merchant_id, date)
                DO UPDATE SET unique_clients = ?
                """,
                (merchant_id, today, count, count)
            )
            await db.commit()

    # === RÉCUPÉRATION DES STATS ===

    async def get_stats_range(
        self,
        merchant_id: int,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Récupère les stats pour une période"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM daily_stats
                WHERE merchant_id = ? AND date BETWEEN ? AND ?
                ORDER BY date ASC
                """,
                (merchant_id, start_date.isoformat(), end_date.isoformat())
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_summary_stats(
        self,
        merchant_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Récupère un résumé des stats sur une période"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT
                    COALESCE(SUM(conversations_count), 0) as total_conversations,
                    COALESCE(SUM(messages_count), 0) as total_messages,
                    COALESCE(SUM(sales_count), 0) as total_sales,
                    COALESCE(SUM(revenue), 0) as total_revenue,
                    COALESCE(AVG(conversations_count), 0) as avg_daily_conversations,
                    COALESCE(AVG(sales_count), 0) as avg_daily_sales
                FROM daily_stats
                WHERE merchant_id = ? AND date BETWEEN ? AND ?
                """,
                (merchant_id, start_date.isoformat(), end_date.isoformat())
            )
            row = await cursor.fetchone()

            return {
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_conversations": row[0] or 0,
                "total_messages": row[1] or 0,
                "total_sales": row[2] or 0,
                "total_revenue": row[3] or 0,
                "avg_daily_conversations": round(row[4] or 0, 1),
                "avg_daily_sales": round(row[5] or 0, 1)
            }

    async def get_top_products(
        self,
        merchant_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Récupère les produits les plus vendus"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.code,
                    COUNT(c.id) as conversation_count,
                    SUM(CASE WHEN c.status = 'completed' THEN 1 ELSE 0 END) as sales_count,
                    SUM(CASE WHEN c.status = 'completed' THEN c.current_offer ELSE 0 END) as revenue
                FROM products p
                LEFT JOIN conversations c ON p.id = c.product_id
                WHERE p.merchant_id = ?
                GROUP BY p.id
                ORDER BY sales_count DESC, conversation_count DESC
                LIMIT ?
                """,
                (merchant_id, limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_conversion_rate(self, merchant_id: int, days: int = 30) -> Dict[str, Any]:
        """Calcule le taux de conversion"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT
                    COUNT(*) as total_conversations,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status IN ('pending_delivery', 'pending_pickup') THEN 1 ELSE 0 END) as pending
                FROM conversations
                WHERE merchant_id = ? AND date(created_at) BETWEEN ? AND ?
                """,
                (merchant_id, start_date.isoformat(), end_date.isoformat())
            )
            row = await cursor.fetchone()

            total = row[0] or 0
            completed = row[1] or 0
            pending = row[2] or 0

            conversion_rate = (completed / total * 100) if total > 0 else 0

            return {
                "total_conversations": total,
                "completed_sales": completed,
                "pending_sales": pending,
                "conversion_rate": round(conversion_rate, 1)
            }

    async def get_hourly_activity(self, merchant_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Récupère l'activité par heure de la journée"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT
                    strftime('%H', created_at) as hour,
                    COUNT(*) as message_count
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.merchant_id = ? AND date(m.created_at) BETWEEN ? AND ?
                GROUP BY hour
                ORDER BY hour
                """,
                (merchant_id, start_date.isoformat(), end_date.isoformat())
            )
            rows = await cursor.fetchall()
            return [{"hour": int(row[0]), "count": row[1]} for row in rows]

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
        """Enregistre un événement analytics"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO analytics_events
                (merchant_id, event_type, product_id, conversation_id, client_phone, data)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    merchant_id,
                    event_type,
                    product_id,
                    conversation_id,
                    client_phone,
                    json.dumps(data) if data else None
                )
            )
            await db.commit()
            return cursor.lastrowid

    async def get_recent_events(
        self,
        merchant_id: int,
        event_type: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Récupère les événements récents"""
        async with get_connection() as db:
            if event_type:
                cursor = await db.execute(
                    """
                    SELECT * FROM analytics_events
                    WHERE merchant_id = ? AND event_type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (merchant_id, event_type, limit)
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM analytics_events
                    WHERE merchant_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (merchant_id, limit)
                )

            rows = await cursor.fetchall()
            result = []
            for row in rows:
                item = dict(row)
                if item.get('data'):
                    try:
                        item['data'] = json.loads(item['data'])
                    except:
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
