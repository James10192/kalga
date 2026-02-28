"""
Routes d'administration pour KALGA
Dashboard admin, monitoring marchands, gestion abonnements
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import httpx

from ..services.auth_service import get_current_admin
from ..services.activation_service import get_activation_service
from ..database.repositories.user_repo import get_user_repository
from ..database.repositories.merchant_repo import get_merchant_repository
from ..database.repositories.subscription_repo import get_subscription_repository
from ..database.repositories.conversation_repo import get_conversation_repository
from ..database.connection import get_connection
from ..config import settings

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ============================================
# SCHEMAS
# ============================================

class MerchantStatusUpdate(BaseModel):
    is_active: bool
    reason: Optional[str] = None


class SubscriptionUpdate(BaseModel):
    plan: str
    duration_months: int = 1
    messages_limit: int = 5000
    products_limit: int = 100


class CreateAdminRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = "Admin"


# ============================================
# DASHBOARD STATS
# ============================================

@router.get("/dashboard")
async def get_admin_dashboard(admin: dict = Depends(get_current_admin)):
    """
    Statistiques globales pour le dashboard admin.
    """
    async with get_connection() as db:
        # Nombre total de marchands
        cursor = await db.execute("SELECT COUNT(*) as total FROM merchants")
        merchants_total = (await cursor.fetchone())["total"]

        # Marchands actifs (avec subscription active)
        cursor = await db.execute("""
            SELECT COUNT(*) as total FROM subscriptions WHERE status = 'active'
        """)
        merchants_active = (await cursor.fetchone())["total"]

        # Nouveaux marchands ce mois
        cursor = await db.execute("""
            SELECT COUNT(*) as total FROM merchants
            WHERE created_at >= date('now', 'start of month')
        """)
        merchants_this_month = (await cursor.fetchone())["total"]

        # Total conversations
        cursor = await db.execute("SELECT COUNT(*) as total FROM conversations")
        conversations_total = (await cursor.fetchone())["total"]

        # Conversations aujourd'hui
        cursor = await db.execute("""
            SELECT COUNT(*) as total FROM conversations
            WHERE date(created_at) = date('now')
        """)
        conversations_today = (await cursor.fetchone())["total"]

        # Total messages
        cursor = await db.execute("SELECT COUNT(*) as total FROM messages")
        messages_total = (await cursor.fetchone())["total"]

        # Ventes (conversations avec status completed)
        cursor = await db.execute("""
            SELECT COUNT(*) as total FROM conversations
            WHERE status IN ('completed', 'pending_delivery', 'pending_pickup')
        """)
        sales_total = (await cursor.fetchone())["total"]

        # Abonnements par plan
        cursor = await db.execute("""
            SELECT plan, COUNT(*) as count FROM subscriptions
            GROUP BY plan
        """)
        plans = {row["plan"]: row["count"] for row in await cursor.fetchall()}

        # Abonnements expirant bientôt (7 jours)
        subscription_repo = get_subscription_repository()
        expiring_soon = await subscription_repo.get_expiring_soon(7)

    return {
        "merchants": {
            "total": merchants_total,
            "active": merchants_active,
            "this_month": merchants_this_month
        },
        "conversations": {
            "total": conversations_total,
            "today": conversations_today
        },
        "messages": {
            "total": messages_total
        },
        "sales": {
            "total": sales_total
        },
        "subscriptions": {
            "by_plan": plans,
            "expiring_soon": len(expiring_soon)
        },
        "expiring_subscriptions": expiring_soon[:5]  # Top 5
    }


# ============================================
# GESTION DES MARCHANDS
# ============================================

@router.get("/merchants")
async def list_merchants(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, regex="^(active|inactive|trial|expired)$"),
    search: Optional[str] = None,
    admin: dict = Depends(get_current_admin)
):
    """
    Liste tous les marchands avec pagination et filtres.
    """
    user_repo = get_user_repository()
    result = await user_repo.get_all_merchants(
        page=page,
        limit=limit,
        status_filter=status_filter
    )

    # Ajouter le statut WhatsApp pour chaque marchand (en parallèle)
    import asyncio

    async def fetch_wa_status(client: httpx.AsyncClient, phone: str) -> str:
        try:
            response = await client.get(
                f"{settings.whatsapp_bridge_url}/status/{phone}",
                timeout=1.5
            )
            if response.status_code == 200:
                data = response.json()
                return "ready" if data.get("ready") else "disconnected"
            if response.status_code == 404:
                return "not_registered"
            return "disconnected"
        except Exception:
            return "disconnected"

    async def no_phone() -> str:
        return "no_phone"

    async with httpx.AsyncClient() as client:
        wa_statuses = await asyncio.gather(*[
            fetch_wa_status(client, m["phone"]) if m.get("phone") else no_phone()
            for m in result["merchants"]
        ])

    merchants_with_status = []
    for m, wa_status in zip(result["merchants"], wa_statuses):
        merchant_data = dict(m)
        merchant_data["whatsapp_status"] = wa_status
        merchants_with_status.append(merchant_data)

    result["merchants"] = merchants_with_status
    return result


@router.get("/merchants/{merchant_id}")
async def get_merchant_details(
    merchant_id: int,
    admin: dict = Depends(get_current_admin)
):
    """
    Détails complets d'un marchand.
    """
    merchant_repo = get_merchant_repository()
    subscription_repo = get_subscription_repository()
    conversation_repo = get_conversation_repository()

    merchant = await merchant_repo.get_by_id(merchant_id)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marchand non trouvé"
        )

    subscription = await subscription_repo.get_by_merchant(merchant_id)

    # Stats du marchand
    async with get_connection() as db:
        # Nombre de produits
        cursor = await db.execute(
            "SELECT COUNT(*) as total FROM products WHERE merchant_id = ?",
            (merchant_id,)
        )
        products_count = (await cursor.fetchone())["total"]

        # Nombre de conversations
        cursor = await db.execute(
            "SELECT COUNT(*) as total FROM conversations WHERE merchant_id = ?",
            (merchant_id,)
        )
        conversations_count = (await cursor.fetchone())["total"]

        # Nombre de ventes
        cursor = await db.execute("""
            SELECT COUNT(*) as total FROM conversations
            WHERE merchant_id = ? AND status IN ('completed', 'pending_delivery', 'pending_pickup')
        """, (merchant_id,))
        sales_count = (await cursor.fetchone())["total"]

        # Dernières conversations
        cursor = await db.execute("""
            SELECT c.*, p.name as product_name, p.code as product_code
            FROM conversations c
            JOIN products p ON c.product_id = p.id
            WHERE c.merchant_id = ?
            ORDER BY c.updated_at DESC
            LIMIT 10
        """, (merchant_id,))
        recent_conversations = [dict(row) for row in await cursor.fetchall()]

    # User associé
    user_repo = get_user_repository()
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE merchant_id = ?",
            (merchant_id,)
        )
        user = await cursor.fetchone()

    # Statut WhatsApp
    whatsapp_status = "unknown"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.whatsapp_bridge_url}/status/{merchant['phone']}",
                timeout=2.0
            )
            if response.status_code == 200:
                data = response.json()
                whatsapp_status = "ready" if data.get("ready") else "disconnected"
            elif response.status_code == 404:
                whatsapp_status = "not_registered"
    except Exception:
        pass

    # Compte réel de messages
    real_messages_count = 0
    async with get_connection() as db:
        cursor = await db.execute(
            """
            SELECT COUNT(msg.id) as total
            FROM conversations c
            JOIN messages msg ON msg.conversation_id = c.id
            WHERE c.merchant_id = ?
            """,
            (merchant_id,)
        )
        real_messages_count = (await cursor.fetchone())["total"]

    return {
        "merchant": merchant,
        "user": dict(user) if user else None,
        "subscription": subscription,
        "whatsapp_status": whatsapp_status,
        "real_messages_count": real_messages_count,
        "stats": {
            "products": products_count,
            "conversations": conversations_count,
            "sales": sales_count
        },
        "recent_conversations": recent_conversations
    }


@router.put("/merchants/{merchant_id}/status")
async def update_merchant_status(
    merchant_id: int,
    update: MerchantStatusUpdate,
    admin: dict = Depends(get_current_admin)
):
    """
    Active ou désactive un marchand.
    """
    user_repo = get_user_repository()

    # Trouver l'utilisateur associé
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT id FROM users WHERE merchant_id = ?",
            (merchant_id,)
        )
        user = await cursor.fetchone()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur du marchand non trouvé"
        )

    await user_repo.set_active(user["id"], update.is_active)

    # Log l'action
    await _log_admin_action(
        admin["id"],
        "merchant_status_update",
        "merchant",
        merchant_id,
        {"is_active": update.is_active, "reason": update.reason}
    )

    action = "activé" if update.is_active else "désactivé"
    return {"message": f"Marchand {action} avec succès"}


@router.put("/merchants/{merchant_id}/subscription")
async def update_merchant_subscription(
    merchant_id: int,
    update: SubscriptionUpdate,
    admin: dict = Depends(get_current_admin)
):
    """
    Met à jour l'abonnement d'un marchand.
    """
    subscription_repo = get_subscription_repository()

    existing = await subscription_repo.get_by_merchant(merchant_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Abonnement non trouvé"
        )

    result = await subscription_repo.upgrade_plan(
        merchant_id=merchant_id,
        plan=update.plan,
        duration_months=update.duration_months,
        messages_limit=update.messages_limit,
        products_limit=update.products_limit
    )

    await _log_admin_action(
        admin["id"],
        "subscription_update",
        "subscription",
        existing["id"],
        update.dict()
    )

    return result


# ============================================
# GESTION DES ADMINS
# ============================================

@router.get("/admins")
async def list_admins(admin: dict = Depends(get_current_admin)):
    """
    Liste tous les administrateurs.
    """
    user_repo = get_user_repository()
    admins = await user_repo.get_admin_users()

    # Ne pas retourner les password_hash
    return [{
        "id": a["id"],
        "email": a["email"],
        "is_active": a["is_active"],
        "last_login": a.get("last_login"),
        "created_at": a["created_at"]
    } for a in admins]


@router.post("/admins")
async def create_admin(
    request: CreateAdminRequest,
    admin: dict = Depends(get_current_admin)
):
    """
    Crée un nouvel administrateur.
    """
    user_repo = get_user_repository()

    existing = await user_repo.get_by_email(request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà utilisé"
        )

    new_admin = await user_repo.create_user(
        email=request.email,
        password=request.password,
        role="admin",
        is_verified=True
    )

    await _log_admin_action(
        admin["id"],
        "admin_created",
        "user",
        new_admin["id"],
        {"email": request.email}
    )

    return {
        "id": new_admin["id"],
        "email": new_admin["email"],
        "message": "Administrateur créé avec succès"
    }


# ============================================
# LOGS D'AUDIT
# ============================================

@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin: dict = Depends(get_current_admin)
):
    """
    Récupère les logs d'audit des actions admin.
    """
    offset = (page - 1) * limit

    async with get_connection() as db:
        cursor = await db.execute("""
            SELECT l.*, u.email as admin_email
            FROM admin_audit_logs l
            JOIN users u ON l.admin_user_id = u.id
            ORDER BY l.created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        logs = [dict(row) for row in await cursor.fetchall()]

        cursor = await db.execute("SELECT COUNT(*) as total FROM admin_audit_logs")
        total = (await cursor.fetchone())["total"]

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


