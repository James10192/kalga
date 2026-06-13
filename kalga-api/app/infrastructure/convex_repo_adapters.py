"""
Adaptateurs Convex -> dicts snake_case pour les repos NON hot-path (Phase E2).

Le hot-path chat a ses propres adaptateurs dans `convex_adapters.py`. Ce module
couvre les domaines CRUD/dashboard portés sur Convex en Phase E2 : marchands,
produits, conversations (lecture), stats, abonnements, codes d'activation,
catégories, commandes vitrine, waitlist/journal stock, KB, historique client.

Règles de conversion (parité avec l'ancien SQLite) :
- `_id` Convex (string) -> `id` (string). Les FK camelCase -> snake_case string.
- Les dates : SQLite stockait des ISO strings. Convex renvoie des epoch ms
  (`_creationTime`, `endDate`, ...). Là où un *appelant Python parse la date*
  (ex: `subscription.check_limits` fait `datetime.fromisoformat`), l'adaptateur
  reconvertit l'epoch ms -> ISO string pour préserver le contrat.
- Les champs JSON (preferences, memory_facts, ...) restent des strings brutes,
  comme avec SQLite (l'appelant les `json.loads`).

Aucune dépendance réseau ici : entrée = doc Convex (dict), sortie = dict.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# === Conversions temps ===

def ms_to_iso(ms: Optional[float]) -> Optional[str]:
    """Epoch ms (Convex) -> ISO string locale naïve (parité stockage SQLite)."""
    if ms is None:
        return None
    # SQLite stockait des ISO naïfs en heure locale ; on reste cohérent en
    # produisant un ISO naïf depuis l'epoch ms (UTC -> naïf, suffisant pour la
    # comparaison de bornes côté appelant).
    return datetime.fromtimestamp(ms / 1000.0).isoformat()


def iso_to_ms(value: Optional[str]) -> Optional[float]:
    """ISO string -> epoch ms. None-safe."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt.timestamp() * 1000.0


def now_ms() -> float:
    """Epoch ms courant (UTC)."""
    return datetime.now(timezone.utc).timestamp() * 1000.0


def _id(doc: Dict[str, Any]) -> Optional[str]:
    return doc.get("_id") if doc else None


# === Catégories ===

