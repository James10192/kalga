"""
Repository pour la gestion des marchands.

Phase E2 : délègue à Convex (`internal/merchant:*`) pour le NON hot-path.
`get_by_phone` (hot-path) passe par `internal/chat:getContext` côté chat ; il
reste exposé ici pour les routers/services et délègue à `internal/merchant`.
Signatures publiques inchangées.
"""
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.infrastructure.convex_client import get_convex
from app.infrastructure.convex_repo_adapters import (
    adapt_merchant_full,
    merchant_patch_to_camel,
)


class MerchantRepository:
    """Gère les opérations CRUD pour les marchands (backend Convex)."""

    async def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Récupère un marchand par son numéro de téléphone."""
        doc = await get_convex().query("internal/merchant:getByPhone", {
            "phone": phone,
        })
        return adapt_merchant_full(doc)

    async def get_by_id(self, merchant_id: int) -> Optional[Dict[str, Any]]:
        """Récupère un marchand par son ID."""
        doc = await get_convex().query("internal/merchant:getById", {
            "merchantId": merchant_id,
        })
        return adapt_merchant_full(doc)

    async def create(self, name: str, phone: str, business_name: str = None) -> Dict[str, Any]:
        """Crée un nouveau marchand."""
        args: Dict[str, Any] = {"name": name, "phone": phone}
        if business_name is not None:
            args["businessName"] = business_name
        doc = await get_convex().mutation("internal/merchant:create", args)
        return adapt_merchant_full(doc)

    async def update(self, merchant_id: int, **kwargs) -> bool:
        """Met à jour un marchand avec les champs fournis."""
        if not kwargs:
            return False
        patch = merchant_patch_to_camel(kwargs)
        if not patch:
            return False
        result = await get_convex().mutation("internal/merchant:update", {
            "merchantId": merchant_id,
            "patch": patch,
        })
        return bool(result and result.get("updated"))

    async def update_location(
        self,
        merchant_id: int,
        address: str = None,
        latitude: float = None,
        longitude: float = None
    ) -> bool:
        """Met à jour la localisation d'un marchand."""
        update_fields = {}
        if address is not None:
            update_fields['address'] = address
        if latitude is not None:
            update_fields['latitude'] = latitude
        if longitude is not None:
            update_fields['longitude'] = longitude
        return await self.update(merchant_id, **update_fields)

    async def get_all(self, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        """Récupère tous les marchands avec pagination."""
        docs = await get_convex().query("internal/merchant:getAll", {
            "page": page,
            "limit": limit,
        })
        return [adapt_merchant_full(d) for d in (docs or [])]

    async def get_total_count(self) -> int:
        """Retourne le nombre total de marchands."""
        return await get_convex().query("internal/merchant:getTotalCount", {})

    # ============= GESTION MODE ABSENCE =============

    async def update_away_settings(
        self,
        merchant_id: int,
        away_mode_enabled: bool = None,
        working_hours: Dict = None,
        away_message: str = None
    ) -> bool:
        """Met à jour les paramètres du mode absence."""
        update_fields: Dict[str, Any] = {}
        if away_mode_enabled is not None:
            update_fields['away_mode_enabled'] = away_mode_enabled
        if working_hours is not None:
            update_fields['working_hours'] = json.dumps(working_hours)
        if away_message is not None:
            update_fields['away_message'] = away_message
        if not update_fields:
            return False
        return await self.update(merchant_id, **update_fields)

    async def get_away_settings(self, merchant_id: int) -> Optional[Dict[str, Any]]:
        """Récupère les paramètres du mode absence d'un marchand."""
        row = await get_convex().query("internal/merchant:getAwaySettings", {
            "merchantId": merchant_id,
        })
        if not row:
            return None

        working_hours = None
        if row.get('working_hours'):
            try:
                working_hours = json.loads(row['working_hours'])
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            'away_mode_enabled': bool(row.get('away_mode_enabled')),
            'working_hours': working_hours,
            'away_message': row.get('away_message'),
        }

    def is_within_working_hours(self, working_hours: Dict) -> bool:
        """Vérifie si l'heure actuelle est dans les heures d'ouverture."""
        if not working_hours or not working_hours.get('enabled'):
            return True

        schedule = working_hours.get('schedule', {})
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        now = datetime.now()
        current_day = day_names[now.weekday()]
        day_config = schedule.get(current_day, {})

        if not day_config.get('enabled', True):
            return False

        open_time_str = day_config.get('open', '08:00')
        close_time_str = day_config.get('close', '18:00')

        try:
            open_time = datetime.strptime(open_time_str, '%H:%M').time()
            close_time = datetime.strptime(close_time_str, '%H:%M').time()
            current_time = now.time()
            return open_time <= current_time <= close_time
        except ValueError:
            return True

    async def is_merchant_available(self, merchant_id: int) -> tuple[bool, str]:
        """Vérifie si un marchand est disponible pour répondre."""
        settings = await self.get_away_settings(merchant_id)
        if not settings:
            return (True, None)

        if settings['away_mode_enabled']:
            default_away_msg = "Bonjour! Je suis actuellement absent. Je vous répondrai dès que possible. Merci de votre patience!"
            return (False, settings['away_message'] or default_away_msg)

        working_hours = settings.get('working_hours')
        if working_hours and working_hours.get('enabled'):
            if not self.is_within_working_hours(working_hours):
                default_closed_msg = "Bonjour! Notre boutique est actuellement fermée. Nous reviendrons vers vous dès l'ouverture. Merci!"
                return (False, settings['away_message'] or default_closed_msg)

        return (True, None)


# Instance globale
_merchant_repo: Optional[MerchantRepository] = None


def get_merchant_repository() -> MerchantRepository:
    """Retourne l'instance globale du repository"""
    global _merchant_repo
    if _merchant_repo is None:
        _merchant_repo = MerchantRepository()
    return _merchant_repo