# ============================================
# ACTIONS SYSTEME
# ============================================

@router.post("/system/cleanup-expired")
async def cleanup_expired_subscriptions(
    admin: dict = Depends(get_current_admin)
):
    """
    Marque les abonnements expirés et nettoie les conversations anciennes.
    """
    subscription_repo = get_subscription_repository()

    # Marquer les abonnements expirés
    expired_count = await subscription_repo.mark_expired()

    # Nettoyer les conversations expirées
    from ..database.repositories.conversation_repo import get_conversation_repository
    conversation_repo = get_conversation_repository()
    cleaned = await conversation_repo.cleanup_expired()

    await _log_admin_action(
        admin["id"],
        "system_cleanup",
        "system",
        None,
        {"expired_subscriptions": expired_count, "cleaned_conversations": cleaned}
    )

    return {
        "expired_subscriptions_marked": expired_count,
        "conversations_cleaned": cleaned
    }


@router.get("/system/whatsapp-status")
async def get_all_whatsapp_status(admin: dict = Depends(get_current_admin)):
    """
    Récupère le statut WhatsApp de tous les marchands.
    """
    merchant_repo = get_merchant_repository()

    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT id, name, phone FROM merchants WHERE phone IS NOT NULL"
        )
        merchants = [dict(row) for row in await cursor.fetchall()]

    statuses = []
    for m in merchants:
        status_data = {"merchant_id": m["id"], "name": m["name"], "phone": m["phone"]}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.whatsapp_bridge_url}/status/{m['phone']}",
                    timeout=2.0
                )
                if response.status_code == 200:
                    wa_data = response.json()
                    status_data["status"] = wa_data.get("status", "unknown")
                    status_data["ready"] = wa_data.get("ready", False)
                else:
                    status_data["status"] = "error"
                    status_data["ready"] = False
        except Exception as e:
            status_data["status"] = "unreachable"
            status_data["ready"] = False

        statuses.append(status_data)

    connected = len([s for s in statuses if s.get("ready")])

    return {
        "total": len(statuses),
        "connected": connected,
        "disconnected": len(statuses) - connected,
        "statuses": statuses
    }


