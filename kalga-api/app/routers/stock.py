"""
Router stock — endpoints pour le dashboard de gestion de stock
"""
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..database.repositories.waitlist_repo import get_waitlist_repository
from ..database.repositories.product_repo import ProductRepository
from ..services.stock_alert_service import get_stock_alert_service
from ..services.notification_service import get_notification_service

router = APIRouter(prefix="/stock", tags=["Gestion Stock"])


class StockModeUpdate(BaseModel):
    mode: str  # waitlist | alert | suspend | preorder


class QuickRestock(BaseModel):
    quantity: int
    notify_waitlist: bool = True


class StockConfigUpdate(BaseModel):
    stock_alert_days: Optional[int] = None
    stock_alerts_enabled: Optional[bool] = None
    waitlist_enabled: Optional[bool] = None
    low_stock_alert_global: Optional[int] = None


# === WIDGET STOCK CRITIQUE (home dashboard) ===

@router.get("/merchant/{merchant_id}/critique")
async def get_stock_critique(merchant_id: int):
    """
    Données pour le widget 'Stock Critique' sur la home dashboard.
    Retourne: ruptures, stock bas, total waitlist, revenus perdus estimés.
    """
    db = await get_db()
    waitlist_repo = get_waitlist_repository()
    product_repo = ProductRepository()

    out_of_stock = await product_repo.get_out_of_stock_products(merchant_id)
    low_stock = await product_repo.get_low_stock_products(merchant_id)
    waitlist_summary = await waitlist_repo.get_merchant_waitlist_summary(merchant_id)
    lost_revenue = await waitlist_repo.get_lost_revenue_estimate(merchant_id, days=7)

    # Enrichir les produits critiques avec leur count waitlist et stock_status
    waitlist_by_product = {w['product_id']: w['waiting_count'] for w in waitlist_summary}

    critical_products = []
    for p in out_of_stock:
        critical_products.append({**p, "stock_status": "out_of_stock", "waitlist_count": waitlist_by_product.get(p['id'], 0)})
    for p in low_stock:
        critical_products.append({**p, "stock_status": "low_stock", "waitlist_count": waitlist_by_product.get(p['id'], 0)})

    return {
        "out_of_stock_count": len(out_of_stock),
        "low_stock_count": len(low_stock),
        "total_waitlist": sum(w['waiting_count'] for w in waitlist_summary),
        "lost_revenue_estimate": lost_revenue.get('estimated_lost', 0) if lost_revenue else 0,
        "critical_products": critical_products
    }


# === PAGE STOCK DÉDIÉE ===

@router.get("/merchant/{merchant_id}/overview")
async def get_stock_overview(merchant_id: int):
    """
    Vue complète du stock pour la page Stock dédiée.
    Tous les produits avec leur stock, waitlist count et statut.
    """
    db = await get_db()
    waitlist_repo = get_waitlist_repository()

    products = await db.get_products_by_merchant(merchant_id)
    waitlist_summary = await waitlist_repo.get_merchant_waitlist_summary(merchant_id)
    waitlist_by_product = {w['product_id']: w for w in waitlist_summary}

    enriched = []
    for p in products:
        stock_qty = p.get('stock_quantity', -1)
        threshold = p.get('low_stock_threshold', 5)
        is_unlimited = stock_qty == -1
        is_out = not is_unlimited and stock_qty == 0
        is_low = not is_unlimited and not is_out and 0 < stock_qty <= threshold

        wl_data = waitlist_by_product.get(p['id'], {})
        stock_status = "out_of_stock" if is_out else ("low_stock" if is_low else ("unlimited" if is_unlimited else "ok"))
        enriched.append({
            **p,
            "stock_status": stock_status,
            "waitlist_count": wl_data.get('waiting_count', 0),
            "oldest_wait_date": wl_data.get('oldest_wait_date')
        })

    # Trier : épuisés > stock bas > normal > illimité
    order = {"out_of_stock": 0, "low_stock": 1, "ok": 2, "unlimited": 3}
    enriched.sort(key=lambda x: (order.get(x['stock_status'], 4), x['name']))

    return enriched


@router.get("/product/{product_id}/waitlist")
async def get_product_waitlist(product_id: int):
    """Détail de la waitlist pour un produit"""
    waitlist_repo = get_waitlist_repository()
    entries = await waitlist_repo.get_waitlist_for_product(product_id)
    return {
        "product_id": product_id,
        "waitlist": entries,
        "count": len(entries)
    }


@router.get("/product/{product_id}/history")
async def get_stock_history(product_id: int, days: int = 30):
    """Historique des événements de stock d'un produit"""
    waitlist_repo = get_waitlist_repository()
    history = await waitlist_repo.get_stock_history(product_id, days=days)
    return {"product_id": product_id, "history": history, "days": days}


