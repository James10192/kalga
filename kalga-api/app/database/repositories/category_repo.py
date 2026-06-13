"""
Repository pour la gestion des catégories de produits.

Phase E2 : délègue à Convex (`internal/category:*`). Signatures publiques
inchangées (les routers continuent de consommer les mêmes dicts snake_case).
"""
from typing import Optional, List, Dict, Any

from app.infrastructure.convex_client import get_convex
from app.infrastructure.convex_repo_adapters import adapt_category


class CategoryRepository:
    """Gère les opérations CRUD pour les catégories (backend Convex)."""

    async def create(
        self,
        merchant_id: int,
        name: str,
        icon: str = "📦",
        color: str = "#667eea"
    ) -> Dict[str, Any]:
        """Crée une nouvelle catégorie."""
        doc = await get_convex().mutation("internal/category:create", {
            "merchantId": merchant_id,
            "name": name,
            "icon": icon,
            "color": color,
        })
        return adapt_category(doc)

    async def get_by_merchant(self, merchant_id: int) -> List[Dict[str, Any]]:
        """Récupère toutes les catégories d'un marchand (+ product_count)."""
        docs = await get_convex().query("internal/category:listByMerchant", {
            "merchantId": merchant_id,
        })
        return [adapt_category(d) for d in (docs or [])]

    async def get_by_name(self, merchant_id: int, name: str) -> Optional[Dict[str, Any]]:
        """Récupère une catégorie par son nom."""
        doc = await get_convex().query("internal/category:getByName", {
            "merchantId": merchant_id,
            "name": name,
        })
        return adapt_category(doc)

    async def update(self, category_id: int, **kwargs) -> bool:
        """Met à jour une catégorie (name/icon/color)."""
        if not kwargs:
            return False
        args: Dict[str, Any] = {"categoryId": category_id}
        for key in ("name", "icon", "color"):
            if key in kwargs and kwargs[key] is not None:
                args[key] = kwargs[key]
        result = await get_convex().mutation("internal/category:update", args)
        return bool(result and result.get("updated"))

    async def delete(self, category_id: int) -> bool:
        """Supprime une catégorie."""
        result = await get_convex().mutation("internal/category:remove", {
            "categoryId": category_id,
        })
        return bool(result and result.get("deleted"))
