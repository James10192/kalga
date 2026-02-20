"""
Router pour les catégories de produits
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ..database.repositories.category_repo import CategoryRepository
from ..database.repositories import MerchantRepository

router = APIRouter(prefix="/api/categories", tags=["categories"])

category_repo = CategoryRepository()
merchant_repo = MerchantRepository()


class CategoryCreate(BaseModel):
    """Schéma pour créer une catégorie"""
    name: str
    icon: Optional[str] = "📦"
    color: Optional[str] = "#667eea"


class CategoryUpdate(BaseModel):
    """Schéma pour mettre à jour une catégorie"""
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


@router.get("/{merchant_phone}")
async def get_merchant_categories(merchant_phone: str):
    """
    Récupère toutes les catégories d'un marchand.
    """
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    categories = await category_repo.get_by_merchant(merchant["id"])

    return {
        "merchant_id": merchant["id"],
        "categories": categories
    }


@router.post("/{merchant_phone}")
async def create_category(merchant_phone: str, category: CategoryCreate):
    """
    Crée une nouvelle catégorie pour un marchand.
    """
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    # Vérifier si la catégorie existe déjà
    existing = await category_repo.get_by_name(merchant["id"], category.name)
    if existing:
        raise HTTPException(status_code=400, detail="Cette catégorie existe déjà")

    new_category = await category_repo.create(
        merchant_id=merchant["id"],
        name=category.name,
        icon=category.icon,
        color=category.color
    )

    return {
        "success": True,
        "category": new_category
    }


@router.put("/{category_id}")
async def update_category(category_id: int, category: CategoryUpdate):
    """
    Met à jour une catégorie.
    """
    update_data = {k: v for k, v in category.dict().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")

    success = await category_repo.update(category_id, **update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Catégorie non trouvée")

    return {"success": True}


@router.delete("/{category_id}")
async def delete_category(category_id: int):
    """
    Supprime une catégorie.
    Les produits de cette catégorie seront mis sans catégorie.
    """
    success = await category_repo.delete(category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Catégorie non trouvée")

    return {"success": True}


# Icônes prédéfinies pour les catégories
CATEGORY_ICONS = [
    "📦", "👕", "👗", "👠", "👜", "💍", "📱", "💻", "🎧", "🎮",
    "🏠", "🚗", "🍕", "🍔", "☕", "🍷", "💄", "🧴", "🏋️", "⚽",
    "📚", "🎨", "🎵", "🎬", "✈️", "🏖️", "💼", "🛠️", "🌸", "🎁"
]

CATEGORY_COLORS = [
    "#667eea", "#764ba2", "#25d366", "#10b981", "#f59e0b",
    "#ef4444", "#3b82f6", "#8b5cf6", "#ec4899", "#06b6d4"
]


@router.get("/options/icons")
async def get_category_icons():
    """Retourne la liste des icônes disponibles pour les catégories"""
    return {"icons": CATEGORY_ICONS}


@router.get("/options/colors")
async def get_category_colors():
    """Retourne la liste des couleurs disponibles pour les catégories"""
    return {"colors": CATEGORY_COLORS}
