"""
Repository pour la gestion de la waitlist et des événements de stock
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from ..connection import get_connection


class WaitlistRepository:
    """Gère les opérations sur product_waitlist et stock_events"""

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
        """
        Ajoute un client à la waitlist d'un produit.
        Ignore si déjà en attente pour ce produit.
        Retourne l'entrée créée ou existante.
        """
        expires_at = datetime.now() + timedelta(days=expires_days)

        async with get_connection() as db:
            # Vérifier si déjà en waitlist
            cursor = await db.execute(
                """SELECT * FROM product_waitlist
                   WHERE product_id = ? AND client_phone = ? AND status = 'waiting'""",
                (product_id, client_phone)
            )
            existing = await cursor.fetchone()
            if existing:
                return dict(existing)

            cursor = await db.execute(
                """INSERT INTO product_waitlist
                   (merchant_id, product_id, client_phone, client_name, status,
                    conversation_id, offered_price, expires_at)
                   VALUES (?, ?, ?, ?, 'waiting', ?, ?, ?)""",
                (merchant_id, product_id, client_phone, client_name,
                 conversation_id, offered_price, expires_at.isoformat())
            )
            await db.commit()
            entry_id = cursor.lastrowid

            cursor = await db.execute(
                "SELECT * FROM product_waitlist WHERE id = ?", (entry_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_waitlist_for_product(
        self,
        product_id: int,
        status: str = 'waiting'
    ) -> List[Dict[str, Any]]:
        """Récupère tous les clients en attente pour un produit"""
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT * FROM product_waitlist
                   WHERE product_id = ? AND status = ?
                   ORDER BY created_at ASC""",
                (product_id, status)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_waitlist_count(self, product_id: int) -> int:
        """Nombre de clients en attente pour un produit"""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM product_waitlist WHERE product_id = ? AND status = 'waiting'",
                (product_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_merchant_waitlist_summary(
        self,
        merchant_id: int
    ) -> List[Dict[str, Any]]:
        """
        Résumé waitlist par produit pour un marchand.
        Retourne: product_id, product_name, product_code, waiting_count, oldest_wait_date
        """
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT
                       p.id as product_id,
                       p.name as product_name,
                       p.code as product_code,
                       p.price as product_price,
                       COUNT(w.id) as waiting_count,
                       MIN(w.created_at) as oldest_wait_date
                   FROM product_waitlist w
                   JOIN products p ON w.product_id = p.id
                   WHERE w.merchant_id = ? AND w.status = 'waiting'
                   GROUP BY p.id
                   ORDER BY waiting_count DESC""",
                (merchant_id,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def mark_notified(
        self,
        waitlist_ids: List[int]
    ) -> int:
        """Marque des entrées waitlist comme notifiées"""
        if not waitlist_ids:
            return 0
        placeholders = ','.join('?' * len(waitlist_ids))
        async with get_connection() as db:
            cursor = await db.execute(
                f"""UPDATE product_waitlist
                    SET status = 'notified', notified_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})""",
                tuple(waitlist_ids)
            )
            await db.commit()
            return cursor.rowcount

    async def clear_waitlist(self, product_id: int) -> int:
        """Vide la waitlist d'un produit après broadcast"""
        async with get_connection() as db:
            cursor = await db.execute(
                """UPDATE product_waitlist
                   SET status = 'notified', notified_at = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE product_id = ? AND status = 'waiting'""",
                (product_id,)
            )
            await db.commit()
            return cursor.rowcount

    async def is_client_in_waitlist(
        self,
        product_id: int,
        client_phone: str
    ) -> bool:
        """Vérifie si un client est déjà en waitlist pour un produit"""
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT 1 FROM product_waitlist
                   WHERE product_id = ? AND client_phone = ? AND status = 'waiting'""",
                (product_id, client_phone)
            )
            return await cursor.fetchone() is not None

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
        """
        Enregistre un événement de stock (journal append-only).
        event_type: 'sale' | 'restock' | 'manual_adjust' | 'out_of_stock' | 'low_stock_alert'
        """
        async with get_connection() as db:
            await db.execute(
                """INSERT INTO stock_events
                   (merchant_id, product_id, event_type, quantity_delta, quantity_after,
                    conversation_id, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (merchant_id, product_id, event_type, quantity_delta, quantity_after,
                 conversation_id, notes)
            )
            await db.commit()

    async def get_stock_history(
        self,
        product_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Historique des événements de stock d'un produit sur N jours"""
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT * FROM stock_events
                   WHERE product_id = ?
                     AND created_at >= datetime('now', ?)
                   ORDER BY created_at ASC""",
                (product_id, f'-{days} days')
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_lost_revenue_estimate(
        self,
        merchant_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Calcule les revenus potentiels perdus sur les N derniers jours.
        Méthode: conversations actives sur produits épuisés × prix × 0.5
        """
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT
                       COUNT(DISTINCT c.id) as lost_inquiries,
                       AVG(p.price) as avg_price,
                       SUM(p.price) * 0.5 as estimated_lost
                   FROM conversations c
                   JOIN products p ON c.product_id = p.id
                   WHERE c.merchant_id = ?
                     AND p.stock_quantity = 0
                     AND c.created_at >= datetime('now', ?)
                     AND c.status IN ('active', 'ended', 'abandoned')""",
                (merchant_id, f'-{days} days')
            )
            row = await cursor.fetchone()
            result = dict(row) if row else {}
            return {
                "lost_inquiries": result.get("lost_inquiries") or 0,
                "avg_price": result.get("avg_price") or 0,
                "estimated_lost": result.get("estimated_lost") or 0,
                "days": days
            }

    async def get_products_out_of_stock_since(
        self,
        merchant_id: int,
        days: int
    ) -> List[Dict[str, Any]]:
        """
        Produits épuisés depuis au moins N jours (pour le dialogue proactif marchand).
        Utilise stock_events pour trouver la date du dernier passage à 0.
        """
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT
                       p.id, p.name, p.code, p.price, p.last_stock_alert_at,
                       MIN(se.created_at) as out_since,
                       COALESCE(
                           (SELECT COUNT(*) FROM product_waitlist w
                            WHERE w.product_id = p.id AND w.status = 'waiting'),
                           0
                       ) as waitlist_count
                   FROM products p
                   JOIN stock_events se ON se.product_id = p.id
                   WHERE p.merchant_id = ?
                     AND p.is_available = 1
                     AND p.stock_quantity = 0
                     AND se.event_type = 'out_of_stock'
                     AND se.created_at <= datetime('now', ?)
                   GROUP BY p.id
                   HAVING (p.last_stock_alert_at IS NULL
                           OR p.last_stock_alert_at <= datetime('now', '-1 day'))""",
                (merchant_id, f'-{days} days')
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# Instance globale
_waitlist_repo: Optional[WaitlistRepository] = None


def get_waitlist_repository() -> WaitlistRepository:
    global _waitlist_repo
    if _waitlist_repo is None:
        _waitlist_repo = WaitlistRepository()
    return _waitlist_repo
