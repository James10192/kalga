"""
Router pour la gestion du mode absence
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

from ..database.repositories import MerchantRepository

router = APIRouter(prefix="/api/merchants", tags=["away-mode"])

merchant_repo = MerchantRepository()


class DaySchedule(BaseModel):
    """Horaires pour un jour"""
    open: str = "08:00"
    close: str = "18:00"
    enabled: bool = True


class WorkingHours(BaseModel):
    """Configuration des horaires de travail"""
    enabled: bool = True
    timezone: str = "Africa/Abidjan"
    schedule: Dict[str, DaySchedule] = None

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "timezone": "Africa/Abidjan",
                "schedule": {
                    "monday": {"open": "08:00", "close": "18:00", "enabled": True},
                    "tuesday": {"open": "08:00", "close": "18:00", "enabled": True},
                    "wednesday": {"open": "08:00", "close": "18:00", "enabled": True},
                    "thursday": {"open": "08:00", "close": "18:00", "enabled": True},
                    "friday": {"open": "08:00", "close": "18:00", "enabled": True},
                    "saturday": {"open": "09:00", "close": "14:00", "enabled": True},
                    "sunday": {"open": "00:00", "close": "00:00", "enabled": False}
                }
            }
        }


class AwayModeSettings(BaseModel):
    """Paramètres du mode absence"""
    away_mode_enabled: Optional[bool] = None
    working_hours: Optional[WorkingHours] = None
    away_message: Optional[str] = None


class QuickAwayToggle(BaseModel):
    """Activation/désactivation rapide du mode absence"""
    enabled: bool
    message: Optional[str] = None


@router.get("/{merchant_phone}/away-settings")
async def get_away_settings(merchant_phone: str):
    """
    Récupère les paramètres du mode absence d'un marchand.
    """
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    settings = await merchant_repo.get_away_settings(merchant["id"])

    # Valeurs par défaut si pas de settings
    if not settings:
        settings = {
            "away_mode_enabled": False,
            "working_hours": None,
            "away_message": None
        }

    # Ajouter la disponibilité actuelle
    is_available, away_message = await merchant_repo.is_merchant_available(merchant["id"])

    return {
        "merchant_id": merchant["id"],
        "settings": settings,
        "current_status": {
            "is_available": is_available,
            "away_message": away_message
        }
    }


@router.put("/{merchant_phone}/away-settings")
async def update_away_settings(merchant_phone: str, settings: AwayModeSettings):
    """
    Met à jour les paramètres du mode absence d'un marchand.
    """
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    working_hours_dict = None
    if settings.working_hours:
        working_hours_dict = settings.working_hours.dict()

    success = await merchant_repo.update_away_settings(
        merchant_id=merchant["id"],
        away_mode_enabled=settings.away_mode_enabled,
        working_hours=working_hours_dict,
        away_message=settings.away_message
    )

    if not success:
        raise HTTPException(status_code=400, detail="Aucune modification effectuée")

    # Retourner les nouveaux paramètres
    new_settings = await merchant_repo.get_away_settings(merchant["id"])
    is_available, away_message = await merchant_repo.is_merchant_available(merchant["id"])

    return {
        "success": True,
        "settings": new_settings,
        "current_status": {
            "is_available": is_available,
            "away_message": away_message
        }
    }


@router.post("/{merchant_phone}/away-toggle")
async def toggle_away_mode(merchant_phone: str, toggle: QuickAwayToggle):
    """
    Active/désactive rapidement le mode absence.
    """
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    update_data = {"away_mode_enabled": toggle.enabled}
    if toggle.message:
        update_data["away_message"] = toggle.message

    await merchant_repo.update_away_settings(
        merchant_id=merchant["id"],
        **update_data
    )

    is_available, away_message = await merchant_repo.is_merchant_available(merchant["id"])

    return {
        "success": True,
        "away_mode_enabled": toggle.enabled,
        "is_available": is_available,
        "away_message": away_message
    }


@router.get("/{merchant_phone}/availability")
async def check_availability(merchant_phone: str):
    """
    Vérifie si un marchand est actuellement disponible.
    """
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    is_available, away_message = await merchant_repo.is_merchant_available(merchant["id"])

    return {
        "merchant_id": merchant["id"],
        "is_available": is_available,
        "away_message": away_message
    }
