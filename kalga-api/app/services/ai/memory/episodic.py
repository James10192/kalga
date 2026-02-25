"""
Episodic Memory
===============
Récupère le contexte inter-sessions pour un client retournant.

Utilise les conversation_summaries et memory_facts stockés en LTM
pour construire un bloc de contexte injecté dans le prompt DeepSeek.

Score de pertinence :
    0.6 × recency_score + 0.4 × product_match_score
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

logger = logging.getLogger("kalga.memory.episodic")

# Nombre max de résumés de sessions à injecter
MAX_SESSIONS = 3
# Nombre max de faits à injecter
MAX_FACTS = 5


async def get_episodic_context(
    repo,
    merchant_id: int,
    client_phone: str,
    product_name: str
) -> Optional[str]:
    """
    Construit le contexte épisodique pour un client.

    Retourne None si le client est nouveau ou si l'historique est vide.
    Retourne un bloc texte formaté à injecter dans le prompt DeepSeek.
    """
    try:
        summaries = await repo.get_conversation_summaries(merchant_id, client_phone)
        facts = await repo.get_memory_facts(merchant_id, client_phone)
        preferences = await repo.get_preferences(merchant_id, client_phone)

        if not summaries and not facts:
            return None

        # Sélectionner les sessions les plus pertinentes
        relevant = _rank_summaries(summaries, product_name)[:MAX_SESSIONS]
        top_facts = facts[:MAX_FACTS]

        return _format_episodic_prompt(relevant, top_facts, preferences)

    except Exception as e:
        logger.warning(f"Episodic: erreur récupération contexte pour {client_phone}: {e}")
        return None


def _rank_summaries(
    summaries: List[Dict],
    product_name: str
) -> List[Dict]:
    """
    Trie les sessions par score de pertinence décroissant.

    Score = 0.6 × recency + 0.4 × product_match
    - recency: exponentiel décroissant (1.0 = aujourd'hui, ~0 après 30 jours)
    - product_match: 1.0 si même produit, 0.0 sinon
    """
    today = datetime.now()
    product_lower = product_name.lower()

    def score(s: Dict) -> float:
        # Recency
        try:
            date = datetime.strptime(s.get("date", ""), "%Y-%m-%d")
            days_ago = max((today - date).days, 0)
            recency = max(0.0, 1.0 - days_ago / 30.0)
        except ValueError:
            recency = 0.0

        # Product match
        session_product = s.get("product", "").lower()
        product_match = 1.0 if product_lower and product_lower in session_product else 0.0

        return 0.6 * recency + 0.4 * product_match

    return sorted(summaries, key=score, reverse=True)


def _format_episodic_prompt(
    sessions: List[Dict],
    facts: List[Dict],
    preferences: Dict[str, Any]
) -> str:
    """
    Formate le bloc de contexte épisodique pour le prompt DeepSeek.
    """
    lines = ["[MÉMOIRE CLIENT — SESSIONS PRÉCÉDENTES]"]

    # Sessions passées
    if sessions:
        lines.append("Conversations précédentes :")
        for s in sessions:
            date = s.get("date", "?")
            product = s.get("product", "")
            outcome = s.get("outcome", "")
            summary = s.get("summary", "")
            outcome_label = {"sale": "✅ Acheté", "ended": "❌ Pas acheté", "abandoned": "⏸ Abandonné"}.get(outcome, outcome)
            product_info = f" ({product})" if product else ""
            lines.append(f"• {date}{product_info} — {outcome_label} : {summary}")

    # Faits durables
    if facts:
        lines.append("Ce qu'on sait de ce client :")
        for f in facts:
            confidence = f.get("confidence", 0)
            if confidence >= 0.6:
                lines.append(f"• {f.get('fact', '')}")

    # Préférences
    if preferences:
        pref_items = []
        if preferences.get("delivery") and preferences["delivery"] not in ("unknown", "null"):
            pref_items.append(f"livraison: {preferences['delivery']}")
        if preferences.get("zone") and preferences["zone"] not in ("null", None):
            pref_items.append(f"zone: {preferences['zone']}")
        if preferences.get("budget_max") and preferences["budget_max"] not in ("null", None):
            pref_items.append(f"budget max: {preferences['budget_max']}")
        if pref_items:
            lines.append(f"Préférences : {', '.join(pref_items)}")

    lines.append("[FIN MÉMOIRE CLIENT]")
    return "\n".join(lines)
