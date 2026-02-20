"""
Repository pour la gestion des commandes vitrine web
"""
from typing import Optional, List, Dict, Any
from .base import BaseRepository
from ..connection import get_connection


class StorefrontOrderRepository(BaseRepository):
    """Gère les commandes passées via la vitrine web"""

    def __init__(self):
        super().__init__("storefront_orders")

    async def create(
        self,
        merchant_id: int,
        product_id: int,
        client_name: str,
        client_phone: str,
        message: str = None
    ) -> Dict[str, Any]:
        """Crée une nouvelle commande vitrine"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO storefront_orders (merchant_id, product_id, client_name, client_phone, message)
                VALUES (?, ?, ?, ?, ?)
                """,
                (merchant_id, product_id, client_name, client_phone, message)
            )
            await db.commit()
            order_id = cursor.lastrowid

            cursor = await db.execute(
                "SELECT * FROM storefront_orders WHERE id = ?",
                (order_id,)
            )
            row = await cursor.fetchone()
            return dict(row)

    async def get_by_merchant(
        self,
        merchant_id: int,
        status: str = None
    ) -> List[Dict[str, Any]]:
        """Récupère les commandes d'un marchand"""
        async with get_connection() as db:
            query = """
                SELECT so.*, p.name as product_name, p.code as product_code, p.price
                FROM storefront_orders so
                JOIN products p ON so.product_id = p.id
                WHERE so.merchant_id = ?
            """
            params = [merchant_id]

            if status:
                query += " AND so.status = ?"
                params.append(status)

            query += " ORDER BY so.created_at DESC"

            cursor = await db.execute(query, tuple(params))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_status(self, order_id: int, status: str) -> bool:
        """Met à jour le statut d'une commande"""
        async with get_connection() as db:
            cursor = await db.execute(
                "UPDATE storefront_orders SET status = ? WHERE id = ?",
                (status, order_id)
            )
            await db.commit()
            return cursor.rowcount > 0


# Instance globale
_storefront_order_repo: Optional[StorefrontOrderRepository] = None


def get_storefront_order_repository() -> StorefrontOrderRepository:
    """Retourne l'instance globale du repository"""
    global _storefront_order_repo
    if _storefront_order_repo is None:
        _storefront_order_repo = StorefrontOrderRepository()
    return _storefront_order_repo