def adapt_category(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    return {
        "id": doc["_id"],
        "merchant_id": doc.get("merchantId"),
        "name": doc.get("name"),
        "icon": doc.get("icon"),
        "color": doc.get("color"),
        "created_at": ms_to_iso(doc.get("_creationTime")),
        "product_count": doc.get("productCount", 0),
    }


# === Commandes vitrine ===

def adapt_storefront_order(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    out = {
        "id": doc["_id"],
        "merchant_id": doc.get("merchantId"),
        "product_id": doc.get("productId"),
        "client_name": doc.get("clientName"),
        "client_phone": doc.get("clientPhone"),
        "message": doc.get("message"),
        "status": doc.get("status"),
        "created_at": ms_to_iso(doc.get("_creationTime")),
        "updated_at": ms_to_iso(doc.get("_creationTime")),
    }
    # Champs JOIN produit déjà aplatis par la fonction Convex.
    for k in ("productName", "productCode"):
        snake = "product_name" if k == "productName" else "product_code"
        if k in doc:
            out[snake] = doc[k]
    if "price" in doc:
        out["price"] = doc["price"]
    return out


# === Stats ===

def adapt_daily_stats(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """La fonction Convex renvoie déjà des clés snake_case (statRow)."""
    return doc


# === Abonnements ===

def adapt_subscription(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    out = {
        "id": doc["_id"],
        "merchant_id": doc.get("merchantId"),
        "plan": doc.get("plan"),
        "status": doc.get("status"),
        # Dates -> ISO (l'appelant fait datetime.fromisoformat).
        "start_date": ms_to_iso(doc.get("startDate")),
        "end_date": ms_to_iso(doc.get("endDate")),
        "trial_ends_at": ms_to_iso(doc.get("trialEndsAt")),
        "messages_limit": doc.get("messagesLimit", 0),
        "messages_used": doc.get("messagesUsed", 0),
        "products_limit": doc.get("productsLimit", 0),
        "created_at": ms_to_iso(doc.get("_creationTime")),
        "updated_at": ms_to_iso(doc.get("updatedAt")),
    }
    # get_expiring_soon aplatit name/phone/business_name.
    for k in ("name", "phone", "business_name"):
        if k in doc:
            out[k] = doc[k]
    return out


# === Codes d'activation ===

def adapt_activation_code(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    out = {
        "id": doc["_id"],
        "merchant_id": doc.get("merchantId"),
        "code": doc.get("code"),
        "status": doc.get("status"),
        "expires_at": ms_to_iso(doc.get("expiresAt")),
        "used_at": ms_to_iso(doc.get("usedAt")),
        "created_by": doc.get("createdBy"),
        "created_at": ms_to_iso(doc.get("_creationTime")),
    }
    for k in ("merchant_phone", "merchant_name", "admin_email"):
        if k in doc:
            out[k] = doc[k]
    return out


# === Marchands (CRUD non hot-path) ===

def adapt_merchant_full(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Doc marchand complet -> dict snake_case (parité SELECT * merchants)."""
    if not doc:
        return None
    out: Dict[str, Any] = {"id": doc["_id"]}
    direct = ("name", "phone", "slug", "address", "latitude", "longitude",
              "about", "tagline")
    for k in direct:
        if k in doc:
            out[k] = doc[k]
    camel = {
        "businessName": "business_name",
        "awayModeEnabled": "away_mode_enabled",
        "workingHours": "working_hours",
        "awayMessage": "away_message",
        "logoPath": "logo_path",
        "bannerPath": "banner_path",
        "botTone": "bot_tone",
        "botStyle": "bot_style",
        "botCatchphrase": "bot_catchphrase",
        "paymentMethods": "payment_methods",
        "stockAlertDays": "stock_alert_days",
        "stockAlertsEnabled": "stock_alerts_enabled",
        "waitlistEnabled": "waitlist_enabled",
        "lowStockAlertGlobal": "low_stock_alert_global",
        "whatsappRealPhone": "whatsapp_real_phone",
        "whatsappLinkedAt": "whatsapp_linked_at",
    }
    for c, s in camel.items():
        if c in doc:
            out[s] = doc[c]
    out["created_at"] = ms_to_iso(doc.get("_creationTime"))
    return out


def merchant_patch_to_camel(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Patch snake_case (repo.update) -> camelCase Convex (champs autorisés)."""
    mapping = {
        "name": "name", "phone": "phone", "slug": "slug", "address": "address",
        "latitude": "latitude", "longitude": "longitude", "about": "about",
        "tagline": "tagline",
        "business_name": "businessName",
        "away_mode_enabled": "awayModeEnabled",
        "working_hours": "workingHours",
        "away_message": "awayMessage",
        "logo_path": "logoPath",
        "banner_path": "bannerPath",
        "bot_tone": "botTone",
        "bot_style": "botStyle",
        "bot_catchphrase": "botCatchphrase",
        "payment_methods": "paymentMethods",
        "stock_alert_days": "stockAlertDays",
        "stock_alerts_enabled": "stockAlertsEnabled",
        "waitlist_enabled": "waitlistEnabled",
        "low_stock_alert_global": "lowStockAlertGlobal",
        "whatsapp_real_phone": "whatsappRealPhone",
        "whatsapp_linked_at": "whatsappLinkedAt",
        "organization_id": "organizationId",
    }
    out: Dict[str, Any] = {}
    for k, v in kwargs.items():
        if v is None:
            continue
        camel = mapping.get(k)
        if not camel:
            continue
        # away_mode_enabled / *_enabled : SQLite stockait 0/1 ; Convex bool.
        if camel in ("awayModeEnabled", "stockAlertsEnabled", "waitlistEnabled"):
            out[camel] = bool(v)
        else:
            out[camel] = v
    return out


# === Produits (CRUD non hot-path) ===

def adapt_product_full(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Doc produit (embedding déjà exclu côté Convex) -> dict snake_case."""
    if not doc:
        return None
    out: Dict[str, Any] = {"id": doc["_id"]}
    for k in ("name", "code", "price", "description"):
        if k in doc:
            out[k] = doc[k]
    camel = {
        "merchantId": "merchant_id",
        "minPrice": "min_price",
        "imagePath": "image_path",
        "groupId": "group_id",
        "variantName": "variant_name",
        "outOfStockMode": "out_of_stock_mode",
        "stockQuantity": "stock_quantity",
        "lowStockThreshold": "low_stock_threshold",
        "lastStockAlertAt": "last_stock_alert_at",
    }
    for c, s in camel.items():
        if c in doc:
            out[s] = doc[c]
    if "isAvailable" in doc:
        out["is_available"] = 1 if doc["isAvailable"] else 0
    out["created_at"] = ms_to_iso(doc.get("_creationTime"))
    return out


def product_patch_to_camel(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Patch snake_case (repo.update) -> camelCase Convex (champs produits)."""
    mapping = {
        "name": "name", "code": "code", "price": "price",
        "description": "description",
        "min_price": "minPrice",
        "image_path": "imagePath",
        "group_id": "groupId",
        "variant_name": "variantName",
        "out_of_stock_mode": "outOfStockMode",
        "stock_quantity": "stockQuantity",
        "low_stock_threshold": "lowStockThreshold",
        "last_stock_alert_at": "lastStockAlertAt",
    }
    out: Dict[str, Any] = {}
    for k, v in kwargs.items():
        camel = mapping.get(k)
        if camel and v is not None:
            out[camel] = v
    # is_available 0/1 -> isAvailable bool (soft delete).
    if "is_available" in kwargs and kwargs["is_available"] is not None:
        out["isAvailable"] = bool(kwargs["is_available"])
    # last_stock_alert_at peut être une ISO string -> ms.
    if "last_stock_alert_at" in out and isinstance(out["lastStockAlertAt"], str):
        out["lastStockAlertAt"] = iso_to_ms(out["lastStockAlertAt"])
    return out


# === Historique client (non hot-path) ===

def history_patch_to_camel(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Patch snake_case (create_or_update) -> camelCase Convex."""
    mapping = {
        "total_conversations": "totalConversations",
        "total_purchases": "totalPurchases",
        "total_spent": "totalSpent",
        "avg_negotiation_discount": "avgNegotiationDiscount",
        "last_purchase_date": "lastPurchaseDate",
        "last_interaction_date": "lastInteractionDate",
        "preferred_categories": "preferredCategories",
        "negotiation_style": "negotiationStyle",
        "notes": "notes",
        "memory_facts": "memoryFacts",
        "last_session_summary": "lastSessionSummary",
        "preferences": "preferences",
        "conversation_summaries": "conversationSummaries",
    }
    out: Dict[str, Any] = {}
    for k, v in kwargs.items():
        camel = mapping.get(k)
        if not camel or v is None:
            continue
        # Les dates ISO -> ms.
        if camel in ("lastPurchaseDate", "lastInteractionDate") and isinstance(v, str):
            out[camel] = iso_to_ms(v)
        else:
            out[camel] = v
    return out


def adapt_client_history(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Le doc renvoyé par `internal/clienthistory:get` est DÉJÀ snake_case (toDict).
    On reconvertit les dates ms -> ISO et on parse preferred_categories (JSON)
    pour parité exacte avec l'ancien repo SQLite.
    """
    if not doc:
        return None
    import json
    out = dict(doc)
    for k in ("last_purchase_date", "last_interaction_date", "updated_at"):
        if isinstance(out.get(k), (int, float)):
            out[k] = ms_to_iso(out[k])
    pc = out.get("preferred_categories")
    if pc:
        try:
            out["preferred_categories"] = json.loads(pc)
        except (json.JSONDecodeError, TypeError):
            out["preferred_categories"] = []
    else:
        out["preferred_categories"] = []
    return out
