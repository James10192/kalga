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

from ...database.repositories.product_repo import ProductRepository
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


async def _resolve_images(plan, conversation, product) -> Optional[List[dict]]:
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
) -> Optional[EngineResponse]:
    try:
        llm_client = _default_llm() if llm is _UNSET else llm

        persona = None
        if any(merchant.get(k) for k in ("bot_tone", "bot_style", "bot_catchphrase")):
            persona = {k: merchant.get(k) for k in ("bot_tone", "bot_style", "bot_catchphrase")}

        result = await run_pipeline(
            client_message=client_message,
            db_status=conversation.get("status", "active"),
            history=history or [],
            product=product,
            current_offer=conversation.get("current_offer"),
            llm=llm_client,
            persona=persona,
            memory_block=_format_history_block(history),
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

        notify = next((a.reason for a in plan.actions
                       if a.type == ActionType.NOTIFY_MERCHANT), None)

        return EngineResponse(
            message=message,
            new_status=result.db_status,
            new_offer=result.new_offer,
            send_location=ActionType.SEND_LOCATION in types,
            images_to_send=await _resolve_images(plan, conversation, product),
            human_takeover=ActionType.HANDOVER_HUMAN in types,
            notify_reason=notify,
            facts=[f for a in plan.actions for f in a.facts],
        )
    except Exception as e:
        logger.error(f"Moteur v2 indisponible — repli v1: {e}")
        return None
