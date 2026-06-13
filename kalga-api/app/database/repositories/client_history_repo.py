"""
Repository pour l'historique des clients.

Phase E2 : délègue à Convex (`internal/clienthistory:*` pour les lectures et
l'upsert générique, `internal/memory:upsertMemory` pour les champs mémoire
LTM/épisodique). Signatures publiques inchangées. La logique de scoring de
négociation (`get_negotiation_context`, `_determine_negotiation_style`) reste
pure côté Python.
"""
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.infrastructure.convex_client import get_convex
from app.infrastructure.convex_repo_adapters import (
    adapt_client_history,
    history_patch_to_camel,
)


class ClientHistoryRepository:
    """Gère l'historique des interactions avec les clients (backend Convex)."""

    async def get_client_history(
        self,
        merchant_id: int,
        client_phone: str
    ) -> Optional[Dict[str, Any]]:
        """Récupère l'historique d'un client pour un marchand."""
        doc = await get_convex().query("internal/clienthistory:get", {
            "merchantId": merchant_id,
            "clientPhone": client_phone,
        })
        return adapt_client_history(doc)

    async def create_or_update(
        self,
        merchant_id: int,
        client_phone: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Crée ou met à jour l'historique d'un client."""
        patch = history_patch_to_camel(kwargs)
        doc = await get_convex().mutation("internal/clienthistory:createOrUpdate", {
            "merchantId": merchant_id,
            "clientPhone": client_phone,
            "patch": patch,
        })
        return adapt_client_history(doc)

    async def record_conversation(
        self,
        merchant_id: int,
        client_phone: str
    ) -> Dict[str, Any]:
        """Enregistre une nouvelle conversation pour un client."""
        history = await self.get_client_history(merchant_id, client_phone)
        if history:
            new_total = history['total_conversations'] + 1
            return await self.create_or_update(
                merchant_id,
                client_phone,
                total_conversations=new_total,
                last_interaction_date=datetime.now().isoformat()
            )
        return await self.create_or_update(
            merchant_id,
            client_phone,
            total_conversations=1
        )

    async def record_purchase(
        self,
        merchant_id: int,
        client_phone: str,
        amount: float,
        original_price: float,
        final_price: float,
        category: str = None
    ) -> Dict[str, Any]:
        """Enregistre un achat et met à jour les statistiques de négociation."""
        history = await self.get_client_history(merchant_id, client_phone)

        discount_percent = 0
        if original_price > 0 and final_price < original_price:
            discount_percent = ((original_price - final_price) / original_price) * 100

        if history:
            new_purchases = history['total_purchases'] + 1
            new_spent = history['total_spent'] + amount
            old_avg = history['avg_negotiation_discount'] or 0
            new_avg = ((old_avg * history['total_purchases']) + discount_percent) / new_purchases
            negotiation_style = self._determine_negotiation_style(new_avg, new_purchases)

            preferred_categories = history['preferred_categories'] or []
            if category and category not in preferred_categories:
                preferred_categories.append(category)

            return await self.create_or_update(
                merchant_id,
                client_phone,
                total_purchases=new_purchases,
                total_spent=new_spent,
                avg_negotiation_discount=new_avg,
                negotiation_style=negotiation_style,
                last_purchase_date=datetime.now().isoformat(),
                last_interaction_date=datetime.now().isoformat(),
                preferred_categories=json.dumps(preferred_categories) if preferred_categories else None
            )
        else:
            negotiation_style = self._determine_negotiation_style(discount_percent, 1)
            preferred_categories = [category] if category else []
            return await self.create_or_update(
                merchant_id,
                client_phone,
                total_conversations=1,
                total_purchases=1,
                total_spent=amount,
                avg_negotiation_discount=discount_percent,
                negotiation_style=negotiation_style,
                last_purchase_date=datetime.now().isoformat(),
                preferred_categories=json.dumps(preferred_categories) if preferred_categories else None
            )

    def _determine_negotiation_style(self, avg_discount: float, purchase_count: int) -> str:
        """Détermine le style de négociation d'un client basé sur son historique."""
        if purchase_count >= 5 and avg_discount < 5:
            return 'loyal'
        elif purchase_count >= 3 and avg_discount < 3:
            return 'premium'
        elif avg_discount > 15:
            return 'hard_negotiator'
        elif avg_discount > 8:
            return 'negotiator'
        else:
            return 'normal'

    async def get_negotiation_context(
        self,
        merchant_id: int,
        client_phone: str,
        product_price: float,
        min_price: float
    ) -> Dict[str, Any]:
        """Retourne le contexte de négociation pour adapter les contre-offres."""
        history = await self.get_client_history(merchant_id, client_phone)

        price_range = product_price - min_price
        max_discount_percent = (price_range / product_price) * 100 if product_price > 0 else 0

        if not history:
            return {
                'is_returning': False,
                'client_style': 'unknown',
                'purchase_count': 0,
                'suggested_discount': min(5, max_discount_percent / 3),
                'loyalty_discount': 0,
                'avg_discount': 0,
                'total_spent': 0,
                'recommendation': "Nouveau client - approche standard"
            }

        style = history['negotiation_style']
        purchases = history['total_purchases']
        avg_discount = history['avg_negotiation_discount'] or 0

        if style == 'loyal':
            suggested = min(avg_discount + 3, max_discount_percent * 0.7)
            loyalty_discount = 5 if purchases >= 5 else 3
            recommendation = f"Client fidèle ({purchases} achats) - Offrir un bon prix rapidement"
        elif style == 'premium':
            suggested = min(3, max_discount_percent * 0.3)
            loyalty_discount = 2
            recommendation = "Client premium - Pas besoin de négocier beaucoup"
        elif style == 'hard_negotiator':
            suggested = min(avg_discount * 0.8, max_discount_percent * 0.5)
            loyalty_discount = 0
            recommendation = f"Négociateur ({avg_discount:.0f}% moyen) - Rester ferme, paliers progressifs"
        elif style == 'negotiator':
            suggested = min(avg_discount, max_discount_percent * 0.6)
            loyalty_discount = 2 if purchases >= 3 else 0
            recommendation = "Négociateur - Proposer des paliers raisonnables"
        else:
            suggested = min(avg_discount, max_discount_percent * 0.5)
            loyalty_discount = 1 if purchases >= 2 else 0
            recommendation = "Client standard - Négociation normale"

        return {
            'is_returning': True,
            'client_style': style,
            'purchase_count': purchases,
            'suggested_discount': suggested,
            'loyalty_discount': loyalty_discount,
            'avg_discount': avg_discount,
            'total_spent': history['total_spent'],
            'last_purchase': history.get('last_purchase_date'),
            'recommendation': recommendation
        }

    async def get_top_clients(
        self,
        merchant_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Récupère les meilleurs clients d'un marchand."""
        docs = await get_convex().query("internal/clienthistory:getTopClients", {
            "merchantId": merchant_id,
            "limit": limit,
        })
        return [adapt_client_history(d) for d in (docs or [])]

    # =========================================================================
    # Méthodes LTM — mémoire sémantique (faits, résumés, préférences)
    # =========================================================================

    async def get_memory_facts(
        self,
        merchant_id: int,
        client_phone: str
    ) -> List[Dict[str, Any]]:
        """Récupère les faits mémorisés pour un client."""
        history = await self.get_client_history(merchant_id, client_phone)
        if not history or not history.get('memory_facts'):
            return []
        try:
            return json.loads(history['memory_facts'])
        except (json.JSONDecodeError, TypeError):
            return []

    async def save_memory_facts(
        self,
        merchant_id: int,
        client_phone: str,
        facts: List[Dict[str, Any]]
    ) -> None:
        """Sauvegarde la liste de faits mémorisés pour un client."""
        await get_convex().mutation("internal/memory:upsertMemory", {
            "merchantId": merchant_id,
            "clientPhone": client_phone,
            "memoryFacts": json.dumps(facts, ensure_ascii=False),
        })

    async def save_session_summary(
        self,
        merchant_id: int,
        client_phone: str,
        summary: str,
        conv_entry: Dict[str, Any]
    ) -> None:
        """Sauvegarde le résumé de la dernière session + historique (max 10)."""
        history = await self.get_client_history(merchant_id, client_phone)
        summaries = []
        if history and history.get('conversation_summaries'):
            try:
                summaries = json.loads(history['conversation_summaries'])
            except (json.JSONDecodeError, TypeError):
                summaries = []

        summaries.insert(0, conv_entry)
        summaries = summaries[:10]

        await get_convex().mutation("internal/memory:upsertMemory", {
            "merchantId": merchant_id,
            "clientPhone": client_phone,
            "lastSessionSummary": summary,
            "conversationSummaries": json.dumps(summaries, ensure_ascii=False),
        })

    async def get_conversation_summaries(
        self,
        merchant_id: int,
        client_phone: str
    ) -> List[Dict[str, Any]]:
        """Récupère l'historique des résumés de conversations."""
        history = await self.get_client_history(merchant_id, client_phone)
        if not history or not history.get('conversation_summaries'):
            return []
        try:
            return json.loads(history['conversation_summaries'])
        except (json.JSONDecodeError, TypeError):
            return []

    async def save_preferences(
        self,
        merchant_id: int,
        client_phone: str,
        preferences: Dict[str, Any]
    ) -> None:
        """Fusionne et sauvegarde les préférences détectées d'un client."""
        history = await self.get_client_history(merchant_id, client_phone)
        existing_prefs = {}
        if history and history.get('preferences'):
            try:
                existing_prefs = json.loads(history['preferences'])
            except (json.JSONDecodeError, TypeError):
                existing_prefs = {}

        for key, value in preferences.items():
            if value and value not in ('null', 'unknown', None):
                existing_prefs[key] = value

        await get_convex().mutation("internal/memory:upsertMemory", {
            "merchantId": merchant_id,
            "clientPhone": client_phone,
            "preferences": json.dumps(existing_prefs, ensure_ascii=False),
        })

    async def get_preferences(
        self,
        merchant_id: int,
        client_phone: str
    ) -> Dict[str, Any]:
        """Récupère les préférences mémorisées d'un client."""
        history = await self.get_client_history(merchant_id, client_phone)
        if not history or not history.get('preferences'):
            return {}
        try:
            return json.loads(history['preferences'])
        except (json.JSONDecodeError, TypeError):
            return {}


# Instance globale
_client_history_repo: Optional[ClientHistoryRepository] = None


def get_client_history_repository() -> ClientHistoryRepository:
    """Retourne l'instance globale du repository"""
    global _client_history_repo
    if _client_history_repo is None:
        _client_history_repo = ClientHistoryRepository()
    return _client_history_repo
