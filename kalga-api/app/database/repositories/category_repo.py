"""
Repository pour la gestion des catégories de produits
"""
from typing import Optional, List, Dict, Any
from .base import BaseRepository
from ..connection import get_connection


class CategoryRepository(BaseRepository):
    """Gère les opérations CRUD pour les catégories"""

    def __init__(self):
        super().__init__("categories")

    async def create(
        self,
        merchant_id: int,
        name: str,
        icon: str = "📦",
        color: str = "#667eea"
    ) -> Dict[str, Any]:
        """Crée une nouvelle catégorie"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO categories (merchant_id, name, icon, color)
                VALUES (?, ?, ?, ?)
                """,
                (merchant_id, name, icon, color)
            )
            await db.commit()

            cursor = await db.execute(
                "SELECT * FROM categories WHERE id = ?",
                (cursor.lastrowid,)
            )
            row = await cursor.fetchone()
            return dict(row)

    async def get_by_merchant(self, merchant_id: int) -> List[Dict[str, Any]]:
        """Récupère toutes les catégories d'un marchand"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT c.*, COUNT(p.id) as product_count
                FROM categories c
                LEFT JOIN products p ON p.category_id = c.id AND p.is_available = 1
                WHERE c.merchant_id = ?
                GROUP BY c.id
                ORDER BY c.name
                """,
                (merchant_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_by_name(self, merchant_id: int, name: str) -> Optional[Dict[str, Any]]:
        """Récupère une catégorie par son nom"""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM categories WHERE merchant_id = ? AND name = ?",
                (merchant_id, name)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update(self, category_id: int, **kwargs) -> bool:
        """Met à jour une catégorie"""
        if not kwargs:
            return False

        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values())
        values.append(category_id)

        async with get_connection() as db:
            cursor = await db.execute(
                f"UPDATE categories SET {fields} WHERE id = ?",
                tuple(values)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete(self, category_id: int) -> bool:
        """Supprime une catégorie (met les produits sans catégorie)"""
        async with get_connection() as db:
            # D'abord, retirer la catégorie des produits
            await db.execute(
                "UPDATE products SET category_id = NULL WHERE category_id = ?",
                (category_id,)
            )

            # Supprimer la catégorie
            cursor = await db.execute(
                "DELETE FROM categories WHERE id = ?",
                (category_id,)
            )
            await db.commit()
            return cursor.rowcount > 0
