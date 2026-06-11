"""
Chef d'orchestre du pipeline (spec §4) — mince, zéro logique métier :
① assainir (dans extract_intents) → ② comprendre (+ classifieur LLM si UNCLEAR)
→ ③ décider → ④ parler → ⑤ filtrer (dans render).

Retourne None quand le message ne porte aucune intention client (messages
système purs) : l'appelant garde alors son chemin historique.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

from .actions import ActionPlan
from .intents import Intent, IntentType
from .llm_classifier import classify_with_llm
from .llm_protocol import LLMClient
from .policy import PolicyContext, decide_plan
from .sale_state import DB_STATUS, from_db_status
from .speech import SpeechContext, render
from .understanding import extract_intents, extract_price_amount


@dataclass
class DialogueResult:
    text: str
    plan: ActionPlan
    db_status: str
    new_offer: Optional[float]


def _last_bot_message(history: List[Dict]) -> Optional[str]:
    for msg in reversed(history or []):
        if not msg.get("is_from_client"):
            return msg.get("content")
    return None


async def run_pipeline(
    client_message: str,
    db_status: str,
    history: List[Dict],
    product: Dict,
    current_offer: Optional[float],
    llm: Optional[LLMClient],
    persona: Optional[dict] = None,
    memory_block: Optional[str] = None,
) -> Optional[DialogueResult]:
    last_bot = _last_bot_message(history)

    # ①② Comprendre (multi-intentions, métadonnées assainies)
    intents = extract_intents(client_message, last_bot_message=last_bot)
    if not intents:
        return None  # message 100 % système → chemin v1

    # ②bis Classifieur LLM pour l'ambigu
    if intents == [Intent(IntentType.UNCLEAR)]:
        intents = await classify_with_llm(client_message, llm,
                                          {"last_bot_message": last_bot})
        # Règle marchand : un message AMBIGU ne peut JAMAIS conclure une vente
        # NI clore la conversation (terrain : « Je t'en prie » classé au revoir
        # → conversation terminée → client muré). Le classifieur informe ;
        # il n'a aucun pouvoir transactionnel ni de clôture.
        intents = [i for i in intents
                   if i.type not in (IntentType.ACCEPT_PRICE, IntentType.GOODBYE)] \
            or [Intent(IntentType.UNCLEAR)]

    # ③ Décider
    ctx = PolicyContext(
        state=from_db_status(db_status, message_count=len(history)),
        listed_price=float(product["price"]),
        floor_price=float(product.get("effective_min_price") or product["min_price"]),
        current_offer=current_offer,
        has_variants=bool(product.get("group_id")),
        has_photo=bool(product.get("image_path")),
        last_bot_price=extract_price_amount(last_bot) if last_bot else None,
    )
    plan = decide_plan(intents, ctx)

    # ④⑤ Parler (filtré)
    sctx = SpeechContext(
        product_name=product["name"],
        listed_price=float(product["price"]),
        floor_price=ctx.floor_price,
        round_seed=len(history),
        persona=persona,
        memory_block=memory_block,
        client_message=client_message,
        product_description=product.get("description"),
    )
    text = await render(plan, sctx, llm)

    return DialogueResult(
        text=text,
        plan=plan,
        db_status=DB_STATUS[plan.new_state],
        new_offer=plan.new_offer,
    )
