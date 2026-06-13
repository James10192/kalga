"""
Adaptateurs Convex -> forme dict snake_case attendue par le cerveau v2.

Le chemin chat hot-path lit désormais Convex (`internal/chat:getContext`,
`internal/inventory:*`). Les documents Convex sont en camelCase et portent un
`_id` STRING. Le moteur de dialogue v2 (`app/services/dialogue/`) et le code
aval de `chat_service.py` consomment historiquement la forme SQLite snake_case
(`id`, `min_price`, `image_path`, `group_id`, `current_offer`, ...).

Ces fonctions PURES traduisent l'un vers l'autre SANS rien convertir d'autre :
les identifiants Convex restent des STRINGS de bout en bout (plus d'entiers sur
le hot-path). Le cerveau v2 reste donc INCHANGÉ dans ses accès dict.

Aucune dépendance réseau / DB ici : entrée = doc Convex (dict), sortie = dict.
"""
from typing import Any, Dict, List, Optional


def _pick(doc: Dict[str, Any], camel: str, snake: str, out: Dict[str, Any]) -> None:
    """Recopie doc[camel] -> out[snake] uniquement si la clé existe."""
    if camel in doc and doc[camel] is not None:
        out[snake] = doc[camel]


def adapt_merchant(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Doc Convex `merchants` -> dict marchand snake_case (id = string)."""
    if not doc:
        return None
    out: Dict[str, Any] = {
        "id": doc["_id"],  # string Convex, threadé tel quel
    }
    # Champs directs (même nom)
    for key in (
        "name", "phone", "slug", "address", "latitude", "longitude",
        "about", "tagline",
    ):
        _pick(doc, key, key, out)
    # camelCase -> snake_case
    _pick(doc, "businessName", "business_name", out)
    _pick(doc, "awayModeEnabled", "away_mode_enabled", out)
    _pick(doc, "awayMessage", "away_message", out)
    _pick(doc, "botTone", "bot_tone", out)
    _pick(doc, "botStyle", "bot_style", out)
    _pick(doc, "botCatchphrase", "bot_catchphrase", out)
    # paymentMethods (JSON) est l'équivalent du payment_info/payment_methods SQLite ;
    # le cerveau v2 lit `payment_info` puis `payment_methods` en repli.
    _pick(doc, "paymentMethods", "payment_methods", out)
    return out


def adapt_product(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Doc Convex `products` -> dict produit snake_case (id/merchant_id/group_id = string)."""
    if not doc:
        return None
    out: Dict[str, Any] = {
        "id": doc["_id"],
    }
    for key in ("name", "code", "price", "description", "category"):
        _pick(doc, key, key, out)
    _pick(doc, "merchantId", "merchant_id", out)
    _pick(doc, "minPrice", "min_price", out)
    _pick(doc, "imagePath", "image_path", out)
    _pick(doc, "groupId", "group_id", out)
    _pick(doc, "variantName", "variant_name", out)
    _pick(doc, "outOfStockMode", "out_of_stock_mode", out)
    _pick(doc, "stockQuantity", "stock_quantity", out)
    _pick(doc, "lowStockThreshold", "low_stock_threshold", out)
    return out


def adapt_conversation(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Doc Convex `conversations` -> dict conversation snake_case (ids = string)."""
    if not doc:
        return None
    out: Dict[str, Any] = {
        "id": doc["_id"],
        "status": doc.get("status", "active"),
    }
    _pick(doc, "merchantId", "merchant_id", out)
    _pick(doc, "productId", "product_id", out)
    _pick(doc, "clientPhone", "client_phone", out)
    _pick(doc, "currentOffer", "current_offer", out)
    _pick(doc, "selectedVariantId", "selected_variant_id", out)
    return out


def adapt_messages(docs: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Liste de docs Convex `messages` -> liste {content, is_from_client, id}."""
    result: List[Dict[str, Any]] = []
    for m in docs or []:
        result.append({
            "id": m.get("_id"),
            "content": m.get("content", ""),
            "is_from_client": bool(m.get("isFromClient")),
        })
    return result


def adapt_context(ctx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Résultat de `internal/chat:getContext` -> bundle snake_case pour le hot-path.

    Renvoie un dict avec :
      merchant, product, conversation : dicts adaptés (ou None)
      history                         : liste messages adaptés
      away (bool), stock_status (dict|None), memory_facts (str JSON|None)
    `merchant=None` signale un marchand introuvable (getContext renvoie alors
    seulement `{ merchant: null }`).
    """
    ctx = ctx or {}
    return {
        "merchant": adapt_merchant(ctx.get("merchant")),
        "product": adapt_product(ctx.get("product")),
        "conversation": adapt_conversation(ctx.get("conversation")),
        "history": adapt_messages(ctx.get("history")),
        "away": bool(ctx.get("away")),
        "stock_status": ctx.get("stockStatus"),
        "memory_facts": ctx.get("memoryFacts"),
    }
