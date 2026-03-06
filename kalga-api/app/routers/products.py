import asyncio
import logging
import os
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from ..database import get_db
from ..database.repositories.product_repo import ProductRepository
from ..models.schemas import ProductCreate
from ..services.visual_search_service import compute_image_embedding, embedding_to_blob
from typing import List, Optional

logger = logging.getLogger("kalga.products")

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")

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


@router.post("/{code}/upload-image")
async def upload_product_image(code: str, file: UploadFile = File(...)):
    """
    Upload une image pour un produit.
    Accepte JPG, PNG, WEBP. Max 5MB.
    Stocke dans /uploads/ et met à jour image_path du produit.
    """
    db = await get_db()

    if not code.startswith("#"):
        code = f"#{code}"

    product = await db.get_product_by_code(code)
    if not product:
        raise HTTPException(status_code=404, detail=f"Produit {code} non trouvé")

    # Validation type
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Format non supporté. Utilise JPG, PNG ou WEBP.")

    # Lecture et limite taille (5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image trop lourde. Maximum 5MB.")

    # Générer un nom unique
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOADS_DIR, filename)
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    with open(filepath, "wb") as f:
        f.write(content)

    # Mettre à jour image_path en base
    await db.products.update(product['id'], image_path=filename)

    # Générer et stocker l'embedding CLIP en arrière-plan (non-bloquant)
    embedding_stored = False
    try:
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(None, compute_image_embedding, content)
        if embedding is not None:
            product_repo = ProductRepository()
            await product_repo.save_embedding(product['id'], embedding_to_blob(embedding))
            embedding_stored = True
            logger.info(f"Embedding CLIP généré pour {code} ({filename})")
        else:
            logger.warning(f"Impossible de générer l'embedding pour {code} (image invalide ou CLIP non dispo)")
    except Exception as e:
        logger.error(f"Erreur génération embedding {code}: {e}")

    return {
        "success": True,
        "product_code": code,
        "image_path": filename,
        "image_url": f"/uploads/{filename}",
        "embedding_generated": embedding_stored,
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
