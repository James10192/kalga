"""
Long-Term Memory (LTM)
======================
Extrait et persiste les faits sémantiques durables d'une conversation en DB.

Déclenché de façon asynchrone (non-bloquante) à la fin de chaque conversation
(statut pending_delivery, pending_pickup, ended, completed).

Utilise DeepSeek JSON mode pour extraire :
- facts      : liste de faits durables sur le client
- summary    : résumé court de la conversation
- preferences: préférences détectées (livraison, zone, budget…)
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

logger = logging.getLogger("kalga.memory.ltm")

# Prompt d'extraction — demande un JSON structuré
_EXTRACTION_SYSTEM_PROMPT = """Tu es un assistant qui analyse des conversations WhatsApp de vente.
Extrais les informations importantes sur le client en JSON.

Retourne UNIQUEMENT un JSON valide avec ce format exact:
{
  "facts": [
    {"fact": "description courte du fait", "confidence": 0.9}
  ],
  "summary": "résumé en 1-2 phrases de cette conversation",
  "preferences": {
    "delivery": "livraison|pickup|unknown",
    "zone": "quartier ou ville mentionné, ou null",
    "budget_max": "montant max mentionné, ou null",
    "notes": "autres préférences pertinentes, ou null"
  }
}

Pour facts, inclure uniquement les faits durables et utiles pour les prochaines conversations:
- Préférence livraison/pickup
- Zone géographique / quartier
- Budget habituel
- Taille, couleur ou modèle préféré
- Style de communication (formel/informel)
Ne pas inclure les prix de cette négociation spécifique."""


async def extract_and_save(
    repo,
    merchant_id: int,
    client_phone: str,
    history: List[Dict],
    product: Dict,
    outcome: str,
    deepseek_client
) -> None:
    """
    Extrait les faits de la conversation et les persiste dans client_history.
    Conçu pour être appelé via asyncio.create_task() — non-bloquant.

    Args:
        repo          : ClientHistoryRepository instance
        merchant_id   : ID du marchand
        client_phone  : Téléphone du client
        history       : Historique complet de la conversation
        product       : Données produit {name, price}
        outcome       : Résultat ('sale', 'ended', 'abandoned')
        deepseek_client: Instance DeepSeekClient
    """
    try:
        if not deepseek_client.api_key:
            return

        extracted = await _extract_from_conversation(history, product, outcome, deepseek_client)
        if not extracted:
            return

        await _persist(repo, merchant_id, client_phone, extracted, product, outcome)
        logger.info(f"LTM: faits extraits et sauvegardés pour {client_phone} ({len(extracted.get('facts', []))} faits)")

    except Exception as e:
        logger.warning(f"LTM extraction échouée pour {client_phone}: {e}")


async def _extract_from_conversation(
    history: List[Dict],
    product: Dict,
    outcome: str,
    deepseek_client
) -> Optional[Dict]:
    """Appelle DeepSeek JSON mode pour extraire les faits."""
    try:
        # Limiter l'historique à 30 messages pour l'extraction
        history_text = "\n".join([
            f"{'Client' if m['is_from_client'] else 'Vendeur'}: {m['content']}"
            for m in history[-30:]
        ])

        user_prompt = (
            f"Produit discuté: {product.get('name', 'inconnu')} "
            f"(prix: {product.get('price', 0):,.0f} F)\n"
            f"Résultat: {outcome}\n\n"
            f"Conversation:\n{history_text}\n\n"
            f"Retourne le JSON d'analyse."
        )

        response = await deepseek_client.chat_completion(
            system_prompt=_EXTRACTION_SYSTEM_PROMPT,
            user_message=user_prompt,
            temperature=0.1,
            max_tokens=400
        )

        if not response:
            return None

        # Parser le JSON — DeepSeek peut wrapper dans ```json ... ```
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

        return json.loads(cleaned)

    except json.JSONDecodeError as e:
        logger.warning(f"LTM: JSON invalide reçu de DeepSeek: {e}")
        return None
    except Exception as e:
        logger.warning(f"LTM: erreur extraction: {e}")
        return None


async def _persist(
    repo,
    merchant_id: int,
    client_phone: str,
    extracted: Dict,
    product: Dict,
    outcome: str
) -> None:
    """Fusionne les nouveaux faits avec l'existant et sauvegarde."""
    new_facts = extracted.get("facts", [])
    summary = extracted.get("summary", "")
    preferences = extracted.get("preferences", {})

    # Ajouter la date à chaque fait
    today = datetime.now().strftime("%Y-%m-%d")
    for fact in new_facts:
        fact["date"] = today

    # Récupérer les faits existants
    existing_facts = await repo.get_memory_facts(merchant_id, client_phone) or []

    # Fusionner : remplacer les faits similaires, ajouter les nouveaux
    merged_facts = _merge_facts(existing_facts, new_facts)

    # Construire l'entrée de résumé de conversation
    conv_entry = {
        "date": today,
        "product": product.get("name", ""),
        "outcome": outcome,
        "summary": summary,
        "key_facts": [f["fact"] for f in new_facts[:3]]
    }

    # Sauvegarder
    await repo.save_memory_facts(merchant_id, client_phone, merged_facts)
    await repo.save_session_summary(merchant_id, client_phone, summary, conv_entry)

    if preferences:
        await repo.save_preferences(merchant_id, client_phone, preferences)


def _merge_facts(existing: List[Dict], new_facts: List[Dict]) -> List[Dict]:
    """
    Fusionne les faits existants et nouveaux.
    Si un fait similaire existe déjà (même début de phrase), on met à jour sa confidence.
    On garde max 20 faits au total, les plus récents et les plus confiants.
    """
    MAX_FACTS = 20

    # Index des faits existants par mot-clé (premiers mots)
    existing_by_key = {}
    for f in existing:
        key = _fact_key(f.get("fact", ""))
        existing_by_key[key] = f

    # Intégrer les nouveaux faits
    for nf in new_facts:
        key = _fact_key(nf.get("fact", ""))
        if key in existing_by_key:
            # Mettre à jour la confidence et la date
            existing_by_key[key]["confidence"] = max(
                existing_by_key[key].get("confidence", 0.5),
                nf.get("confidence", 0.5)
            )
            existing_by_key[key]["date"] = nf.get("date", "")
        else:
            existing_by_key[key] = nf

    # Trier par confidence desc, limiter à MAX_FACTS
    all_facts = sorted(
        existing_by_key.values(),
        key=lambda x: x.get("confidence", 0),
        reverse=True
    )
    return all_facts[:MAX_FACTS]


def _fact_key(fact_text: str) -> str:
    """Clé de déduplication : premiers 4 mots en minuscule."""
    words = fact_text.lower().split()
    return " ".join(words[:4])