# === ACTIONS RAPIDES ===

@router.put("/product/{product_code}/restock")
async def quick_restock(product_code: str, body: QuickRestock):
    """
    Renouvellement rapide du stock d'un produit.
    Déclenche le broadcast waitlist si notify_waitlist=True.
    """
    db = await get_db()
    waitlist_repo = get_waitlist_repository()

    if not product_code.startswith("#"):
        product_code = f"#{product_code}"

    product = await db.get_product_by_code(product_code)
    if not product:
        raise HTTPException(status_code=404, detail=f"Produit {product_code} non trouvé")

    # Mettre à jour le stock (Convex)
    from ..database.repositories.product_repo import ProductRepository
    await ProductRepository().update(product['id'], stock_quantity=body.quantity)

    # Logger l'événement
    try:
        await waitlist_repo.log_stock_event(
            merchant_id=product['merchant_id'],
            product_id=product['id'],
            event_type='restock',
            quantity_delta=body.quantity,
            quantity_after=body.quantity,
            notes="Restock via dashboard"
        )
    except Exception:
        pass

    # Broadcast waitlist (non-bloquant)
    waitlist_count = await waitlist_repo.get_waitlist_count(product['id'])
    notified = 0
    if body.notify_waitlist and waitlist_count > 0:
        from ..database.repositories.merchant_repo import MerchantRepository
        merchant = await MerchantRepository().get_by_id(product['merchant_id'])
        if merchant:
            store_name = merchant.get('business_name') or merchant.get('name') or ''
            asyncio.create_task(
                get_stock_alert_service().broadcast_waitlist_on_restock(
                    merchant_id=product['merchant_id'],
                    merchant_phone=merchant['phone'],
                    product_id=product['id'],
                    product_name=product['name'],
                    product_code=product['code'],
                    new_quantity=body.quantity,
                    store_name=store_name
                )
            )
            notified = min(waitlist_count, body.quantity)

    return {
        "success": True,
        "product_code": product_code,
        "new_quantity": body.quantity,
        "waitlist_notified": notified
    }


@router.put("/product/{product_code}/mode")
async def update_stock_mode(product_code: str, body: StockModeUpdate):
    """Met à jour le mode rupture d'un produit (waitlist|alert|suspend|preorder)"""
    db = await get_db()
    allowed_modes = {'waitlist', 'alert', 'suspend', 'preorder'}
    if body.mode not in allowed_modes:
        raise HTTPException(status_code=400, detail=f"Mode invalide. Valeurs: {allowed_modes}")

    if not product_code.startswith("#"):
        product_code = f"#{product_code}"

    product = await db.get_product_by_code(product_code)
    if not product:
        raise HTTPException(status_code=404, detail=f"Produit {product_code} non trouvé")

    from ..database.repositories.product_repo import ProductRepository
    await ProductRepository().update(product['id'], out_of_stock_mode=body.mode)

    return {"success": True, "product_code": product_code, "mode": body.mode}


# === CONFIGURATION STOCK MARCHAND ===

@router.get("/merchant/{merchant_id}/config")
async def get_stock_config(merchant_id: int):
    """Récupère la configuration stock d'un marchand"""
    from ..database.repositories.merchant_repo import MerchantRepository
    merchant = await MerchantRepository().get_by_id(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")
    return {
        "stock_alert_days": merchant.get("stock_alert_days") if merchant.get("stock_alert_days") is not None else 3,
        "stock_alerts_enabled": bool(merchant["stock_alerts_enabled"]) if merchant.get("stock_alerts_enabled") is not None else True,
        "waitlist_enabled": bool(merchant["waitlist_enabled"]) if merchant.get("waitlist_enabled") is not None else True,
        "low_stock_alert_global": merchant.get("low_stock_alert_global") if merchant.get("low_stock_alert_global") is not None else 5
    }


@router.put("/merchant/{merchant_id}/config")
async def update_stock_config(merchant_id: int, body: StockConfigUpdate):
    """Met à jour la configuration stock d'un marchand"""
    updates = {}
    if body.stock_alert_days is not None:
        updates['stock_alert_days'] = body.stock_alert_days
    if body.stock_alerts_enabled is not None:
        updates['stock_alerts_enabled'] = int(body.stock_alerts_enabled)
    if body.waitlist_enabled is not None:
        updates['waitlist_enabled'] = int(body.waitlist_enabled)
    if body.low_stock_alert_global is not None:
        updates['low_stock_alert_global'] = body.low_stock_alert_global

    if not updates:
        return {"success": True, "message": "Aucun changement"}

    from ..database.repositories.merchant_repo import MerchantRepository
    await MerchantRepository().update(merchant_id, **updates)

    return {"success": True, "updated": updates}
