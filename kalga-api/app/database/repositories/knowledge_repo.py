"""
Repository pour la base de connaissances dynamique.

Stocke les couples (question client → réponse marchand) pour enrichir
les réponses IA avec le savoir accumulé du marchand.
"""
import re
from typing import Optional, List, Dict, Any
from .base import BaseRepository
from ..connection import get_connection


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


class KnowledgeBaseRepository(BaseRepository):
    """
    Gère la base de connaissances dynamique du marchand.

    Workflow:
    1. Marchand répond manuellement à un client → save_entry()
    2. Client pose une question → search() → injecter dans le prompt DeepSeek
    """

    def __init__(self):
        super().__init__("knowledge_base")

    async def save_entry(
        self,
        merchant_id: int,
        question: str,
        answer: str,
        source: str = "human_reply"
    ) -> int:
        """
        Enregistre une nouvelle entrée Q/R dans la base de connaissances.

        Returns: id de l'entrée créée
        """
        keywords = extract_keywords(question)

        async with get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO knowledge_base (merchant_id, question, answer, keywords, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (merchant_id, question, answer, keywords, source)
            )
            await db.commit()
            return cursor.lastrowid

    async def search(
        self,
        merchant_id: int,
        query: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Recherche les entrées KB les plus pertinentes pour une requête.

        Stratégie: scoring par mots-clés communs entre la requête et les entrées.
        Retourne les `limit` entrées avec le meilleur score.
        """
        if not query or not query.strip():
            return []

        query_keywords = set(extract_keywords(query).split(','))
        if not query_keywords or query_keywords == {''}:
            return []

        async with get_connection() as db:
            # Récupérer toutes les entrées du marchand (max 200 pour perf)
            cursor = await db.execute(
                """
                SELECT id, question, answer, keywords, usage_count
                FROM knowledge_base
                WHERE merchant_id = ?
                ORDER BY created_at DESC
                LIMIT 200
                """,
                (merchant_id,)
            )
            rows = await cursor.fetchall()

        if not rows:
            return []

        # Scorer par chevauchement de mots-clés
        scored = []
        for row in rows:
            entry_keywords = set(row['keywords'].split(',')) if row['keywords'] else set()
            common = query_keywords & entry_keywords
            if common:
                score = len(common) / max(len(query_keywords), 1)
                scored.append((score, dict(row)))

        # Trier par score décroissant
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [entry for _, entry in scored[:limit]]

        # Incrémenter le compteur d'utilisation pour les entrées retournées
        if results:
            ids = [r['id'] for r in results]
            async with get_connection() as db:
                for entry_id in ids:
                    await db.execute(
                        "UPDATE knowledge_base SET usage_count = usage_count + 1 WHERE id = ?",
                        (entry_id,)
                    )
                await db.commit()

        return results

    async def get_all(
        self,
        merchant_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Récupère toutes les entrées KB d'un marchand (pour le Dashboard)"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT id, question, answer, keywords, source, usage_count, created_at
                FROM knowledge_base
                WHERE merchant_id = ?
                ORDER BY usage_count DESC, created_at DESC
                LIMIT ? OFFSET ?
                """,
                (merchant_id, limit, offset)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def delete_entry(self, entry_id: int, merchant_id: int) -> bool:
        """Supprime une entrée KB (vérification merchant_id pour sécurité)"""
        async with get_connection() as db:
            cursor = await db.execute(
                "DELETE FROM knowledge_base WHERE id = ? AND merchant_id = ?",
                (entry_id, merchant_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def seed_defaults(self, merchant_id: int) -> int:
        """
        Insère les FAQ par défaut si la KB du marchand est vide.
        Idempotent : retourne 0 si la KB est déjà alimentée.

        Appelé à l'onboarding pour démarrer avec une KB non vide.
        Returns: nombre d'entrées créées.
        """
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT COUNT(*) as cnt FROM knowledge_base WHERE merchant_id = ?",
                (merchant_id,)
            )
            row = await cursor.fetchone()
            if row['cnt'] > 0:
                return 0  # KB déjà alimentée, ne pas écraser

        count = 0
        for question, answer in DEFAULT_FAQ_ENTRIES:
            await self.save_entry(
                merchant_id=merchant_id,
                question=question,
                answer=answer,
                source="default_faq"
            )
            count += 1
        return count

    async def get_insights(self, merchant_id: int) -> Dict[str, Any]:
        """
        Statistiques de la boucle d'apprentissage pour le Dashboard.

        Retourne:
        - Répartition des entrées KB par source (default_faq, auto_learned_deal, feedback_correction, etc.)
        - Top 5 entrées les plus utilisées
        - Questions auto-flaggées (sans réponse bot adéquate), groupées par fréquence
        """
        async with get_connection() as db:
            # Répartition par source
            cur = await db.execute(
                "SELECT source, COUNT(*) as cnt FROM knowledge_base WHERE merchant_id = ? GROUP BY source",
                (merchant_id,)
            )
            sources = {r['source']: r['cnt'] for r in await cur.fetchall()}

            # Top 5 entrées KB les plus utilisées (déclenchées dans des conversations réelles)
            cur = await db.execute(
                """SELECT question, answer, usage_count, source
                   FROM knowledge_base WHERE merchant_id = ?
                   ORDER BY usage_count DESC LIMIT 5""",
                (merchant_id,)
            )
            top_entries = [dict(r) for r in await cur.fetchall()]

            # Questions auto-flaggées groupées par message (top 10 récurrentes)
            cur = await db.execute(
                """SELECT client_message, COUNT(*) as occurrence
                   FROM conversation_feedback
                   WHERE merchant_id = ? AND feedback_type = 'auto_flagged'
                   GROUP BY client_message ORDER BY occurrence DESC LIMIT 10""",
                (merchant_id,)
            )
            gaps = [dict(r) for r in await cur.fetchall()]

        total = sum(sources.values())
        return {
            "total_kb_entries": total,
            "sources_breakdown": sources,
            "auto_learned_deals": sources.get("auto_learned_deal", 0),
            "feedback_corrections": sources.get("feedback_correction", 0),
            "default_faq": sources.get("default_faq", 0),
            "top_entries": top_entries,
            "question_gaps": gaps,
            "gap_count": len(gaps),
        }
