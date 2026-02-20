"""
Repository pour la gestion des abonnements marchands
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from .base import BaseRepository
from ..connection import get_connection


class SubscriptionRepository(BaseRepository):
    """Gère les abonnements des marchands"""

    def __init__(self):
        super().__init__("subscriptions")

    async def get_by_merchant(self, merchant_id: int) -> Optional[Dict[str, Any]]:
        """Récupère l'abonnement d'un marchand"""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM subscriptions WHERE merchant_id = ?",
                (merchant_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_trial(
        self,
        merchant_id: int,
        trial_days: int = 14,
        messages_limit: int = 500,
        products_limit: int = 10
    ) -> Dict[str, Any]:
        """Crée un abonnement trial pour un nouveau marchand"""
        trial_ends = datetime.now() + timedelta(days=trial_days)

        async with get_connection() as db:
            await db.execute(
                """
                INSERT INTO subscriptions (
                    merchant_id, plan, status, start_date, trial_ends_at,
                    messages_limit, messages_used, products_limit, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    merchant_id,
                    "trial",
                    "active",
                    datetime.now().isoformat(),
                    trial_ends.isoformat(),
                    messages_limit,
                    0,
                    products_limit,
                    datetime.now().isoformat()
                )
            )
            await db.commit()

        return await self.get_by_merchant(merchant_id)

    async def upgrade_plan(
        self,
        merchant_id: int,
        plan: str,
        duration_months: int = 1,
        messages_limit: int = 5000,
        products_limit: int = 100
    ) -> Dict[str, Any]:
        """Upgrade l'abonnement d'un marchand"""
        end_date = datetime.now() + timedelta(days=30 * duration_months)

        async with get_connection() as db:
            await db.execute(
                """
                UPDATE subscriptions SET
                    plan = ?,
                    status = 'active',
                    start_date = ?,
                    end_date = ?,
                    trial_ends_at = NULL,
                    messages_limit = ?,
                    messages_used = 0,
                    products_limit = ?,
                    updated_at = ?
                WHERE merchant_id = ?
                """,
                (
                    plan,
                    datetime.now().isoformat(),
                    end_date.isoformat(),
                    messages_limit,
                    products_limit,
                    datetime.now().isoformat(),
                    merchant_id
                )
            )
            await db.commit()

        return await self.get_by_merchant(merchant_id)

    async def increment_messages(self, merchant_id: int) -> Dict[str, Any]:
        """Incrémente le compteur de messages utilisés"""
        async with get_connection() as db:
            await db.execute(
                """
                UPDATE subscriptions SET
                    messages_used = messages_used + 1,
                    updated_at = ?
                WHERE merchant_id = ?
                """,
                (datetime.now().isoformat(), merchant_id)
            )
            await db.commit()

        return await self.get_by_merchant(merchant_id)

    async def check_limits(self, merchant_id: int) -> Dict[str, Any]:
        """Vérifie les limites de l'abonnement"""
        sub = await self.get_by_merchant(merchant_id)

        if not sub:
            return {
                "has_subscription": False,
                "can_send_messages": False,
                "can_add_products": False,
                "reason": "no_subscription"
            }

        now = datetime.now()

        # Vérifier si trial expiré
        if sub['plan'] == 'trial' and sub['trial_ends_at']:
            trial_ends = datetime.fromisoformat(sub['trial_ends_at'])
            if now > trial_ends:
                return {
                    "has_subscription": True,
                    "can_send_messages": False,
                    "can_add_products": False,
                    "reason": "trial_expired",
                    "expired_at": sub['trial_ends_at']
                }

        # Vérifier si abonnement expiré
        if sub['end_date']:
            end_date = datetime.fromisoformat(sub['end_date'])
            if now > end_date:
                return {
                    "has_subscription": True,
                    "can_send_messages": False,
                    "can_add_products": False,
                    "reason": "subscription_expired",
                    "expired_at": sub['end_date']
                }

        # Vérifier limite messages
        messages_ok = sub['messages_used'] < sub['messages_limit']

        return {
            "has_subscription": True,
            "can_send_messages": messages_ok,
            "can_add_products": True,  # On vérifie ailleurs pour les produits
            "plan": sub['plan'],
            "messages_used": sub['messages_used'],
            "messages_limit": sub['messages_limit'],
            "messages_remaining": sub['messages_limit'] - sub['messages_used'],
            "reason": None if messages_ok else "messages_limit_reached"
        }

    async def reactivate(self, merchant_id: int) -> Dict[str, Any]:
        """Réactive un abonnement existant (trial ou expiré)"""
        from datetime import timedelta

        # Récupérer l'abonnement existant
        existing = await self.get_by_merchant(merchant_id)

        if existing:
            # Réactiver avec un nouveau trial de 14 jours
            trial_ends = datetime.now() + timedelta(days=14)

            async with get_connection() as db:
                await db.execute(
                    """
                    UPDATE subscriptions SET
                        status = 'active',
                        plan = 'trial',
                        trial_ends_at = ?,
                        messages_used = 0,
                        updated_at = ?
                    WHERE merchant_id = ?
                    """,
                    (trial_ends.isoformat(), datetime.now().isoformat(), merchant_id)
                )
                await db.commit()

        return await self.get_by_merchant(merchant_id)

    async def get_expiring_soon(self, days: int = 7) -> List[Dict[str, Any]]:
        """Récupère les abonnements qui expirent bientôt"""
        threshold = (datetime.now() + timedelta(days=days)).isoformat()
        now = datetime.now().isoformat()

        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT s.*, m.name, m.phone, m.business_name
                FROM subscriptions s
                JOIN merchants m ON s.merchant_id = m.id
                WHERE (
                    (s.plan = 'trial' AND s.trial_ends_at BETWEEN ? AND ?)
                    OR (s.plan != 'trial' AND s.end_date BETWEEN ? AND ?)
                )
                AND s.status = 'active'
                ORDER BY COALESCE(s.trial_ends_at, s.end_date)
                """,
                (now, threshold, now, threshold)
            )
            rows = await cursor.fetchall()

        return [dict(row) for row in rows]

    async def mark_expired(self) -> int:
        """Marque les abonnements expirés"""
        now = datetime.now().isoformat()

        async with get_connection() as db:
            # Trial expirés
            cursor = await db.execute(
                """
                UPDATE subscriptions SET status = 'expired', updated_at = ?
                WHERE plan = 'trial' AND trial_ends_at < ? AND status = 'active'
                """,
                (now, now)
            )
            trial_count = cursor.rowcount

            # Abonnements payants expirés
            cursor = await db.execute(
                """
                UPDATE subscriptions SET status = 'expired', updated_at = ?
                WHERE plan != 'trial' AND end_date < ? AND status = 'active'
                """,
                (now, now)
            )
            paid_count = cursor.rowcount

            await db.commit()

        return trial_count + paid_count

    async def get_stats(self) -> Dict[str, Any]:
        """Statistiques globales des abonnements"""
        async with get_connection() as db:
            cursor = await db.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired,
                    SUM(CASE WHEN plan = 'trial' THEN 1 ELSE 0 END) as trials,
                    SUM(CASE WHEN plan = 'starter' THEN 1 ELSE 0 END) as starter,
                    SUM(CASE WHEN plan = 'pro' THEN 1 ELSE 0 END) as pro,
                    SUM(CASE WHEN plan = 'enterprise' THEN 1 ELSE 0 END) as enterprise,
                    AVG(messages_used) as avg_messages_used
                FROM subscriptions
            """)
            row = await cursor.fetchone()

        return dict(row) if row else {}


# Instance globale
_subscription_repo: Optional[SubscriptionRepository] = None


def get_subscription_repository() -> SubscriptionRepository:
    """Retourne l'instance globale du repository"""
    global _subscription_repo
    if _subscription_repo is None:
        _subscription_repo = SubscriptionRepository()
    return _subscription_repo
