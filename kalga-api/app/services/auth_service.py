"""
Service d'authentification JWT pour KALGA
Gère les tokens, sessions et permissions
"""
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import settings
from ..database.repositories.user_repo import get_user_repository, UserRepository
from ..database.repositories.subscription_repo import get_subscription_repository
from ..database.connection import get_connection

security = HTTPBearer(auto_error=False)


class AuthService:
    """Service d'authentification principal"""

    def __init__(self, user_repo: UserRepository = None):
        self.user_repo = user_repo or get_user_repository()
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_expire = settings.jwt_access_token_expire_minutes
        self.refresh_expire = settings.jwt_refresh_token_expire_days

    def _create_token(
        self,
        data: Dict[str, Any],
        expires_delta: timedelta
    ) -> str:
        """Crée un token JWT"""
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_access_token(self, user: Dict[str, Any]) -> str:
        """Crée un token d'accès"""
        return self._create_token(
            {
                "sub": str(user["id"]),
                "email": user["email"],
                "role": user["role"],
                "merchant_id": user.get("merchant_id"),
                "type": "access"
            },
            timedelta(minutes=self.access_expire)
        )

    def create_refresh_token(self, user: Dict[str, Any]) -> str:
        """Crée un token de refresh"""
        return self._create_token(
            {
                "sub": str(user["id"]),
                "type": "refresh"
            },
            timedelta(days=self.refresh_expire)
        )

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Décode un token JWT"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    async def login(
        self,
        email: str,
        password: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Authentifie un utilisateur.
        Retourne (tokens, None) si succès, (None, error_message) sinon
        """
        user = await self.user_repo.verify_credentials(email, password)

        if not user:
            return None, "Email ou mot de passe incorrect"

        if not user["is_active"]:
            return None, "Compte désactivé. Contactez l'administrateur."

        # Créer les tokens
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)

        # Sauvegarder la session
        await self._save_session(user["id"], access_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "role": user["role"],
                "merchant_id": user.get("merchant_id"),
                "is_verified": user["is_verified"]
            }
        }, None

    async def refresh_access_token(
        self,
        refresh_token: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Rafraîchit le token d'accès"""
        payload = self.decode_token(refresh_token)

        if not payload or payload.get("type") != "refresh":
            return None, "Token de refresh invalide"

        user_id = int(payload["sub"])
        user = await self.user_repo.get_by_id(user_id)

        if not user or not user["is_active"]:
            return None, "Utilisateur non trouvé ou désactivé"

        new_access_token = self.create_access_token(user)
        await self._save_session(user_id, new_access_token)

        return new_access_token, None

    async def _save_session(
        self,
        user_id: int,
        token: str,
        device_info: str = None,
        ip_address: str = None
    ):
        """Sauvegarde une session active"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires = datetime.now() + timedelta(minutes=self.access_expire)

        async with get_connection() as db:
            # Supprimer les anciennes sessions expirées
            await db.execute(
                "DELETE FROM active_sessions WHERE user_id = ? AND expires_at < ?",
                (user_id, datetime.now().isoformat())
            )

            # Ajouter la nouvelle session
            await db.execute(
                """
                INSERT INTO active_sessions (
                    user_id, token_hash, device_info, ip_address,
                    last_activity, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    token_hash,
                    device_info,
                    ip_address,
                    datetime.now().isoformat(),
                    expires.isoformat(),
                    datetime.now().isoformat()
                )
            )
            await db.commit()

    async def logout(self, token: str) -> bool:
        """Invalide une session"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        async with get_connection() as db:
            await db.execute(
                "DELETE FROM active_sessions WHERE token_hash = ?",
                (token_hash,)
            )
            await db.commit()

        return True

    async def get_current_user(
        self,
        token: str
    ) -> Optional[Dict[str, Any]]:
        """Récupère l'utilisateur courant à partir du token"""
        payload = self.decode_token(token)

        if not payload or payload.get("type") != "access":
            return None

        user_id = int(payload["sub"])
        user = await self.user_repo.get_by_id(user_id)

        if not user or not user["is_active"]:
            return None

        return user

    async def register_merchant(
        self,
        email: str,
        password: str,
        name: str,
        phone: str,
        business_name: str = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Inscrit un nouveau marchand.
        Crée le user, le merchant et l'abonnement trial.
        """
        from ..database.repositories.merchant_repo import get_merchant_repository

        # Vérifier si email déjà utilisé
        existing = await self.user_repo.get_by_email(email)
        if existing:
            return None, "Cet email est déjà utilisé"

        merchant_repo = get_merchant_repository()

        # Vérifier si téléphone déjà utilisé
        existing_merchant = await merchant_repo.get_by_phone(phone)
        if existing_merchant:
            return None, "Ce numéro de téléphone est déjà enregistré"

        try:
            # Créer le marchand
            merchant = await merchant_repo.create(
                name=name,
                phone=phone,
                business_name=business_name
            )

            # Créer l'utilisateur
            user = await self.user_repo.create_user(
                email=email,
                password=password,
                role="merchant",
                merchant_id=merchant["id"],
                is_verified=False  # Nécessite vérification email
            )

            # Créer l'abonnement trial
            subscription_repo = get_subscription_repository()
            await subscription_repo.create_trial(
                merchant_id=merchant["id"],
                trial_days=settings.trial_duration_days,
                messages_limit=settings.trial_messages_limit,
                products_limit=settings.trial_products_limit
            )

            # Générer les tokens (même sans vérification pour le moment)
            access_token = self.create_access_token(user)
            refresh_token = self.create_refresh_token(user)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                    "role": user["role"],
                    "merchant_id": merchant["id"],
                    "is_verified": False
                },
                "merchant": merchant,
                "message": "Inscription réussie! Un email de vérification a été envoyé."
            }, None

        except Exception as e:
            return None, f"Erreur lors de l'inscription: {str(e)}"


# Instance globale
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Retourne l'instance globale du service"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


# ============================================
# DEPENDANCES FASTAPI
# ============================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Dépendance FastAPI pour obtenir l'utilisateur courant"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification requis",
            headers={"WWW-Authenticate": "Bearer"}
        )

    auth_service = get_auth_service()
    user = await auth_service.get_current_user(credentials.credentials)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


async def get_current_merchant(
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Dépendance pour obtenir un marchand authentifié"""
    if user["role"] != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux marchands"
        )

    if not user.get("merchant_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aucun compte marchand associé"
        )

    return user


async def get_current_admin(
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Dépendance pour obtenir un admin authentifié"""
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs"
        )

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Dict[str, Any]]:
    """Dépendance pour obtenir l'utilisateur si authentifié (optionnel)"""
    if not credentials:
        return None

    auth_service = get_auth_service()
    return await auth_service.get_current_user(credentials.credentials)
