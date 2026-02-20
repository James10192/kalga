"""
Repository pour l'historique des clients
Permet de mémoriser le comportement de négociation des clients
"""
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import BaseRepository
from ..connection import get_connection


class ClientHistoryRepository(BaseRepository):
    """Gère l'historique des interactions avec les clients"""

    def __init__(self):
        super().__init__("client_history")

    async def get_client_history(
        self,
        merchant_id: int,
        client_phone: str
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère l'historique d'un client pour un marchand.
        """
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM client_history
                WHERE merchant_id = ? AND client_phone = ?
                """,
                (merchant_id, client_phone)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            history = dict(row)
            # Parser les catégories préférées (JSON)
            if history.get('preferred_categories'):
                try:
                    history['preferred_categories'] = json.loads(history['preferred_categories'])
                except json.JSONDecodeError:
                    history['preferred_categories'] = []
            else:
                history['preferred_categories'] = []

            return history

    async def create_or_update(
        self,
        merchant_id: int,
        client_phone: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Crée ou met à jour l'historique d'un client.
        """
        existing = await self.get_client_history(merchant_id, client_phone)

        if existing:
            # Mise à jour
            update_fields = {k: v for k, v in kwargs.items() if v is not None}
            update_fields['updated_at'] = datetime.now().isoformat()

            if update_fields:
                fields = ", ".join(f"{k} = ?" for k in update_fields.keys())
                values = list(update_fields.values())
                values.extend([merchant_id, client_phone])

                async with get_connection() as db:
                    await db.execute(
                        f"UPDATE client_history SET {fields} WHERE merchant_id = ? AND client_phone = ?",
                        tuple(values)
                    )
                    await db.commit()

            return await self.get_client_history(merchant_id, client_phone)
        else:
            # Création
            async with get_connection() as db:
                await db.execute(
                    """
                    INSERT INTO client_history (
                        merchant_id, client_phone, total_conversations,
                        total_purchases, total_spent, avg_negotiation_discount,
                        negotiation_style, last_interaction_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        merchant_id,
                        client_phone,
                        kwargs.get('total_conversations', 1),
                        kwargs.get('total_purchases', 0),
                        kwargs.get('total_spent', 0),
                        kwargs.get('avg_negotiation_discount', 0),
                        kwargs.get('negotiation_style', 'normal'),
                        datetime.now().isoformat()
                    )
                )
                await db.commit()

            return await self.get_client_history(merchant_id, client_phone)

    async def record_conversation(
        self,
        merchant_id: int,
        client_phone: str
    ) -> Dict[str, Any]:
        """
        Enregistre une nouvelle conversation pour un client.
        """
        history = await self.get_client_history(merchant_id, client_phone)

        if history:
            new_total = history['total_conversations'] + 1
            return await self.create_or_update(
                merchant_id,
                client_phone,
                total_conversations=new_total,
                last_interaction_date=datetime.now().isoformat()
            )
        else:
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
        """
        Enregistre un achat et met à jour les statistiques de négociation.
        """
        history = await self.get_client_history(merchant_id, client_phone)

        # Calculer le discount
        discount_percent = 0
        if original_price > 0 and final_price < original_price:
            discount_percent = ((original_price - final_price) / original_price) * 100

        if history:
            # Mettre à jour les stats existantes
            new_purchases = history['total_purchases'] + 1
            new_spent = history['total_spent'] + amount

            # Moyenne mobile du discount
            old_avg = history['avg_negotiation_discount'] or 0
            new_avg = ((old_avg * history['total_purchases']) + discount_percent) / new_purchases

            # Déterminer le style de négociation
            negotiation_style = self._determine_negotiation_style(new_avg, new_purchases)

            # Mettre à jour les catégories préférées
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
            # Nouveau client
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
        """
        Détermine le style de négociation d'un client basé sur son historique.

        Styles:
        - loyal: Client fidèle, achète souvent sans trop négocier
        - negotiator: Négocie activement, cherche les réductions
        - premium: Achète sans négocier (ou peu)
        - normal: Comportement standard
        """
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
        """
        Retourne le contexte de négociation pour adapter les contre-offres.

        Retourne:
        - suggested_discount: Réduction suggérée basée sur l'historique
        - client_style: Style de négociation du client
        - is_returning: Si c'est un client récurrent
        - purchase_count: Nombre d'achats précédents
        - loyalty_discount: Réduction fidélité possible
        """
        history = await self.get_client_history(merchant_id, client_phone)

        price_range = product_price - min_price
        max_discount_percent = (price_range / product_price) * 100 if product_price > 0 else 0

        if not history:
            # Nouveau client
            return {
                'is_returning': False,
                'client_style': 'unknown',
                'purchase_count': 0,
                'suggested_discount': min(5, max_discount_percent / 3),  # Commencer doucement
                'loyalty_discount': 0,
                'avg_discount': 0,
                'total_spent': 0,
                'recommendation': "Nouveau client - approche standard"
            }

        style = history['negotiation_style']
        purchases = history['total_purchases']
        avg_discount = history['avg_negotiation_discount'] or 0

        # Calculer la réduction suggérée selon le style
        if style == 'loyal':
            # Client fidèle: offrir un bon deal plus rapidement
            suggested = min(avg_discount + 3, max_discount_percent * 0.7)
            loyalty_discount = 5 if purchases >= 5 else 3
            recommendation = f"Client fidèle ({purchases} achats) - Offrir un bon prix rapidement"
        elif style == 'premium':
            # Client premium: peu de négociation attendue
            suggested = min(3, max_discount_percent * 0.3)
            loyalty_discount = 2
            recommendation = "Client premium - Pas besoin de négocier beaucoup"
        elif style == 'hard_negotiator':
            # Négociateur dur: rester ferme mais proposer des paliers
            suggested = min(avg_discount * 0.8, max_discount_percent * 0.5)
            loyalty_discount = 0  # Pas de bonus pour les négociateurs durs
            recommendation = f"Négociateur ({avg_discount:.0f}% moyen) - Rester ferme, paliers progressifs"
        elif style == 'negotiator':
            # Négociateur normal
            suggested = min(avg_discount, max_discount_percent * 0.6)
            loyalty_discount = 2 if purchases >= 3 else 0
            recommendation = "Négociateur - Proposer des paliers raisonnables"
        else:
            # Normal
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
        """
        Récupère les meilleurs clients d'un marchand.
        """
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM client_history
                WHERE merchant_id = ?
                ORDER BY total_spent DESC
                LIMIT ?
                """,
                (merchant_id, limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# Instance globale
_client_history_repo: Optional[ClientHistoryRepository] = None


def get_client_history_repository() -> ClientHistoryRepository:
    """Retourne l'instance globale du repository"""
    global _client_history_repo
    if _client_history_repo is None:
        _client_history_repo = ClientHistoryRepository()
    return _client_history_repo
