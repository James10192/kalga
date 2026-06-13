"""
Repository pour la gestion des codes d'activation.

Phase E2 : délègue à Convex (`internal/activation:*`). Signatures inchangées.
La génération du code (KALG + 4 alphanum) reste ici ; Convex valide l'unicité
et insère atomiquement (invalidation des pending précédents incluse).

NB `admin_email` : l'ancien repo LEFT JOIN-ait la table `users` (supprimée,
Better Auth). `get_activation_history` renvoie désormais `admin_email: null`.
"""
import random
from datetime import datetime, timedelta
from typing import Optional, List

from app.infrastructure.convex_client import get_convex
from app.infrastructure.convex_repo_adapters import (
    adapt_activation_code,
    now_ms,
)


class ActivationRepository:
    """Repository pour les codes d'activation des marchands (backend Convex)."""

    CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    CODE_PREFIX = "KALG"
    CODE_SUFFIX_LENGTH = 4
    CODE_EXPIRY_HOURS = 24

    def _generate_code(self) -> str:
        """Génère un code: KALG + 4 aléatoires (sans O/0/I/1)."""
        suffix = ''.join(random.choices(self.CODE_CHARS, k=self.CODE_SUFFIX_LENGTH))
        return f"{self.CODE_PREFIX}{suffix}"

    async def create_code(self, merchant_id: int, admin_id) -> dict:
        """
        Crée un nouveau code d'activation pour un marchand.
        Invalide les codes précédents non utilisés (atomique côté Convex).
        """
        convex = get_convex()

        # Générer un code unique (vérif unicité côté Convex).
        code = None
        for _ in range(10):
            candidate = self._generate_code()
            taken = await convex.query("internal/activation:isCodeTaken", {
                "code": candidate,
            })
            if not taken:
                code = candidate
                break
        if not code:
            raise Exception("Impossible de générer un code unique")

        expires_at = datetime.now() + timedelta(hours=self.CODE_EXPIRY_HOURS)
        result = await convex.mutation("internal/activation:createCode", {
            "merchantId": merchant_id,
            "code": code,
            "expiresAt": expires_at.timestamp() * 1000.0,
            "createdBy": str(admin_id),
        })
        # Parité retour : {id, code, expires_at (ISO), merchant_id}.
        return {
            "id": result.get("id"),
            "code": result.get("code"),
            "expires_at": expires_at.isoformat(),
            "merchant_id": merchant_id,
        }

    async def validate_code(self, code: str, merchant_phone: str) -> dict:
        """Valide un code d'activation."""
        return await get_convex().mutation("internal/activation:validateCode", {
            "code": code,
            "merchantPhone": merchant_phone,
            "nowMs": now_ms(),
        })

    async def get_by_code(self, code: str) -> Optional[dict]:
        """Récupère un code d'activation par son code (+ infos marchand)."""
        doc = await get_convex().query("internal/activation:getByCode", {
            "code": code,
        })
        return adapt_activation_code(doc)

    async def get_pending_for_merchant(self, merchant_id: int) -> Optional[dict]:
        """Récupère le code en attente pour un marchand."""
        doc = await get_convex().query("internal/activation:getPendingForMerchant", {
            "merchantId": merchant_id,
        })
        return adapt_activation_code(doc)

    async def get_pending_merchants(self) -> List[dict]:
        """Marchands connectés WhatsApp mais sans abonnement actif."""
        rows = await get_convex().query("internal/activation:getPendingMerchants", {
            "nowMs": now_ms(),
        })
        # Les rows sont déjà snake_case ; on convertit created_at/pending_code_sent_at en ISO.
        from app.infrastructure.convex_repo_adapters import ms_to_iso
        out = []
        for r in (rows or []):
            r = dict(r)
            for k in ("created_at", "pending_code_sent_at"):
                if isinstance(r.get(k), (int, float)):
                    r[k] = ms_to_iso(r[k])
            out.append(r)
        return out

    async def expire_old_codes(self) -> int:
        """Expire les codes dépassés. Retourne le nombre de codes expirés."""
        result = await get_convex().mutation("internal/activation:expireOldCodes", {
            "nowMs": now_ms(),
        })
        return result.get("expired", 0) if result else 0

    async def get_activation_history(self, limit: int = 50) -> List[dict]:
        """Récupère l'historique des activations (pour admin)."""
        docs = await get_convex().query("internal/activation:getActivationHistory", {
            "limit": limit,
        })
        return [adapt_activation_code(d) for d in (docs or [])]


# Singleton pour injection de dépendances
_activation_repo: Optional[ActivationRepository] = None


def get_activation_repository() -> ActivationRepository:
    """Factory pour obtenir le repository d'activation"""
    global _activation_repo
    if _activation_repo is None:
        _activation_repo = ActivationRepository()
    return _activation_repo
