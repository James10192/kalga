"""
Repository de base avec méthodes communes
"""
from abc import ABC
from typing import Optional, List, Dict, Any
from ..connection import get_connection


class BaseRepository(ABC):
    """
    Classe de base pour tous les repositories.
    Fournit les opérations communes de base de données.
    """

    def __init__(self, table_name: str):
        self.table_name = table_name

    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Récupère un enregistrement par son ID"""
        async with get_connection() as db:
            cursor = await db.execute(
                f"SELECT * FROM {self.table_name} WHERE id = ?",
                (id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def delete(self, id: int) -> bool:
        """Supprime un enregistrement par son ID"""
        async with get_connection() as db:
            cursor = await db.execute(
                f"DELETE FROM {self.table_name} WHERE id = ?",
                (id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def count(self, where: str = "1=1", params: tuple = ()) -> int:
        """Compte les enregistrements avec une condition optionnelle"""
        async with get_connection() as db:
            cursor = await db.execute(
                f"SELECT COUNT(*) FROM {self.table_name} WHERE {where}",
                params
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
