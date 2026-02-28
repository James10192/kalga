"""
Short-Term Memory (STM)
=======================
Gère la compression du contexte intra-session.

Stratégie : rolling window avec résumé automatique via DeepSeek.
- Si history <= THRESHOLD messages  → retourne les 8 derniers verbatim, sans appel LLM
- Si history  > THRESHOLD messages  → résume les anciens via DeepSeek (max 150 tokens),
                                       retourne (summary, 8 derniers verbatim)

L'appelant passe le résultat à build_negotiation_prompt() via context_summary.
"""
import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger("kalga.memory.stm")

# Seuil à partir duquel on compresse (en nombre de messages total)
COMPRESSION_THRESHOLD = 12
# Nombre de messages récents conservés verbatim
RECENT_WINDOW = 8


async def build_context(
    history: List[Dict],
    deepseek_client=None
) -> Tuple[Optional[str], List[Dict]]:
    """
    Construit le contexte à envoyer au LLM depuis l'historique complet.

    Args:
        history       : Liste complète des messages {content, is_from_client}
        deepseek_client: Instance DeepSeekClient (optionnel — si None, pas de compression)

    Returns:
        (summary_text, recent_messages)
        - summary_text   : Résumé des anciens messages, ou None si pas de compression
        - recent_messages: Les RECENT_WINDOW derniers messages verbatim
    """
    recent = history[-RECENT_WINDOW:] if len(history) >= RECENT_WINDOW else history

    # Pas besoin de compresser
    if len(history) <= COMPRESSION_THRESHOLD or deepseek_client is None:
        return None, recent

    # Messages "anciens" à compresser (tout sauf les RECENT_WINDOW derniers)
    old_messages = history[:-RECENT_WINDOW]

    summary = await _summarize(old_messages, deepseek_client)
    return summary, recent


async def _summarize(messages: List[Dict], deepseek_client) -> Optional[str]:
    """
    Appelle DeepSeek pour résumer une liste de messages en max 150 tokens.
    Retourne None si l'appel échoue — l'appelant se rabattra sur les messages bruts.
    """
    try:
        history_text = "\n".join([
            f"{'Client' if m['is_from_client'] else 'Vendeur'}: {m['content']}"
            for m in messages
        ])

        system_prompt = (
            "Tu es un assistant qui résume des conversations WhatsApp de vente. "
            "Résume les points clés de cette conversation en 3-5 phrases courtes maximum. "
            "Inclus: prix discutés, préférences du client, accord ou désaccord en cours. "
            "Sois factuel et concis. Ne dépasse pas 150 mots."
        )

        user_prompt = f"Résume cette conversation:\n\n{history_text}"

        summary = await deepseek_client.chat_completion(
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.3,
            max_tokens=200,
            system_prompt=system_prompt
        )

        if summary:
            logger.info(f"STM: contexte compressé ({len(messages)} msgs → résumé)")
            return summary.strip()

        return None

    except Exception as e:
        logger.warning(f"STM compression échouée: {e}")
        return None


def format_for_prompt(summary: Optional[str], recent: List[Dict]) -> str:
    """
    Formate le contexte compressé (summary + recent) en texte pour le prompt.

    Args:
        summary: Résumé des anciens messages (peut être None)
        recent : Messages récents verbatim

    Returns:
        Texte formaté prêt à injecter dans le prompt DeepSeek
    """
    parts = []

    if summary:
        parts.append(f"[RÉSUMÉ DES ÉCHANGES PRÉCÉDENTS]\n{summary}\n")

    recent_text = "\n".join([
        f"{'Client' if m['is_from_client'] else 'Vendeur'}: {m['content']}"
        for m in recent
    ])

    if recent_text:
        label = "[DERNIERS MESSAGES]" if summary else ""
        parts.append(f"{label}\n{recent_text}" if label else recent_text)

    return "\n".join(parts)
