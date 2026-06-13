"""
Repository pour la gestion des produits.

Phase E2 : délègue à Convex (`internal/catalog:*` et `internal/inventory:*`).
Signatures publiques inchangées.

EXCEPTION (STOP, hors scope 004 — tied D8 ML offload) : les embeddings CLIP
`get_all_with_embeddings` / `save_embedding` RESTENT sur SQLite. Le BLOB binaire
numpy float32 n'a pas d'équivalent pratique en round-trip Convex (le schéma a
`imageEmbedding: v.array(v.float64())`, conversion float32<->float64 + pas
d'index vectoriel encore). Ces 2 méthodes gardent `get_connection`.
"""
from typing import Optional, List, Dict, Any

from ..connection import get_connection
from app.infrastructure.convex_client import get_convex
from app.infrastructure.convex_repo_adapters import (
    adapt_product_full,
    product_patch_to_camel,
)


class ProductRepository:
    """Gère les opérations CRUD pour les produits (backend Convex sauf embeddings)."""

    async def get_by_id(self, id):
        """Produit par id (embedding exclu)."""
        doc = await get_convex().query("internal/catalog:getById", {
            "productId": id,
        })
        return adapt_product_full(doc)

    async def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Récupère un produit actif par son code (#K001, etc.)."""
        result = await get_convex().query("internal/inventory:checkProduct", {
            "code": code,
        })
        if not result or not result.get("product"):
            return None
        return adapt_product_full(result["product"])

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
        """Crée un nouveau produit avec un code auto-généré."""
        args: Dict[str, Any] = {
            "merchantId": merchant_id,
            "name": name,
            "price": price,
            "minPrice": min_price,
            "stockQuantity": stock_quantity,
            "lowStockThreshold": low_stock_threshold,
        }
        if description is not None:
            args["description"] = description
        if image_path is not None:
            args["imagePath"] = image_path
        if group_id is not None:
            args["groupId"] = group_id
        if variant_name is not None:
            args["variantName"] = variant_name
        doc = await get_convex().mutation("internal/catalog:create", args)
        return adapt_product_full(doc)

    async def create_variants_batch(
        self,
        merchant_id: int,
        base_name: str,
        price: float,
        min_price: float,
        description: Optional[str],
        group_id: str,
        variants: List[Dict[str, Any]],
        stock_quantity: int = -1,
        low_stock_threshold: int = 5,
    ) -> List[Dict[str, Any]]:
        """Crée N variantes partageant prix/group_id (transaction atomique Convex)."""
        if not variants:
            raise ValueError("La liste de variantes ne peut pas être vide")
        for v in variants:
            name = v.get("variant_name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("variant_name manquant ou vide dans le lot")

        payload = [
            {
                "variantName": v["variant_name"],
                **({"imagePath": v["image_path"]} if v.get("image_path") else {}),
            }
            for v in variants
        ]
        args: Dict[str, Any] = {
            "merchantId": merchant_id,
            "baseName": base_name,
            "price": price,
            "minPrice": min_price,
            "groupId": group_id,
            "variants": payload,
            "stockQuantity": stock_quantity,
            "lowStockThreshold": low_stock_threshold,
        }
        if description is not None:
            args["description"] = description
        docs = await get_convex().mutation("internal/catalog:createVariantsBatch", args)
        return [adapt_product_full(d) for d in (docs or [])]

    async def update(self, product_id: int, **kwargs) -> bool:
        """Met à jour un produit avec les champs fournis."""
        if not kwargs:
            return False
        patch = product_patch_to_camel(kwargs)
        if not patch:
            return False
        result = await get_convex().mutation("internal/catalog:update", {
            "productId": product_id,
            "patch": patch,
        })
        return bool(result and result.get("updated"))

    async def get_by_merchant(
        self,
        merchant_id: int,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Récupère tous les produits d'un marchand."""
        docs = await get_convex().query("internal/inventory:listProductsForTools", {
            "merchantId": merchant_id,
        })
        result = [adapt_product_full(d) for d in (docs or [])]
        # listProductsForTools renvoie déjà uniquement les produits actifs.
        return result

    async def get_other_variants(
        self,
        product_id: int,
        group_id: str
    ) -> List[Dict[str, Any]]:
        """Récupère les autres variantes d'un produit (même group_id)."""
        docs = await get_convex().query("internal/catalog:getInGroup", {
            "groupId": group_id,
            "excludeId": product_id,
        })
        return [adapt_product_full(d) for d in (docs or [])]

    async def get_all_in_group(self, group_id: str) -> List[Dict[str, Any]]:
        """Récupère TOUTES les variantes d'un groupe."""
        docs = await get_convex().query("internal/catalog:getInGroup", {
            "groupId": group_id,
        })
        return [adapt_product_full(d) for d in (docs or [])]

    async def deactivate(self, product_id: int) -> bool:
        """Désactive un produit (soft delete)."""
        return await self.update(product_id, is_available=0)

    async def get_next_code(self) -> str:
        """Retourne le prochain code produit disponible."""
        return await get_convex().query("internal/catalog:getNextCode", {})

    # === EMBEDDINGS CLIP (recherche visuelle) — RESTE SUR SQLITE (D8, hors 004) ===

    async def get_all_with_embeddings(self, merchant_id: int) -> list:
        """Retourne (product_id, product_code, embedding_blob, name, price, description).

        TODO Phase D8 : le BLOB embedding CLIP (numpy float32) reste sur SQLite —
        round-trip Convex impraticable (cf. en-tête module).
        """
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT id, code, embedding, name, price, description FROM products WHERE merchant_id=? AND is_available=1",
                (merchant_id,)
            )
            rows = await cursor.fetchall()
            return [(row[0], row[1], row[2], row[3], row[4], row[5]) for row in rows]

    async def save_embedding(self, product_id: int, embedding_blob: bytes) -> bool:
        """Sauvegarde l'embedding CLIP d'un produit (SQLite — voir TODO ci-dessus)."""
        async with get_connection() as db:
            cursor = await db.execute(
                "UPDATE products SET embedding=? WHERE id=?",
                (embedding_blob, product_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    # === GESTION DU STOCK ===

    async def update_stock(self, product_id: int, quantity: int) -> bool:
        """Met à jour la quantité en stock."""
        return await self.update(product_id, stock_quantity=quantity)

    async def decrement_stock(self, product_id: int, quantity: int = 1) -> Dict[str, Any]:
        """Décrémente le stock d'un produit (atomique côté Convex)."""
        result = await get_convex().mutation("internal/inventory:decrementStock", {
            "productId": product_id,
            "quantity": quantity,
        })
        if result is None:
            return None
        # decrementStock renvoie {stockStatus, decremented} — on relit le produit
        # complet pour parité (l'ancien repo renvoyait le dict produit à jour).
        product = await self.get_by_id(product_id)
        if product is not None and result.get("stockStatus"):
            product["stock_quantity"] = result["stockStatus"].get("quantity")
        return product

    async def check_stock_status(self, product_id: int) -> Dict[str, Any]:
        """Vérifie le statut du stock d'un produit."""
        doc = await get_convex().query("internal/catalog:getById", {
            "productId": product_id,
        })
        if not doc:
            return None
        quantity = doc.get("stockQuantity")
        quantity = -1 if quantity is None else quantity
        threshold = doc.get("lowStockThreshold")
        threshold = 5 if threshold is None else threshold
        is_unlimited = quantity == -1
        return {
            "available": is_unlimited or quantity > 0,
            "quantity": quantity,
            "is_low": not is_unlimited and 0 < quantity <= threshold,
            "is_out_of_stock": not is_unlimited and quantity == 0,
            "is_unlimited": is_unlimited,
            "threshold": threshold,
        }

    async def get_low_stock_products(self, merchant_id: int) -> List[Dict[str, Any]]:
        """Récupère les produits avec stock bas ou en rupture."""
        docs = await get_convex().query("internal/catalog:getLowStock", {
            "merchantId": merchant_id,
        })
        return [adapt_product_full(d) for d in (docs or [])]

    async def get_out_of_stock_products(self, merchant_id: int) -> List[Dict[str, Any]]:
        """Récupère les produits en rupture de stock."""
        docs = await get_convex().query("internal/catalog:getOutOfStock", {
            "merchantId": merchant_id,
        })
        return [adapt_product_full(d) for d in (docs or [])]
