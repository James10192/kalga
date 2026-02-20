"""
Router pour la gestion des activations marchands
Endpoints publics pour la vérification des codes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.activation_service import get_activation_service


router = APIRouter(prefix="/api/activation", tags=["Activation"])


class CodeVerificationRequest(BaseModel):
    """Requête de vérification de code"""
    code: str
    merchant_phone: str


class SubscriptionCheckRequest(BaseModel):
    """Requête de vérification d'abonnement"""
    merchant_phone: str


@router.post("/verify")
async def verify_activation_code(request: CodeVerificationRequest):
    """
    Vérifie un code d'activation et active l'abonnement.

    - **code**: Le code reçu par WhatsApp (ex: KALG7X3F)
    - **merchant_phone**: Le numéro du marchand (avec indicatif)

    Returns:
        - success: True si le code est valide et l'abonnement activé
        - message: Message de confirmation ou d'erreur
    """
    service = get_activation_service()

    result = await service.verify_code(
        code=request.code.strip().upper(),
        merchant_phone=request.merchant_phone
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/check-subscription")
async def check_subscription_status(request: SubscriptionCheckRequest):
    """
    Vérifie si un marchand a un abonnement actif.

    - **merchant_phone**: Le numéro du marchand

    Returns:
        - has_active_subscription: True si abonnement actif
        - subscription: Détails de l'abonnement (si actif)
        - reason: Raison si pas d'abonnement actif
    """
    service = get_activation_service()

    result = await service.check_subscription_status(request.merchant_phone)

    return result


@router.get("/status/{merchant_phone}")
async def get_activation_status(merchant_phone: str):
    """
    Vérifie le statut d'activation d'un marchand (version GET simple).

    Returns:
        - is_active: True si abonnement actif
        - needs_activation: True si le marchand doit entrer un code
        - subscription_info: Infos sur l'abonnement (si actif)
    """
    service = get_activation_service()

    result = await service.check_subscription_status(merchant_phone)

    return {
        "is_active": result.get("has_active_subscription", False),
        "needs_activation": not result.get("has_active_subscription", False),
        "reason": result.get("reason"),
        "subscription_info": result.get("subscription")
    }
