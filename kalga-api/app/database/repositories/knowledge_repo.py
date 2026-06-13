"""
Repository pour la base de connaissances dynamique.

Stocke les couples (question client → réponse marchand) pour enrichir
les réponses IA avec le savoir accumulé du marchand.
"""
import re
from typing import Optional, List, Dict, Any

from app.infrastructure.convex_client import get_convex


# Mots vides français (exclus de l'indexation)
_STOP_WORDS = {
    'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une',
    'est', 'et', 'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
    'que', 'qui', 'en', 'à', 'au', 'aux', 'pour', 'avec', 'sur', 'par',
    'dans', 'ce', 'se', 'on', 'ne', 'pas', 'plus', 'bien', 'mais',
    'mon', 'ton', 'son', 'notre', 'votre', 'leur', 'ma', 'ta', 'sa',
    'ça', 'ca', 'ya', 'oui', 'non', 'ok', 'svp', 'stp',
}


def extract_keywords(text: str, max_keywords: int = 8) -> str:
    """
    Extrait les mots-clés significatifs d'un texte.
    Sans appel IA — simple filtre sur les mots longs et non-vides.

    Returns: chaîne de mots-clés séparés par des virgules
    """
    # Nettoyer: minuscules, supprimer ponctuation sauf apostrophes
    text = text.lower()
    text = re.sub(r"[^\w\s']", ' ', text)

    words = text.split()
    keywords = []
    seen = set()

    for word in words:
        # Supprimer apostrophes résiduelles
        word = word.strip("'")
        if (
            len(word) >= 4 and
            word not in _STOP_WORDS and
            word not in seen and
            word.isalpha()
        ):
            keywords.append(word)
            seen.add(word)
            if len(keywords) >= max_keywords:
                break

    return ','.join(keywords)


# FAQ par défaut pour l'onboarding des nouveaux marchands
# Couvre les questions les plus fréquentes dans le commerce WhatsApp africain
DEFAULT_FAQ_ENTRIES = [
    ("vous livrez ?",
     "Oui, on livre ! Donne-nous ton adresse et on s'organise."),
    ("vous livrez a abidjan ?",
     "Oui, on livre à Abidjan ! Dis-nous ton quartier et on te donne les détails."),
    ("mobile money ?",
     "Oui, on accepte Orange Money et MTN Mobile Money."),
    ("vous acceptez wave ?",
     "Oui, Wave accepté !"),
    ("c est original ?",
     "Oui, 100% original, qualité garantie."),
    ("c est garanti ?",
     "Oui, qualité garantie. En cas de problème, on s'arrange toujours."),
    ("vous avez d autres couleurs ?",
     "Dis-moi quelle couleur tu cherches et je vérifie le stock pour toi."),
    ("vous faites des reductions ?",
     "On s'arrange toujours pour nos clients ! Fais-moi une offre et on voit."),
    ("combien pour deux ?",
     "Pour 2 articles, je te fais un prix spécial ! Intéressé ?"),
    ("vous ouvrez a quelle heure ?",
     "Pour les horaires, contacte directement le vendeur !"),
]


class KnowledgeBaseRepository:
    """
    Gère la base de connaissances dynamique du marchand (backend Convex).

    Workflow:
    1. Marchand répond manuellement à un client → save_entry()
    2. Client pose une question → search() → injecter dans le prompt DeepSeek

    Phase E2 : délègue à Convex (`internal/memory:saveKnowledgeEntry` pour
    l'écriture, `internal/knowledge:*` pour lecture/admin). `search` scoré ici.
    """

    async def save_entry(
        self,
        merchant_id: int,
        question: str,
        answer: str,
        source: str = "human_reply"
    ) -> int:
        """Enregistre une nouvelle entrée Q/R. Returns: id de l'entrée créée."""
        result = await get_convex().mutation("internal/memory:saveKnowledgeEntry", {
            "merchantId": merchant_id,
            "question": question,
            "answer": answer,
            "source": source,
        })
        return result.get("knowledgeBaseId") if result else None

    async def search(
        self,
        merchant_id: int,
        query: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Recherche les entrées KB les plus pertinentes pour une requête.
        Scoring par mots-clés communs (côté Python), incrément usage côté Convex.
        """
        if not query or not query.strip():
            return []

        query_keywords = set(extract_keywords(query).split(','))
        if not query_keywords or query_keywords == {''}:
            return []

        rows = await get_convex().query("internal/knowledge:listForSearch", {
            "merchantId": merchant_id,
            "limit": 200,
        })
        if not rows:
            return []

        scored = []
        for row in rows:
            entry_keywords = set(row['keywords'].split(',')) if row.get('keywords') else set()
            common = query_keywords & entry_keywords
            if common:
                score = len(common) / max(len(query_keywords), 1)
                scored.append((score, {
                    "id": row["id"],
                    "question": row["question"],
                    "answer": row["answer"],
                    "keywords": row.get("keywords"),
                    "usage_count": row.get("usage_count", 0),
                }))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [entry for _, entry in scored[:limit]]

        if results:
            await get_convex().mutation("internal/knowledge:bumpUsage", {
                "entryIds": [r["id"] for r in results],
            })

        return results

    async def get_all(
        self,
        merchant_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Récupère toutes les entrées KB d'un marchand (pour le Dashboard)."""
        rows = await get_convex().query("internal/knowledge:getAll", {
            "merchantId": merchant_id,
            "limit": limit,
            "offset": offset,
        })
        # created_at -> ISO (parité shape Dashboard).
        from app.infrastructure.convex_repo_adapters import ms_to_iso
        out = []
        for r in (rows or []):
            r = dict(r)
            if isinstance(r.get("created_at"), (int, float)):
                r["created_at"] = ms_to_iso(r["created_at"])
            out.append(r)
        return out

    async def delete_entry(self, entry_id: int, merchant_id: int) -> bool:
        """Supprime une entrée KB (vérification merchant_id pour sécurité)."""
        result = await get_convex().mutation("internal/knowledge:deleteEntry", {
            "entryId": entry_id,
            "merchantId": merchant_id,
        })
        return bool(result and result.get("deleted"))

    async def seed_defaults(self, merchant_id: int) -> int:
        """
        Insère les FAQ par défaut si la KB du marchand est vide (idempotent).
        Returns: nombre d'entrées créées.
        """
        entries = [
            {
                "question": q,
                "answer": a,
                "keywords": extract_keywords(q),
            }
            for q, a in DEFAULT_FAQ_ENTRIES
        ]
        result = await get_convex().mutation("internal/knowledge:seedDefaults", {
            "merchantId": merchant_id,
            "entries": entries,
        })
        return result.get("created", 0) if result else 0

    async def get_insights(self, merchant_id: int) -> Dict[str, Any]:
        """Statistiques de la boucle d'apprentissage pour le Dashboard."""
        return await get_convex().query("internal/knowledge:getInsights", {
            "merchantId": merchant_id,
        })
