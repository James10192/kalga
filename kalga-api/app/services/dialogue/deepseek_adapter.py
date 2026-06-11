"""
Adaptateur DeepSeek du contrat LLMClient (spec §9).

Deux prompts étroits :
- classify : catalogue d'intentions imposé, sortie JSON uniquement ;
- speak    : exécuter le brief (plan décidé + interdits), jamais décider.

Toute erreur (réseau, JSON, timeout) → None : le moteur continue
(règles seules / gabarits). Jamais d'exception vers l'appelant.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from .intents import IntentType

logger = logging.getLogger("kalga.dialogue.adapter")

_CLASSIFY_SYSTEM = (
    "Tu classifies le message d'un client WhatsApp d'une boutique en Côte d'Ivoire.\n"
    "Types possibles (UNIQUEMENT ceux-ci) :\n"
    + "\n".join(f"- {t.value}" for t in IntentType)
    + "\nRéponds UNIQUEMENT un tableau JSON : "
      '[{"type": "...", "amount": nombre éventuel, "text": "détail éventuel"}]. '
      "Plusieurs intentions possibles. Aucun autre texte."
)

_SPEAK_SYSTEM = (
    "Tu es le vendeur d'une boutique WhatsApp en Côte d'Ivoire. "
    "Le système a DÉJÀ décidé quoi faire — tu ne décides RIEN, tu rédiges. "
    "Écris UN court message WhatsApp naturel et chaleureux (tutoiement, "
    "1-3 phrases, émojis sobres) qui exprime exactement les actions du plan. "
    "Respecte ABSOLUMENT les interdits fournis. Réponds uniquement le message."
)


class DeepSeekAdapter:
    """Implémente LLMClient au-dessus du DeepSeekClient existant."""

    def __init__(self, ds_client):
        self._ds = ds_client

    async def classify(self, message: str, context: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        try:
            last_bot = context.get("last_bot_message") or "(aucun)"
            user = (f"Dernier message du bot : {last_bot}\n"
                    f"Message du client : {message}")
            raw = await self._ds.chat_completion(
                messages=[{"role": "user", "content": user}],
                temperature=0.1, max_tokens=200, system_prompt=_CLASSIFY_SYSTEM,
            )
            if not raw:
                return None
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(l for l in cleaned.splitlines()
                                    if not l.startswith("```")).strip()
            data = json.loads(cleaned)
            return data if isinstance(data, list) else None
        except Exception as e:
            logger.warning(f"classify indisponible: {e}")
            return None

    async def speak(self, brief: Dict[str, Any]) -> Optional[str]:
        try:
            persona = brief.get("persona") or {}
            persona_line = ""
            if persona.get("bot_catchphrase"):
                persona_line = f"Phrase signature à placer si naturel : {persona['bot_catchphrase']}\n"
            memory_line = f"Contexte client : {brief['memory']}\n" if brief.get("memory") else ""
            user = (
                f"Produit : {brief.get('product_name')} à {brief.get('listed_price')} F\n"
                f"Le client vient de dire : {brief.get('client_message')}\n"
                f"{memory_line}{persona_line}"
                f"PLAN À EXPRIMER (dans cet ordre) : {json.dumps(brief.get('actions', []), ensure_ascii=False)}\n"
                f"INTERDITS : {' ; '.join(brief.get('forbidden', []))}\n"
                f"Rédige le message."
            )
            raw = await self._ds.chat_completion(
                messages=[{"role": "user", "content": user}],
                temperature=0.7, max_tokens=300, system_prompt=_SPEAK_SYSTEM,
            )
            return raw.strip() if raw else None
        except Exception as e:
            logger.warning(f"speak indisponible: {e}")
            return None