# ============================================
# GESTION DES ACTIVATIONS
# ============================================

@router.get("/pending-activations")
async def get_pending_activations(admin: dict = Depends(get_current_admin)):
    """
    Liste tous les marchands en attente d'activation.
    Ce sont les marchands qui ont scanné le QR mais n'ont pas encore d'abonnement actif.
    """
    activation_service = get_activation_service()
    pending = await activation_service.get_pending_activations()

    # Ajouter le statut WhatsApp pour chaque marchand
    result = []
    for m in pending:
        merchant_data = dict(m)

        # Vérifier le statut WhatsApp
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.whatsapp_bridge_url}/status/{m['phone']}",
                    timeout=2.0
                )
                if response.status_code == 200:
                    wa_data = response.json()
                    merchant_data["whatsapp_connected"] = wa_data.get("ready", False)
                else:
                    merchant_data["whatsapp_connected"] = False
        except Exception:
            merchant_data["whatsapp_connected"] = False

        result.append(merchant_data)

    return {
        "count": len(result),
        "merchants": result
    }


@router.post("/send-activation/{merchant_id}")
async def send_activation_code(
    merchant_id: int,
    admin: dict = Depends(get_current_admin)
):
    """
    Génère et envoie un code d'activation à un marchand.
    Le code est envoyé via WhatsApp.
    """
    activation_service = get_activation_service()

    result = await activation_service.generate_and_send_code(
        merchant_id=merchant_id,
        admin_id=admin["id"]
    )

    if result["success"]:
        await _log_admin_action(
            admin["id"],
            "activation_code_sent",
            "merchant",
            merchant_id,
            {"code": result["code"]}
        )

    return result


@router.get("/activation-history")
async def get_activation_history(
    limit: int = Query(50, ge=1, le=200),
    admin: dict = Depends(get_current_admin)
):
    """
    Historique des codes d'activation générés.
    """
    activation_service = get_activation_service()
    history = await activation_service.get_activation_history(limit)

    return {
        "count": len(history),
        "history": history
    }


# ============================================
# HELPERS
# ============================================

async def _log_admin_action(
    admin_id: int,
    action: str,
    target_type: str,
    target_id: Optional[int],
    details: dict
):
    """Log une action admin pour audit"""
    import json

    async with get_connection() as db:
        await db.execute(
            """
            INSERT INTO admin_audit_logs (
                admin_user_id, action, target_type, target_id, details, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                admin_id,
                action,
                target_type,
                target_id,
                json.dumps(details),
                datetime.now().isoformat()
            )
        )
        await db.commit()
