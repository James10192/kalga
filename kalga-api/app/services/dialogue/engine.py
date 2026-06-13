"""
Façade d'intégration du moteur v2 (spec §12, P4).

Traduit le DialogueResult (plan d'actions) vers les champs que le chemin
chat_service sait déjà exécuter (images_to_send, send_location, statut DB…).
DÉFENSIVE PAR CONTRAT : toute erreur ou message non-géré → None, et le
chemin v1 reprend la main. Activer v2 ne peut donc rien casser.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .actions import ActionType
from .deepseek_adapter import DeepSeekAdapter
from .llm_protocol import LLMClient
from .orchestrator import run_pipeline

logger = logging.getLogger("kalga.dialogue.engine")

_UNSET = object()


@dataclass
class EngineResponse:
    message: str
    new_status: str
    new_offer: Optional[float]
    send_location: bool = False
    images_to_send: Optional[List[dict]] = None
    human_takeover: bool = False
    notify_reason: Optional[str] = None
    delivery_address: Optional[str] = None
    facts: List[str] = field(default_factory=list)


def _default_llm() -> Optional[LLMClient]:
    # Imports paresseux : éviter de charger le paquet ai/ au chargement du module
    from ...core.config import settings
    if not settings.deepseek_api_key:
        return None
    from ..ai.deepseek_client import get_deepseek_client
    return DeepSeekAdapter(get_deepseek_client())


def _format_history_block(history: List[Dict], window: int = 8) -> Optional[str]:
    recent = (history or [])[-window:]
    if not recent:
        return None
    lines = []
    for m in recent:
        who = "Client" if m.get("is_from_client") else "Vendeur"
        lines.append(f"{who}: {m.get('content', '')[:120]}")
    return "\n".join(lines)


async def _resolve_images(plan, conversation, product, catalog: Optional[List[Dict]]) -> Optional[List[dict]]:
    """
    Résout les images d'un plan.

    HOT-PATH (production) : `catalog` est fourni par chat_service (liste Convex
    `listProductsForTools`, snake_case, ids strings) → AUCUN accès SQLite.
    REPLI (tests unitaires) : `catalog is None` → lecture via ProductRepository
    (SQLite seedée par le test). Le hot-path passe toujours une liste (même vide),
    donc il ne touche jamais SQLite.
    """
    if catalog is None:
        return await _resolve_images_via_repo(plan, conversation, product)

    by_id = {p["id"]: p for p in catalog if p.get("id")}
    images: List[dict] = []
    for action in plan.actions:
        if action.type == ActionType.SEND_PHOTO:
            target = None
            sel = conversation.get("selected_variant_id")
            if sel:
                target = by_id.get(sel)
            if target and target.get("image_path"):
                images.append({"image_path": target["image_path"],
                               "caption": f"Modèle {target.get('variant_name') or target['name']}"})
            elif product.get("image_path"):
                images.append({"image_path": product["image_path"],
                               "caption": product["name"]})
        elif action.type == ActionType.SEND_VARIANTS and product.get("group_id"):
            seen_labels = set()
            for v in catalog:
                if v.get("group_id") != product.get("group_id"):
                    continue
                if v.get("id") == product.get("id"):
                    continue  # "autres" variantes uniquement
                label = (v.get("variant_name") or v["name"]).strip().lower()
                if v.get("image_path") and label not in seen_labels:
                    seen_labels.add(label)
                    images.append({"image_path": v["image_path"],
                                   "caption": f"Modèle {v.get('variant_name') or v['name']}"})
    return images or None


async def _resolve_images_via_repo(plan, conversation, product) -> Optional[List[dict]]:
    """Repli SQLite (tests uniquement) — chemin historique pré-migration."""
    from ...database.repositories.product_repo import ProductRepository
    repo = ProductRepository()
    images: List[dict] = []
    for action in plan.actions:
        if action.type == ActionType.SEND_PHOTO:
            target = None
            if conversation.get("selected_variant_id"):
                target = await repo.get_by_id(conversation["selected_variant_id"])
            if target and target.get("image_path"):
                images.append({"image_path": target["image_path"],
                               "caption": f"Modèle {target.get('variant_name') or target['name']}"})
            elif product.get("image_path"):
                images.append({"image_path": product["image_path"],
                               "caption": product["name"]})
        elif action.type == ActionType.SEND_VARIANTS and product.get("group_id"):
            variants = await repo.get_other_variants(product["id"], product["group_id"])
            seen_labels = set()
            for v in variants:
                label = (v.get("variant_name") or v["name"]).strip().lower()
                if v.get("image_path") and label not in seen_labels:
                    seen_labels.add(label)
                    images.append({"image_path": v["image_path"],
                                   "caption": f"Modèle {v.get('variant_name') or v['name']}"})
    return images or None


async def respond(
    client_message: str,
    conversation: Dict,
    product: Dict,
    merchant: Dict,
    history: List[Dict],
    llm=_UNSET,
    floor_override: Optional[float] = None,
    memory_extra: Optional[str] = None,
    catalog: Optional[List[Dict]] = None,
) -> Optional[EngineResponse]:
    try:
        llm_client = _default_llm() if llm is _UNSET else llm

        persona = None
        if any(merchant.get(k) for k in ("bot_tone", "bot_style", "bot_catchphrase")):
            persona = {k: merchant.get(k) for k in ("bot_tone", "bot_style", "bot_catchphrase")}

        history_block = _format_history_block(history)
        memory_block = f"{memory_extra}\n{history_block}" if memory_extra and history_block \
            else (memory_extra or history_block)

        result = await run_pipeline(
            client_message=client_message,
            db_status=conversation.get("status", "active"),
            history=history or [],
            product=product,
            current_offer=conversation.get("current_offer"),
            llm=llm_client,
            persona=persona,
            memory_block=memory_block,
            floor_override=floor_override,
        )
        if result is None:
            return None

        plan = result.plan
        types = {a.type for a in plan.actions}
        message = result.text

        # Infos de paiement : ajoutées au texte (donnée marchand, pas LLM)
        if ActionType.SEND_PAYMENT_INFO in types:
            payment = merchant.get("payment_info") or merchant.get("payment_methods")
            if payment:
                message = f"{message}\n{payment}"

        # Catalogue réel : la liste vient de la BASE (jamais inventée par le LLM).
        # « moins_cher » → uniquement les produits sous le prix actuel, triés.
        catalog_action = next((a for a in plan.actions
                               if a.type == ActionType.SEND_TEXT
                               and "catalogue" in a.facts), None)
        if catalog_action is not None and product.get("id") is not None:
            # HOT-PATH : catalogue Convex fourni. REPLI tests : lecture SQLite.
            if catalog is None:
                from ...database.repositories.product_repo import ProductRepository
                source = await ProductRepository().get_by_merchant(merchant["id"])
            else:
                source = catalog
            others = [p for p in source if p.get("id") != product["id"]]
            cheaper_only = "moins_cher" in catalog_action.facts
            if cheaper_only:
                others = [p for p in others if p["price"] < product["price"]]
            others.sort(key=lambda p: p["price"])
            if others:
                lines = [
                    f"• {p['name']} — {int(p['price']):,} F ({p['code']})".replace(",", " ")
                    for p in others[:4]
                ]
                message = f"{message}\n" + "\n".join(lines)
            elif cheaper_only:
                message = (f"{message}\nPour l'instant, le {product['name']} est notre "
                           f"meilleure offre dans cette gamme 😉")

        notify = next((a.reason for a in plan.actions
                       if a.type == ActionType.NOTIFY_MERCHANT), None)
        address = next((a.reason for a in plan.actions
                        if a.type == ActionType.SEND_TEXT
                        and "address_confirmed" in a.facts), None)

        return EngineResponse(
            message=message,
            new_status=result.db_status,
            new_offer=result.new_offer,
            send_location=ActionType.SEND_LOCATION in types,
            images_to_send=await _resolve_images(plan, conversation, product, catalog),
            human_takeover=ActionType.HANDOVER_HUMAN in types,
            notify_reason=notify,
            delivery_address=address,
            facts=[f for a in plan.actions for f in a.facts],
        )
    except Exception as e:
        logger.error(f"Moteur v2 indisponible — repli v1: {e}")
        return None
