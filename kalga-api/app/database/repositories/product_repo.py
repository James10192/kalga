"""
Repository pour la gestion des produits
"""
from typing import Optional, List, Dict, Any
from .base import BaseRepository
from ..connection import get_connection


def _row_to_dict(row) -> Dict[str, Any]:
    """Convertit une row SQLite en dict en excluant le champ embedding (BLOB non-sérialisable)."""
    d = dict(row)
    d.pop("embedding", None)
    return d


class ProductRepository(BaseRepository):
    """Gère les opérations CRUD pour les produits"""

    def __init__(self):
        super().__init__("products")

    async def get_by_id(self, id: int):
        """Override: exclut le champ embedding (BLOB) non-sérialisable en JSON."""
        async with get_connection() as db:
            cursor = await db.execute("SELECT * FROM products WHERE id = ?", (id,))
            row = await cursor.fetchone()
            return _row_to_dict(row) if row else None

    async def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Récupère un produit par son code (#K001, etc.)"""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM products WHERE code = ? AND is_available = 1",
                (code.upper(),)
            )
            row = await cursor.fetchone()
            return _row_to_dict(row) if row else None

    async def create(
        self,
        merchant_id: int,
        name: str,
        price: float,
        min_price: float,
        description: str = None,
        image_path: str = None,
        group_id: str = None,
        variant_name: str = None,
        stock_quantity: int = -1,
        low_stock_threshold: int = 5
    ) -> Dict[str, Any]:
        """
        Crée un nouveau produit avec un code auto-généré.
        stock_quantity: -1 = illimité, >= 0 = quantité gérée
        """
        async with get_connection() as db:
            # Générer le prochain code
            cursor = await db.execute(
                "SELECT MAX(CAST(SUBSTR(code, 3) AS INTEGER)) FROM products"
            )
            row = await cursor.fetchone()
            next_num = (row[0] or 0) + 1
            code = f"#K{next_num:03d}"

            # Insérer le produit
            cursor = await db.execute(
                """
                INSERT INTO products (merchant_id, name, code, price, min_price, description,
                                      image_path, group_id, variant_name, stock_quantity, low_stock_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (merchant_id, name, code, price, min_price, description,
                 image_path, group_id, variant_name, stock_quantity, low_stock_threshold)
            )
            await db.commit()
            product_id = cursor.lastrowid

            # Récupérer le produit créé
            cursor = await db.execute(
                "SELECT * FROM products WHERE id = ?",
                (product_id,)
            )
            row = await cursor.fetchone()
            return _row_to_dict(row) if row else None

    async def update(self, product_id: int, **kwargs) -> bool:
        """Met à jour un produit avec les champs fournis"""
        if not kwargs:
            return False

        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values())
        values.append(product_id)

        async with get_connection() as db:
            cursor = await db.execute(
                f"UPDATE products SET {fields} WHERE id = ?",
                tuple(values)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_by_merchant(
        self,
        merchant_id: int,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Récupère tous les produits d'un marchand"""
        async with get_connection() as db:
            query = (
                "SELECT id, merchant_id, name, code, price, min_price, description, "
                "image_path, group_id, variant_name, stock_quantity, low_stock_threshold, "
                "is_available, created_at FROM products WHERE merchant_id = ?"
            )
            if active_only:
                query += " AND is_available = 1"
            query += " ORDER BY created_at DESC"

            cursor = await db.execute(query, (merchant_id,))
            rows = await cursor.fetchall()
            return [_row_to_dict(row) for row in rows]

    async def get_other_variants(
        self,
        product_id: int,
        group_id: str
    ) -> List[Dict[str, Any]]:
        """Récupère les autres variantes d'un produit (même group_id)"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM products
                WHERE group_id = ? AND id != ? AND is_available = 1
                ORDER BY variant_name
                """,
                (group_id, product_id)
            )
            rows = await cursor.fetchall()
            return [_row_to_dict(row) for row in rows]

    async def get_all_in_group(self, group_id: str) -> List[Dict[str, Any]]:
        """Récupère TOUTES les variantes d'un groupe, y compris le produit courant"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM products
                WHERE group_id = ? AND is_available = 1
                ORDER BY variant_name
                """,
                (group_id,)
            )
            rows = await cursor.fetchall()
            return [_row_to_dict(row) for row in rows]

    async def deactivate(self, product_id: int) -> bool:
        """Désactive un produit (soft delete)"""
        return await self.update(product_id, is_available=0)

    async def get_next_code(self) -> str:
        """Retourne le prochain code produit disponible"""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT MAX(CAST(SUBSTR(code, 3) AS INTEGER)) FROM products"
            )
            row = await cursor.fetchone()
            next_num = (row[0] or 0) + 1
            return f"#K{next_num:03d}"

    # === EMBEDDINGS CLIP (recherche visuelle) ===

    async def get_all_with_embeddings(self, merchant_id: int) -> list:
        """Retourne (product_id, product_code, embedding_blob, name, price, description) pour tous les produits actifs."""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT id, code, embedding, name, price, description FROM products WHERE merchant_id=? AND is_available=1",
                (merchant_id,)
            )
            rows = await cursor.fetchall()
            return [(row[0], row[1], row[2], row[3], row[4], row[5]) for row in rows]

    async def save_embedding(self, product_id: int, embedding_blob: bytes) -> bool:
        """Sauvegarde l'embedding CLIP d'un produit."""
        async with get_connection() as db:
            cursor = await db.execute(
                "UPDATE products SET embedding=? WHERE id=?",
                (embedding_blob, product_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    # === GESTION DU STOCK ===

    async def update_stock(self, product_id: int, quantity: int) -> bool:
        """Met à jour la quantité en stock"""
        return await self.update(product_id, stock_quantity=quantity)

    async def decrement_stock(self, product_id: int, quantity: int = 1) -> Dict[str, Any]:
        """
        Décrémente le stock d'un produit.
        Retourne le produit mis à jour avec son nouveau stock.
        Ne décrémente pas si stock_quantity = -1 (illimité)
        """
        async with get_connection() as db:
            # Récupérer le produit
            cursor = await db.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            product = _row_to_dict(row)
            current_stock = product.get('stock_quantity', -1)

            # Si stock illimité, ne rien faire
            if current_stock == -1:
                return product

            # Calculer le nouveau stock
            new_stock = max(0, current_stock - quantity)

            # Mettre à jour
            await db.execute(
                "UPDATE products SET stock_quantity = ? WHERE id = ?",
                (new_stock, product_id)
            )
            await db.commit()

            product['stock_quantity'] = new_stock
            return product

    async def check_stock_status(self, product_id: int) -> Dict[str, Any]:
        """
        Vérifie le statut du stock d'un produit.
        Retourne: {available: bool, quantity: int, is_low: bool, is_unlimited: bool}
        """
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT stock_quantity, low_stock_threshold FROM products WHERE id = ?",
                (product_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            quantity = row[0] if row[0] is not None else -1
            threshold = row[1] if row[1] is not None else 5

            is_unlimited = quantity == -1

            return {
                "available": is_unlimited or quantity > 0,
                "quantity": quantity,
                "is_low": not is_unlimited and 0 < quantity <= threshold,
                "is_out_of_stock": not is_unlimited and quantity == 0,
                "is_unlimited": is_unlimited,
                "threshold": threshold
            }

    async def get_low_stock_products(self, merchant_id: int) -> List[Dict[str, Any]]:
        """Récupère les produits avec stock bas ou en rupture"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM products
                WHERE merchant_id = ?
                  AND is_available = 1
                  AND stock_quantity != -1
                  AND stock_quantity <= low_stock_threshold
                ORDER BY stock_quantity ASC
                """,
                (merchant_id,)
            )
            rows = await cursor.fetchall()
            return [_row_to_dict(row) for row in rows]

    async def get_out_of_stock_products(self, merchant_id: int) -> List[Dict[str, Any]]:
        """Récupère les produits en rupture de stock"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM products
                WHERE merchant_id = ?
                  AND is_available = 1
                  AND stock_quantity = 0
                ORDER BY name
                """,
                (merchant_id,)
            )
            rows = await cursor.fetchall()
            return [_row_to_dict(row) for row in rows]
