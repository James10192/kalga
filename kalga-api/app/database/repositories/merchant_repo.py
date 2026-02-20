"""
Repository pour la gestion des marchands
"""
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, time
from .base import BaseRepository
from ..connection import get_connection


class MerchantRepository(BaseRepository):
    """Gère les opérations CRUD pour les marchands"""

    def __init__(self):
        super().__init__("merchants")

    async def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Récupère un marchand par son numéro de téléphone"""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM merchants WHERE phone = ?",
                (phone,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create(self, name: str, phone: str, business_name: str = None) -> Dict[str, Any]:
        """Crée un nouveau marchand"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO merchants (name, phone, business_name)
                VALUES (?, ?, ?)
                """,
                (name, phone, business_name)
            )
            await db.commit()
            merchant_id = cursor.lastrowid

            # Récupérer le marchand créé
            cursor = await db.execute(
                "SELECT * FROM merchants WHERE id = ?",
                (merchant_id,)
            )
            row = await cursor.fetchone()
            return dict(row)

    async def update(self, merchant_id: int, **kwargs) -> bool:
        """Met à jour un marchand avec les champs fournis"""
        if not kwargs:
            return False

        # Construire la requête dynamiquement
        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values())
        values.append(merchant_id)

        async with get_connection() as db:
            cursor = await db.execute(
                f"UPDATE merchants SET {fields} WHERE id = ?",
                tuple(values)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_location(
        self,
        merchant_id: int,
        address: str = None,
        latitude: float = None,
        longitude: float = None
    ) -> bool:
        """Met à jour la localisation d'un marchand"""
        update_fields = {}
        if address is not None:
            update_fields['address'] = address
        if latitude is not None:
            update_fields['latitude'] = latitude
        if longitude is not None:
            update_fields['longitude'] = longitude

        return await self.update(merchant_id, **update_fields)

    async def get_all(self, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        """Récupère tous les marchands avec pagination"""
        offset = (page - 1) * limit

        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT * FROM merchants
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_total_count(self) -> int:
        """Retourne le nombre total de marchands"""
        return await self.count()

    # ============= GESTION MODE ABSENCE =============

    async def update_away_settings(
        self,
        merchant_id: int,
        away_mode_enabled: bool = None,
        working_hours: Dict = None,
        away_message: str = None
    ) -> bool:
        """
        Met à jour les paramètres du mode absence.

        working_hours format:
        {
            "enabled": true,
            "timezone": "Africa/Abidjan",
            "schedule": {
                "monday": {"open": "08:00", "close": "18:00", "enabled": true},
                "tuesday": {"open": "08:00", "close": "18:00", "enabled": true},
                ...
            }
        }
        """
        update_fields = {}

        if away_mode_enabled is not None:
            update_fields['away_mode_enabled'] = 1 if away_mode_enabled else 0
        if working_hours is not None:
            update_fields['working_hours'] = json.dumps(working_hours)
        if away_message is not None:
            update_fields['away_message'] = away_message

        if not update_fields:
            return False

        return await self.update(merchant_id, **update_fields)

    async def get_away_settings(self, merchant_id: int) -> Optional[Dict[str, Any]]:
        """Récupère les paramètres du mode absence d'un marchand"""
        async with get_connection() as db:
            cursor = await db.execute(
                """
                SELECT away_mode_enabled, working_hours, away_message
                FROM merchants WHERE id = ?
                """,
                (merchant_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            working_hours = None
            if row['working_hours']:
                try:
                    working_hours = json.loads(row['working_hours'])
                except json.JSONDecodeError:
                    pass

            return {
                'away_mode_enabled': bool(row['away_mode_enabled']),
                'working_hours': working_hours,
                'away_message': row['away_message']
            }

    def is_within_working_hours(self, working_hours: Dict) -> bool:
        """
        Vérifie si l'heure actuelle est dans les heures d'ouverture.
        Retourne True si le marchand est disponible.
        """
        if not working_hours or not working_hours.get('enabled'):
            return True  # Pas de config = toujours disponible

        schedule = working_hours.get('schedule', {})

        # Jour actuel (en anglais, lowercase)
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        now = datetime.now()
        current_day = day_names[now.weekday()]

        day_config = schedule.get(current_day, {})

        if not day_config.get('enabled', True):
            return False  # Jour fermé

        open_time_str = day_config.get('open', '08:00')
        close_time_str = day_config.get('close', '18:00')

        try:
            open_time = datetime.strptime(open_time_str, '%H:%M').time()
            close_time = datetime.strptime(close_time_str, '%H:%M').time()
            current_time = now.time()

            return open_time <= current_time <= close_time
        except ValueError:
            return True  # En cas d'erreur de format, considérer disponible

    async def is_merchant_available(self, merchant_id: int) -> tuple[bool, str]:
        """
        Vérifie si un marchand est disponible pour répondre.

        Retourne:
            (is_available, away_message)
            - is_available: True si disponible
            - away_message: Message d'absence si non disponible
        """
        settings = await self.get_away_settings(merchant_id)

        if not settings:
            return (True, None)

        # Mode absence manuel activé
        if settings['away_mode_enabled']:
            default_away_msg = "Bonjour! Je suis actuellement absent. Je vous répondrai dès que possible. Merci de votre patience!"
            return (False, settings['away_message'] or default_away_msg)

        # Vérifier les horaires de travail
        working_hours = settings.get('working_hours')
        if working_hours and working_hours.get('enabled'):
            if not self.is_within_working_hours(working_hours):
                default_closed_msg = "Bonjour! Notre boutique est actuellement fermée. Nous reviendrons vers vous dès l'ouverture. Merci!"
                return (False, settings['away_message'] or default_closed_msg)

        return (True, None)

    async def get_by_id(self, merchant_id: int) -> Optional[Dict[str, Any]]:
        """Récupère un marchand par son ID"""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM merchants WHERE id = ?",
                (merchant_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None


# Instance globale
_merchant_repo: Optional[MerchantRepository] = None


def get_merchant_repository() -> MerchantRepository:
    """Retourne l'instance globale du repository"""
    global _merchant_repo
    if _merchant_repo is None:
        _merchant_repo = MerchantRepository()
    return _merchant_repo
