"""
Router pour la vitrine publique des marchands.
Tous les endpoints sont publics (pas d'authentification).
IMPORTANT: Ne jamais exposer min_price dans les réponses!
"""
from fastapi import APIRouter, HTTPException, Request
from typing import Optional
import logging

from ..database.repositories.merchant_repo import get_merchant_repository
from ..database.repositories.product_repo import ProductRepository
from ..database.repositories.storefront_order_repo import get_storefront_order_repository
from ..services.notification_service import get_notification_service
from ..models.schemas import StorefrontOrderCreate
from ..rate_limiter import limiter

logger = logging.getLogger("kalga.storefront")

router = APIRouter(prefix="/api/storefront", tags=["Vitrine publique"])

product_repo = ProductRepository()


def _merchant_to_storefront(merchant: dict) -> dict:
    """Convertit un marchand DB en données publiques vitrine"""
    logo_url = None
    if merchant.get("logo_path"):
        logo_url = f"/uploads/{merchant['logo_path']}"

    banner_url = None
    if merchant.get("banner_path"):
        banner_url = f"/uploads/{merchant['banner_path']}"

    return {
        "name": merchant.get("name", ""),
        "business_name": merchant.get("business_name"),
        "phone": merchant["phone"],
        "address": merchant.get("address"),
        "logo_url": logo_url,
        "banner_url": banner_url,
        "about": merchant.get("about"),
        "tagline": merchant.get("tagline"),
    }


def _product_to_storefront(product: dict) -> dict:
    """Convertit un produit DB en produit vitrine (sans min_price!)"""
    image_url = None
    if product.get("image_path"):
        image_url = f"/uploads/{product['image_path']}"

    stock_qty = product.get("stock_quantity", -1)
    is_unlimited = stock_qty == -1
    in_stock = is_unlimited or stock_qty > 0

    return {
        "id": product["id"],
        "code": product["code"],
        "name": product["name"],
        "price": product["price"],
        "description": product.get("description"),
        "image_url": image_url,
        "variant_name": product.get("variant_name"),
        "group_id": product.get("group_id"),
        "in_stock": in_stock,
    }


# === Routes spécifiques EN PREMIER (avant les routes avec paramètres dynamiques) ===

@router.post("/order")
@limiter.limit("5/minute")
async def submit_order(request: Request, order: StorefrontOrderCreate):
    """Soumet une commande depuis la vitrine web"""
    merchant_repo = get_merchant_repository()
    merchant = await merchant_repo.get_by_phone(order.merchant_phone)

    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand introuvable")

    product_code = order.product_code
    if not product_code.startswith("#"):
        product_code = f"#{product_code}"

    product = await product_repo.get_by_code(product_code)
    if not product:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    order_repo = get_storefront_order_repository()
    new_order = await order_repo.create(
        merchant_id=merchant["id"],
        product_id=product["id"],
        client_name=order.client_name,
        client_phone=order.client_phone,
        message=order.message,
    )

    notification_service = get_notification_service()
    await notification_service.notify_storefront_order(
        merchant_phone=merchant["phone"],
        client_name=order.client_name,
        client_phone=order.client_phone,
        product_name=product["name"],
        product_code=product["code"],
        message=order.message,
    )

    logger.info(
        f"Commande web #{new_order['id']} - {order.client_name} -> {product['name']} ({product['code']})"
    )

    return {
        "success": True,
        "order_id": new_order["id"],
        "message": "Commande envoyee! Le marchand vous contactera bientot.",
    }


@router.get("/product/{code}")
async def get_product_detail(code: str):
    """Récupère le détail d'un produit avec ses variantes"""
    if not code.startswith("#"):
        code = f"#{code}"

    product = await product_repo.get_by_code(code)
    if not product:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    result = _product_to_storefront(product)

    variants = []
    if product.get("group_id"):
        raw_variants = await product_repo.get_other_variants(
            product["id"], product["group_id"]
        )
        variants = [_product_to_storefront(v) for v in raw_variants]

    merchant_repo = get_merchant_repository()
    merchant = await merchant_repo.get_by_id(product["merchant_id"])

    return {
        "product": result,
        "variants": variants,
        "merchant": _merchant_to_storefront(merchant) if merchant else {},
    }


# === Routes avec paramètres dynamiques (APRÈS les routes spécifiques) ===

@router.get("/{phone}/products")
async def get_merchant_products(phone: str):
    """Liste tous les produits actifs d'un marchand (sans min_price!)"""
    merchant_repo = get_merchant_repository()
    merchant = await merchant_repo.get_by_phone(phone)

    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand introuvable")

    products = await product_repo.get_by_merchant(merchant["id"], active_only=True)

    return {
        "merchant": _merchant_to_storefront(merchant),
        "products": [_product_to_storefront(p) for p in products],
    }


@router.get("/{phone}")
async def get_merchant_storefront(phone: str):
    """Récupère les infos publiques d'un marchand pour sa vitrine"""
    merchant_repo = get_merchant_repository()
    merchant = await merchant_repo.get_by_phone(phone)

    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand introuvable")

    products = await product_repo.get_by_merchant(merchant["id"], active_only=True)

    storefront_data = _merchant_to_storefront(merchant)
    storefront_data["product_count"] = len(products)
    return storefront_data
