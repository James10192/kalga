"""
Repository pour la gestion des utilisateurs et authentification
"""
import hashlib
import secrets
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from .base import BaseRepository
from ..connection import get_connection


class UserRepository(BaseRepository):
    """Gère les utilisateurs (admin et marchands)"""

    def __init__(self):
        super().__init__("users")

    def _hash_password(self, password: str) -> str:
        """Hash un mot de passe avec SHA256 + salt"""
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return f"{salt}:{hashed}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Vérifie un mot de passe contre son hash"""
        try:
            salt, hashed = password_hash.split(":")
            check_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
            return check_hash == hashed
        except ValueError:
            return False

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Récupère un utilisateur par email"""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM users WHERE email = ?",
                (email.lower(),)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Récupère un utilisateur par ID"""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_user(
        self,
        email: str,
        password: str,
        role: str = "merchant",
        merchant_id: Optional[int] = None,
        is_verified: bool = False
    ) -> Dict[str, Any]:
        """Crée un nouvel utilisateur"""
        password_hash = self._hash_password(password)
        verification_token = secrets.token_urlsafe(32) if not is_verified else None

        async with get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO users (
                    email, password_hash, role, merchant_id,
                    is_verified, verification_token, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email.lower(),
                    password_hash,
                    role,
                    merchant_id,
                    is_verified,
                    verification_token,
                    datetime.now().isoformat()
                )
            )
            await db.commit()
            user_id = cursor.lastrowid

        return await self.get_by_id(user_id)

    async def verify_credentials(
        self,
        email: str,
        password: str
    ) -> Optional[Dict[str, Any]]:
        """Vérifie les credentials et retourne l'utilisateur si valide"""
        user = await self.get_by_email(email)

        if not user:
            return None

        if not user['is_active']:
            return None

        if not self._verify_password(password, user['password_hash']):
            return None

        # Mettre à jour last_login
        async with get_connection() as db:
            await db.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(), user['id'])
            )
            await db.commit()

        return user

    async def update_password(
        self,
        user_id: int,
        new_password: str
    ) -> bool:
        """Met à jour le mot de passe d'un utilisateur"""
        password_hash = self._hash_password(new_password)

        async with get_connection() as db:
            await db.execute(
                """
                UPDATE users SET password_hash = ?, updated_at = ?
                WHERE id = ?
                """,
                (password_hash, datetime.now().isoformat(), user_id)
            )
            await db.commit()
            return True

    async def verify_email(self, token: str) -> Optional[Dict[str, Any]]:
        """Vérifie l'email d'un utilisateur via token"""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM users WHERE verification_token = ?",
                (token,)
            )
            user = await cursor.fetchone()

            if not user:
                return None

            await db.execute(
                """
                UPDATE users SET
                    is_verified = 1,
                    verification_token = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), user['id'])
            )
            await db.commit()

        return await self.get_by_id(user['id'])

    async def create_reset_token(self, email: str) -> Optional[str]:
        """Crée un token de reset de mot de passe"""
        user = await self.get_by_email(email)
        if not user:
            return None

        reset_token = secrets.token_urlsafe(32)
        expires = datetime.now() + timedelta(hours=24)

        async with get_connection() as db:
            await db.execute(
                """
                UPDATE users SET
                    reset_token = ?,
                    reset_token_expires = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (reset_token, expires.isoformat(), datetime.now().isoformat(), user['id'])
            )
            await db.commit()

        return reset_token

    async def reset_password_with_token(
        self,
        token: str,
        new_password: str
    ) -> bool:
        """Reset le mot de passe avec un token"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM users
                WHERE reset_token = ? AND reset_token_expires > ?
                """,
                (token, datetime.now().isoformat())
            )
            user = await cursor.fetchone()

            if not user:
                return False

            password_hash = self._hash_password(new_password)

            await db.execute(
                """
                UPDATE users SET
                    password_hash = ?,
                    reset_token = NULL,
                    reset_token_expires = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (password_hash, datetime.now().isoformat(), user['id'])
            )
            await db.commit()

        return True

    async def set_active(self, user_id: int, is_active: bool) -> bool:
        """Active ou désactive un utilisateur"""
        async with get_connection() as db:
            await db.execute(
                "UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
                (is_active, datetime.now().isoformat(), user_id)
            )
            await db.commit()
            return True

    async def get_all_merchants(
        self,
        page: int = 1,
        limit: int = 50,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Récupère tous les marchands avec leurs infos de subscription"""
        offset = (page - 1) * limit

        base_query = """
            SELECT
                u.id as user_id,
                u.email,
                u.is_active,
                u.is_verified,
                u.last_login,
                u.created_at as user_created_at,
                m.id as merchant_id,
                m.name,
                m.phone,
                m.business_name,
                m.address,
                s.plan,
                s.status as subscription_status,
                s.start_date,
                s.end_date,
                s.trial_ends_at,
                s.messages_used,
                s.messages_limit
            FROM users u
            LEFT JOIN merchants m ON u.merchant_id = m.id
            LEFT JOIN subscriptions s ON m.id = s.merchant_id
            WHERE u.role = 'merchant'
        """

        if status_filter:
            if status_filter == "active":
                base_query += " AND u.is_active = 1"
            elif status_filter == "inactive":
                base_query += " AND u.is_active = 0"
            elif status_filter == "trial":
                base_query += " AND s.plan = 'trial'"
            elif status_filter == "expired":
                base_query += " AND s.status = 'expired'"

        count_query = f"SELECT COUNT(*) as total FROM ({base_query})"
        data_query = f"{base_query} ORDER BY u.created_at DESC LIMIT ? OFFSET ?"

        async with get_connection() as db:
            # Count total
            cursor = await db.execute(count_query)
            total_row = await cursor.fetchone()
            total = total_row['total'] if total_row else 0

            # Get data
            cursor = await db.execute(data_query, (limit, offset))
            rows = await cursor.fetchall()

        return {
            "merchants": [dict(row) for row in rows],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }

    async def get_admin_users(self) -> List[Dict[str, Any]]:
        """Récupère tous les administrateurs"""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM users WHERE role = 'admin' ORDER BY created_at"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def ensure_admin_exists(
        self,
        email: str,
        password: str
    ) -> Dict[str, Any]:
        """S'assure qu'un admin existe, le crée sinon"""
        existing = await self.get_by_email(email)
        if existing:
            return existing

        return await self.create_user(
            email=email,
            password=password,
            role="admin",
            is_verified=True
        )


# Instance globale
_user_repo: Optional[UserRepository] = None


def get_user_repository() -> UserRepository:
    """Retourne l'instance globale du repository"""
    global _user_repo
    if _user_repo is None:
        _user_repo = UserRepository()
    return _user_repo
