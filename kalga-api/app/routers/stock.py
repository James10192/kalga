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

    # Enrichir les produits épuisés avec leur count waitlist
    waitlist_by_product = {w['product_id']: w['waiting_count'] for w in waitlist_summary}
    for p in out_of_stock:
        p['waitlist_count'] = waitlist_by_product.get(p['id'], 0)

    return {
        "out_of_stock": out_of_stock,
        "out_of_stock_count": len(out_of_stock),
        "low_stock": low_stock,
        "low_stock_count": len(low_stock),
        "total_waitlist": sum(w['waiting_count'] for w in waitlist_summary),
        "waitlist_by_product": waitlist_summary,
        "lost_revenue": lost_revenue
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

    products = await db.get_products_by_merchant(merchant_id, active_only=False)
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
        enriched.append({
            **p,
            "stock_status": "out" if is_out else ("low" if is_low else ("unlimited" if is_unlimited else "normal")),
            "waitlist_count": wl_data.get('waiting_count', 0),
            "oldest_wait_date": wl_data.get('oldest_wait_date')
        })

    # Trier : épuisés > stock bas > normal
    order = {"out": 0, "low": 1, "normal": 2, "unlimited": 3}
    enriched.sort(key=lambda x: (order.get(x['stock_status'], 4), x['name']))

    return {
        "products": enriched,
        "summary": {
            "total": len(enriched),
            "out_of_stock": sum(1 for p in enriched if p['stock_status'] == 'out'),
            "low_stock": sum(1 for p in enriched if p['stock_status'] == 'low'),
            "normal": sum(1 for p in enriched if p['stock_status'] == 'normal'),
            "unlimited": sum(1 for p in enriched if p['stock_status'] == 'unlimited')
        }
    }


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

    # Mettre à jour le stock
    from ..database.connection import get_connection
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE products SET stock_quantity = ? WHERE id = ?",
            (body.quantity, product['id'])
        )
        await conn.commit()

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
        merchant = await db.get_merchant_by_id(product['merchant_id'])
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

    from ..database.connection import get_connection
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE products SET out_of_stock_mode = ? WHERE id = ?",
            (body.mode, product['id'])
        )
        await conn.commit()

    return {"success": True, "product_code": product_code, "mode": body.mode}


# === CONFIGURATION STOCK MARCHAND ===

@router.get("/merchant/{merchant_id}/config")
async def get_stock_config(merchant_id: int):
    """Récupère la configuration stock d'un marchand"""
    db = await get_db()
    from ..database.connection import get_connection
    async with get_connection() as conn:
        cursor = await conn.execute(
            """SELECT stock_alert_days, stock_alerts_enabled, waitlist_enabled,
                      low_stock_alert_global
               FROM merchants WHERE id = ?""",
            (merchant_id,)
        )
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")
    return {
        "stock_alert_days": row[0] if row[0] is not None else 3,
        "stock_alerts_enabled": bool(row[1]) if row[1] is not None else True,
        "waitlist_enabled": bool(row[2]) if row[2] is not None else True,
        "low_stock_alert_global": row[3] if row[3] is not None else 5
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

    fields = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [merchant_id]

    from ..database.connection import get_connection
    async with get_connection() as conn:
        await conn.execute(
            f"UPDATE merchants SET {fields} WHERE id = ?",
            tuple(values)
        )
        await conn.commit()

    return {"success": True, "updated": updates}
