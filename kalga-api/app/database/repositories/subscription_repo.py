"""
Repository pour la gestion des abonnements marchands.

Phase E2 : délègue à Convex (`internal/billing:*`). Signatures inchangées.
La logique de dates/limites reste ici (Python a `datetime.now()`) ; les
écritures atomiques et lectures passent par Convex. Les dates sont threadées
en epoch ms vers Convex et reviennent en ISO via l'adaptateur (parité SQLite).
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.infrastructure.convex_client import get_convex
from app.infrastructure.convex_repo_adapters import (
    adapt_subscription,
    iso_to_ms,
    now_ms,
)


def _dt_ms(dt: datetime) -> float:
    return dt.timestamp() * 1000.0


class SubscriptionRepository:
    """Gère les abonnements des marchands (backend Convex)."""

    async def get_by_merchant(self, merchant_id: int) -> Optional[Dict[str, Any]]:
        """Récupère l'abonnement d'un marchand."""
        doc = await get_convex().query("internal/billing:getByMerchant", {
            "merchantId": merchant_id,
        })
        return adapt_subscription(doc)

    async def create_trial(
        self,
        merchant_id: int,
        trial_days: int = 14,
        messages_limit: int = 500,
        products_limit: int = 10
    ) -> Dict[str, Any]:
        """Crée un abonnement trial pour un nouveau marchand."""
        now = datetime.now()
        trial_ends = now + timedelta(days=trial_days)
        doc = await get_convex().mutation("internal/billing:createTrial", {
            "merchantId": merchant_id,
            "startDate": _dt_ms(now),
            "trialEndsAt": _dt_ms(trial_ends),
            "messagesLimit": messages_limit,
            "productsLimit": products_limit,
        })
        return adapt_subscription(doc)

    async def upgrade_plan(
        self,
        merchant_id: int,
        plan: str,
        duration_months: int = 1,
        messages_limit: int = 5000,
        products_limit: int = 100
    ) -> Dict[str, Any]:
        """Upgrade l'abonnement d'un marchand."""
        now = datetime.now()
        end_date = now + timedelta(days=30 * duration_months)
        doc = await get_convex().mutation("internal/billing:upgradePlan", {
            "merchantId": merchant_id,
            "plan": plan,
            "startDate": _dt_ms(now),
            "endDate": _dt_ms(end_date),
            "messagesLimit": messages_limit,
            "productsLimit": products_limit,
        })
        return adapt_subscription(doc)

    async def increment_messages(self, merchant_id: int) -> Dict[str, Any]:
        """Incrémente le compteur de messages utilisés."""
        doc = await get_convex().mutation("internal/billing:incrementMessages", {
            "merchantId": merchant_id,
        })
        return adapt_subscription(doc)

    async def check_limits(self, merchant_id: int) -> Dict[str, Any]:
        """Vérifie les limites de l'abonnement (logique Python conservée)."""
        sub = await self.get_by_merchant(merchant_id)

        if not sub:
            return {
                "has_subscription": False,
                "can_send_messages": False,
                "can_add_products": False,
                "reason": "no_subscription"
            }

        now = datetime.now()

        if sub['plan'] == 'trial' and sub.get('trial_ends_at'):
            trial_ends = datetime.fromisoformat(sub['trial_ends_at'])
            if now > trial_ends:
                return {
                    "has_subscription": True,
                    "can_send_messages": False,
                    "can_add_products": False,
                    "reason": "trial_expired",
                    "expired_at": sub['trial_ends_at']
                }

        if sub.get('end_date'):
            end_date = datetime.fromisoformat(sub['end_date'])
            if now > end_date:
                return {
                    "has_subscription": True,
                    "can_send_messages": False,
                    "can_add_products": False,
                    "reason": "subscription_expired",
                    "expired_at": sub['end_date']
                }

        messages_ok = sub['messages_used'] < sub['messages_limit']

        return {
            "has_subscription": True,
            "can_send_messages": messages_ok,
            "can_add_products": True,
            "plan": sub['plan'],
            "messages_used": sub['messages_used'],
            "messages_limit": sub['messages_limit'],
            "messages_remaining": sub['messages_limit'] - sub['messages_used'],
            "reason": None if messages_ok else "messages_limit_reached"
        }

    async def reactivate(self, merchant_id: int) -> Dict[str, Any]:
        """Réactive un abonnement existant (trial ou expiré)."""
        existing = await self.get_by_merchant(merchant_id)
        if not existing:
            return None

        trial_ends = datetime.now() + timedelta(days=14)
        doc = await get_convex().mutation("internal/billing:reactivate", {
            "merchantId": merchant_id,
            "trialEndsAt": _dt_ms(trial_ends),
        })
        return adapt_subscription(doc)

    async def get_expiring_soon(self, days: int = 7) -> List[Dict[str, Any]]:
        """Récupère les abonnements qui expirent bientôt."""
        now = datetime.now()
        threshold = now + timedelta(days=days)
        docs = await get_convex().query("internal/billing:getExpiringSoon", {
            "nowMs": _dt_ms(now),
            "thresholdMs": _dt_ms(threshold),
        })
        return [adapt_subscription(d) for d in (docs or [])]

    async def mark_expired(self) -> int:
        """Marque les abonnements expirés."""
        result = await get_convex().mutation("internal/billing:markExpired", {
            "nowMs": now_ms(),
        })
        return result.get("expired", 0) if result else 0

    async def get_stats(self) -> Dict[str, Any]:
        """Statistiques globales des abonnements."""
        return await get_convex().query("internal/billing:getStats", {})


# Instance globale
_subscription_repo: Optional[SubscriptionRepository] = None


def get_subscription_repository() -> SubscriptionRepository:
    """Retourne l'instance globale du repository"""
    global _subscription_repo
    if _subscription_repo is None:
        _subscription_repo = SubscriptionRepository()
    return _subscription_repo
