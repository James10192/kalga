from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database import get_db
from ..models.schemas import ProductCreate
from typing import List, Optional

router = APIRouter(prefix="/products", tags=["Produits"])


class StockUpdate(BaseModel):
    """Schéma pour la mise à jour du stock"""
    quantity: int
    low_stock_threshold: Optional[int] = None


@router.post("/", response_model=dict)
async def create_product(product: ProductCreate):
    """
    Crée un nouveau produit

    - **merchant_id**: ID du marchand
    - **name**: Nom du produit
    - **description**: Description (optionnel)
    - **price**: Prix normal en FCFA
    - **min_price**: Prix minimum négociable en FCFA
    - **image_path**: Chemin vers l'image (optionnel)
    - **group_id**: ID du groupe pour variantes (optionnel)
    - **variant_name**: Nom de la variante (optionnel)
    """
    db = await get_db()

    # Vérifier que min_price <= price
    if product.min_price > product.price:
        raise HTTPException(
            status_code=400,
            detail="Le prix minimum ne peut pas être supérieur au prix normal"
        )

    result = await db.create_product(
        merchant_id=product.merchant_id,
        name=product.name,
        price=product.price,
        min_price=product.min_price,
        description=product.description,
        image_path=product.image_path,
        group_id=product.group_id,
        variant_name=product.variant_name
    )

    return {
        "success": True,
        "message": f"Produit créé: {result['name']} - Code: {result['code']}",
        "product": result,
        "tip": f"Ajoutez {result['code']} à votre Status WhatsApp"
    }


@router.get("/{code}")
async def get_product(code: str):
    """
    Récupère un produit par son code (#K001, etc.)

    Le code doit commencer par #K
    """
    db = await get_db()

    # S'assurer que le code commence par #
    if not code.startswith("#"):
        code = f"#{code}"

    product = await db.get_product_by_code(code)

    if not product:
        raise HTTPException(status_code=404, detail=f"Produit {code} non trouvé")

    return product


@router.get("/{code}/variants")
async def get_product_variants(code: str):
    """
    Récupère les variantes d'un produit (autres couleurs du même groupe)
    """
    db = await get_db()

    if not code.startswith("#"):
        code = f"#{code}"

    product = await db.get_product_by_code(code)
    if not product:
        raise HTTPException(status_code=404, detail=f"Produit {code} non trouvé")

    if not product.get('group_id'):
        return {"variants": [], "message": "Ce produit n'a pas de variantes"}

    variants = await db.get_other_variants(product['id'], product['group_id'])
    return {
        "product": product,
        "variants": variants,
        "count": len(variants)
    }


@router.delete("/{identifier}")
async def deactivate_product(identifier: str):
    """
    Désactive un produit (ne le supprime pas)

    Accepte soit un code produit (#K001) soit un ID numérique
    """
    db = await get_db()

    # Check if identifier is numeric (ID) or code
    if identifier.isdigit():
        # It's an ID
        product = await db.get_product_by_id(int(identifier))
        if not product:
            raise HTTPException(status_code=404, detail=f"Produit ID {identifier} non trouvé")
        code = product['code']
    else:
        # It's a code
        if not identifier.startswith("#"):
            code = f"#{identifier}"
        else:
            code = identifier
        product = await db.get_product_by_code(code)
        if not product:
            raise HTTPException(status_code=404, detail=f"Produit {code} non trouvé")

    await db.deactivate_product(code)

    return {"success": True, "message": f"Produit {code} désactivé"}


# === GESTION DU STOCK ===

@router.get("/{code}/stock")
async def get_product_stock(code: str):
    """
    Récupère le statut du stock d'un produit.
    Retourne: quantity, is_low, is_out_of_stock, is_unlimited
    """
    db = await get_db()

    if not code.startswith("#"):
        code = f"#{code}"

    product = await db.get_product_by_code(code)
    if not product:
        raise HTTPException(status_code=404, detail=f"Produit {code} non trouvé")

    stock_status = await db.products.check_stock_status(product['id'])

    return {
        "product_code": code,
        "product_name": product['name'],
        **stock_status
    }


@router.put("/{code}/stock")
async def update_product_stock(code: str, stock: StockUpdate):
    """
    Met à jour le stock d'un produit.

    - **quantity**: Nouvelle quantité (-1 = illimité)
    - **low_stock_threshold**: Seuil d'alerte stock bas (optionnel)
    """
    db = await get_db()

    if not code.startswith("#"):
        code = f"#{code}"

    product = await db.get_product_by_code(code)
    if not product:
        raise HTTPException(status_code=404, detail=f"Produit {code} non trouvé")

    update_data = {"stock_quantity": stock.quantity}
    if stock.low_stock_threshold is not None:
        update_data["low_stock_threshold"] = stock.low_stock_threshold

    await db.products.update(product['id'], **update_data)

    return {
        "success": True,
        "message": f"Stock mis à jour: {stock.quantity}" + (" (illimité)" if stock.quantity == -1 else " unités"),
        "product_code": code
    }


@router.get("/merchant/{merchant_id}/low-stock")
async def get_merchant_low_stock(merchant_id: int):
    """
    Récupère tous les produits avec stock bas ou en rupture pour un marchand
    """
    db = await get_db()

    low_stock = await db.products.get_low_stock_products(merchant_id)
    out_of_stock = await db.products.get_out_of_stock_products(merchant_id)

    return {
        "merchant_id": merchant_id,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "low_stock_count": len(low_stock),
        "out_of_stock_count": len(out_of_stock)
    }
