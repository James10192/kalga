"""
Étage ② (secours) — Classifieur LLM pour les messages ambigus (spec §9).

Appelé UNIQUEMENT quand les règles retournent UNCLEAR (P4). Le LLM ne peut
émettre que des types du catalogue — tout le reste est jeté. Échec, vide ou
inconnu → [UNCLEAR] : le bot demandera une clarification, jamais une action
inventée.
"""
import logging
from typing import Any, Dict, List, Optional

from .intents import Intent, IntentType
from .llm_protocol import LLMClient

logger = logging.getLogger("kalga.dialogue.classifier")

_VALID_TYPES = {t.value: t for t in IntentType}


async def classify_with_llm(message: str, llm: Optional[LLMClient],
                            context: Dict[str, Any]) -> List[Intent]:
    if llm is None:
        return [Intent(IntentType.UNCLEAR)]
    try:
        raw = await llm.classify(message, context)
    except Exception as e:  # un classifieur ne doit JAMAIS casser le flux
        logger.warning(f"Classifieur LLM en erreur: {e}")
        raw = None

    intents: List[Intent] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        intent_type = _VALID_TYPES.get(item.get("type"))
        if intent_type is None or intent_type == IntentType.UNCLEAR:
            continue
        amount = item.get("amount")
        intents.append(Intent(
            intent_type,
            amount=float(amount) if amount is not None else None,
            text=item.get("text"),
        ))

    return intents or [Intent(IntentType.UNCLEAR)]
