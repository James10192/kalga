"""
Repository pour la gestion des codes d'activation
Gère la création, validation et expiration des codes
"""
import random
import string
from datetime import datetime, timedelta
from typing import Optional, List
from ..connection import get_connection


class ActivationRepository:
    """Repository pour les codes d'activation des marchands"""

    # Caractères pour générer les codes (sans O/0/I/1 pour éviter confusion)
    CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    CODE_PREFIX = "KALG"
    CODE_SUFFIX_LENGTH = 4
    CODE_EXPIRY_HOURS = 24

    def _generate_code(self) -> str:
        """Génère un code unique de 8 caractères: KALG + 4 aléatoires"""
        suffix = ''.join(random.choices(self.CODE_CHARS, k=self.CODE_SUFFIX_LENGTH))
        return f"{self.CODE_PREFIX}{suffix}"

    async def create_code(self, merchant_id: int, admin_id: int) -> dict:
        """
        Crée un nouveau code d'activation pour un marchand.
        Invalide les codes précédents non utilisés.

        Returns:
            dict avec id, code, expires_at
        """
        async with get_connection() as db:
            # Invalider les codes précédents non utilisés
            await db.execute("""
                UPDATE activation_codes
                SET status = 'expired'
                WHERE merchant_id = ? AND status = 'pending'
            """, (merchant_id,))

            # Générer un code unique
            max_attempts = 10
            code = None
            for _ in range(max_attempts):
                candidate = self._generate_code()
                cursor = await db.execute(
                    "SELECT id FROM activation_codes WHERE code = ?",
                    (candidate,)
                )
                if not await cursor.fetchone():
                    code = candidate
                    break

            if not code:
                raise Exception("Impossible de générer un code unique")

            # Date d'expiration
            expires_at = datetime.now() + timedelta(hours=self.CODE_EXPIRY_HOURS)

            # Insérer le code
            cursor = await db.execute("""
                INSERT INTO activation_codes (merchant_id, code, status, expires_at, created_by)
                VALUES (?, ?, 'pending', ?, ?)
            """, (merchant_id, code, expires_at.isoformat(), admin_id))

            await db.commit()

            return {
                "id": cursor.lastrowid,
                "code": code,
                "expires_at": expires_at.isoformat(),
                "merchant_id": merchant_id
            }

    async def validate_code(self, code: str, merchant_phone: str) -> dict:
        """
        Valide un code d'activation.

        Returns:
            dict avec success, message, merchant_id (si succès)
        """
        async with get_connection() as db:
            # Vérifier le code
            cursor = await db.execute("""
                SELECT ac.*, m.phone as merchant_phone, m.id as merchant_id
                FROM activation_codes ac
                JOIN merchants m ON m.id = ac.merchant_id
                WHERE ac.code = ? AND ac.status = 'pending'
            """, (code.upper(),))

            row = await cursor.fetchone()

            if not row:
                return {
                    "success": False,
                    "message": "Code invalide ou déjà utilisé"
                }

            # Vérifier que le code correspond au marchand
            if row["merchant_phone"] != merchant_phone:
                return {
                    "success": False,
                    "message": "Ce code n'est pas associé à votre numéro"
                }

            # Vérifier l'expiration
            expires_at = datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
            if expires_at and datetime.now() > expires_at:
                await db.execute(
                    "UPDATE activation_codes SET status = 'expired' WHERE id = ?",
                    (row["id"],)
                )
                await db.commit()
                return {
                    "success": False,
                    "message": "Code expiré. Contactez le support."
                }

            # Marquer comme utilisé
            await db.execute("""
                UPDATE activation_codes
                SET status = 'used', used_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (row["id"],))

            await db.commit()

            return {
                "success": True,
                "message": "Code validé avec succès",
                "merchant_id": row["merchant_id"]
            }

    async def get_by_code(self, code: str) -> Optional[dict]:
        """Récupère un code d'activation par son code"""
        async with get_connection() as db:
            cursor = await db.execute("""
                SELECT ac.*, m.phone as merchant_phone, m.name as merchant_name
                FROM activation_codes ac
                JOIN merchants m ON m.id = ac.merchant_id
                WHERE ac.code = ?
            """, (code.upper(),))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_pending_for_merchant(self, merchant_id: int) -> Optional[dict]:
        """Récupère le code en attente pour un marchand"""
        async with get_connection() as db:
            cursor = await db.execute("""
                SELECT * FROM activation_codes
                WHERE merchant_id = ? AND status = 'pending'
                ORDER BY created_at DESC
                LIMIT 1
            """, (merchant_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_pending_merchants(self) -> List[dict]:
        """
        Récupère tous les marchands connectés WhatsApp mais sans abonnement actif.
        Ce sont les marchands "en attente de paiement".
        """
        async with get_connection() as db:
            # Marchands qui n'ont pas d'abonnement actif
            cursor = await db.execute("""
                SELECT
                    m.id,
                    m.phone,
                    m.name,
                    m.business_name,
                    m.created_at,
                    s.status as subscription_status,
                    s.plan as subscription_plan,
                    (SELECT MAX(ac.created_at) FROM activation_codes ac
                     WHERE ac.merchant_id = m.id AND ac.status = 'pending') as pending_code_sent_at,
                    (SELECT ac.code FROM activation_codes ac
                     WHERE ac.merchant_id = m.id AND ac.status = 'pending'
                     ORDER BY ac.created_at DESC LIMIT 1) as pending_code
                FROM merchants m
                LEFT JOIN subscriptions s ON s.merchant_id = m.id
                WHERE s.id IS NULL
                   OR s.status != 'active'
                   OR (s.plan = 'trial' AND s.trial_ends_at < CURRENT_TIMESTAMP)
                ORDER BY m.created_at DESC
            """)

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def expire_old_codes(self) -> int:
        """Expire les codes dépassés. Retourne le nombre de codes expirés."""
        async with get_connection() as db:
            cursor = await db.execute("""
                UPDATE activation_codes
                SET status = 'expired'
                WHERE status = 'pending'
                  AND expires_at < CURRENT_TIMESTAMP
            """)
            await db.commit()
            return cursor.rowcount

    async def get_activation_history(self, limit: int = 50) -> List[dict]:
        """Récupère l'historique des activations (pour admin)"""
        async with get_connection() as db:
            cursor = await db.execute("""
                SELECT
                    ac.*,
                    m.phone as merchant_phone,
                    m.name as merchant_name,
                    u.email as admin_email
                FROM activation_codes ac
                JOIN merchants m ON m.id = ac.merchant_id
                LEFT JOIN users u ON u.id = ac.created_by
                ORDER BY ac.created_at DESC
                LIMIT ?
            """, (limit,))

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# Singleton pour injection de dépendances
_activation_repo: Optional[ActivationRepository] = None


def get_activation_repository() -> ActivationRepository:
    """Factory pour obtenir le repository d'activation"""
    global _activation_repo
    if _activation_repo is None:
        _activation_repo = ActivationRepository()
    return _activation_repo
