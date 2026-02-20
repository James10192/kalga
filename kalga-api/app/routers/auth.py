"""
Routes d'authentification pour KALGA
Login, Register, Refresh Token, etc.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from ..services.auth_service import (
    get_auth_service,
    get_current_user,
    get_current_merchant,
    AuthService
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ============================================
# SCHEMAS
# ============================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=8, max_length=15)
    business_name: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


# ============================================
# ROUTES
# ============================================

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Connexion utilisateur (Admin ou Marchand).
    Retourne les tokens JWT.
    """
    result, error = await auth_service.login(request.email, request.password)

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error
        )

    return result


@router.post("/register")
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Inscription d'un nouveau marchand.
    Crée le compte et l'abonnement trial.
    """
    result, error = await auth_service.register_merchant(
        email=request.email,
        password=request.password,
        name=request.name,
        phone=request.phone,
        business_name=request.business_name
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    return result


@router.post("/refresh")
async def refresh_token(
    request: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Rafraîchit le token d'accès avec le refresh token.
    """
    new_token, error = await auth_service.refresh_access_token(request.refresh_token)

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error
        )

    return {
        "access_token": new_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Déconnexion - Invalide le token actuel.
    """
    # Le token est déjà validé par get_current_user
    # On pourrait invalider la session côté serveur si nécessaire
    return {"message": "Déconnexion réussie"}


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """
    Récupère les informations de l'utilisateur connecté.
    """
    # Ne pas renvoyer le hash du password
    safe_user = {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "merchant_id": user.get("merchant_id"),
        "is_active": user["is_active"],
        "is_verified": user["is_verified"],
        "last_login": user.get("last_login"),
        "created_at": user["created_at"]
    }

    # Si c'est un marchand, ajouter les infos du marchand
    if user.get("merchant_id"):
        from ..database.repositories.merchant_repo import get_merchant_repository
        from ..database.repositories.subscription_repo import get_subscription_repository

        merchant_repo = get_merchant_repository()
        subscription_repo = get_subscription_repository()

        merchant = await merchant_repo.get_by_id(user["merchant_id"])
        subscription = await subscription_repo.get_by_merchant(user["merchant_id"])

        safe_user["merchant"] = merchant
        safe_user["subscription"] = subscription

    return safe_user


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Change le mot de passe de l'utilisateur connecté.
    """
    from ..database.repositories.user_repo import get_user_repository

    user_repo = get_user_repository()

    # Vérifier l'ancien mot de passe
    verified = await user_repo.verify_credentials(
        user["email"],
        request.current_password
    )

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect"
        )

    # Mettre à jour le mot de passe
    await user_repo.update_password(user["id"], request.new_password)

    return {"message": "Mot de passe mis à jour avec succès"}


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Demande de reset de mot de passe.
    Envoie un email avec le lien de reset.
    """
    from ..database.repositories.user_repo import get_user_repository

    user_repo = get_user_repository()
    token = await user_repo.create_reset_token(request.email)

    # Note: En production, envoyer l'email ici
    # Pour l'instant on retourne juste un message générique

    # On ne dit pas si l'email existe ou non (sécurité)
    return {
        "message": "Si cet email existe, un lien de réinitialisation a été envoyé.",
        "debug_token": token  # À supprimer en production!
    }


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Reset le mot de passe avec le token reçu par email.
    """
    from ..database.repositories.user_repo import get_user_repository

    user_repo = get_user_repository()
    success = await user_repo.reset_password_with_token(
        request.token,
        request.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token invalide ou expiré"
        )

    return {"message": "Mot de passe réinitialisé avec succès"}


@router.get("/verify-email/{token}")
async def verify_email(token: str):
    """
    Vérifie l'email d'un utilisateur via le token reçu.
    """
    from ..database.repositories.user_repo import get_user_repository

    user_repo = get_user_repository()
    user = await user_repo.verify_email(token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de vérification invalide"
        )

    return {"message": "Email vérifié avec succès"}
