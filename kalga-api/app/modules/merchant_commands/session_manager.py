"""
Gestionnaire de sessions de création de produits
Gère le cycle de vie des sessions en mémoire avec protection contre les race conditions
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio
import logging

from ...core.config import settings

logger = logging.getLogger("kalga.sessions")


@dataclass
class ProductSession:
    """Représente une session de création de produit"""
    merchant_phone: str
    step: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def is_expired(self, timeout_minutes: int = None) -> bool:
        """Vérifie si la session a expiré"""
        timeout = timeout_minutes or settings.session_timeout_minutes
        return datetime.now() - self.created_at > timedelta(minutes=timeout)

    def update_step(self, new_step: str) -> None:
        """Met à jour l'étape et le timestamp"""
        self.step = new_step
        self.updated_at = datetime.now()

    def set_data(self, key: str, value: Any) -> None:
        """Met à jour une donnée de la session"""
        self.data[key] = value
        self.updated_at = datetime.now()

    def get_data(self, key: str, default: Any = None) -> Any:
        """Récupère une donnée de la session"""
        return self.data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit la session en dictionnaire"""
        return {
            "merchant_phone": self.merchant_phone,
            "step": self.step,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class SessionManager:
    """
    Gestionnaire centralisé des sessions de création.
    Thread-safe avec verrous asyncio.
    """

    def __init__(self):
        self._sessions: Dict[str, ProductSession] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def get_lock(self, merchant_phone: str) -> asyncio.Lock:
        """Obtient ou crée un verrou pour un marchand"""
        async with self._global_lock:
            if merchant_phone not in self._locks:
                self._locks[merchant_phone] = asyncio.Lock()
            return self._locks[merchant_phone]

    def exists(self, merchant_phone: str) -> bool:
        """Vérifie si une session existe"""
        return merchant_phone in self._sessions

    def get(self, merchant_phone: str) -> Optional[ProductSession]:
        """Récupère une session (None si inexistante ou expirée)"""
        session = self._sessions.get(merchant_phone)
        if session and session.is_expired():
            self.delete(merchant_phone)
            logger.info(f"Session expirée supprimée: {merchant_phone}")
            return None
        return session

    def create(
        self,
        merchant_phone: str,
        step: str,
        data: Optional[Dict[str, Any]] = None
    ) -> ProductSession:
        """Crée une nouvelle session"""
        session = ProductSession(
            merchant_phone=merchant_phone,
            step=step,
            data=data or {}
        )
        self._sessions[merchant_phone] = session
        logger.debug(f"Session créée: {merchant_phone}, step={step}")
        return session

    def update(
        self,
        merchant_phone: str,
        step: Optional[str] = None,
        **data_updates
    ) -> Optional[ProductSession]:
        """Met à jour une session existante"""
        session = self.get(merchant_phone)
        if not session:
            return None

        if step:
            session.update_step(step)

        for key, value in data_updates.items():
            session.set_data(key, value)

        logger.debug(f"Session mise à jour: {merchant_phone}, step={session.step}")
        return session

    def delete(self, merchant_phone: str) -> bool:
        """Supprime une session"""
        if merchant_phone in self._sessions:
            del self._sessions[merchant_phone]
            logger.debug(f"Session supprimée: {merchant_phone}")
            return True
        return False

    def cleanup_expired(self) -> int:
        """Nettoie toutes les sessions expirées. Retourne le nombre supprimé."""
        expired = [
            phone for phone, session in self._sessions.items()
            if session.is_expired()
        ]
        for phone in expired:
            del self._sessions[phone]
            logger.info(f"Session expirée nettoyée: {phone}")
        return len(expired)

    def get_active_count(self) -> int:
        """Retourne le nombre de sessions actives"""
        return len(self._sessions)

    def clear_all(self) -> int:
        """Supprime toutes les sessions (pour shutdown)"""
        count = len(self._sessions)
        self._sessions.clear()
        self._locks.clear()
        return count

    def get_all_active(self) -> Dict[str, Dict[str, Any]]:
        """Retourne toutes les sessions actives (pour debug)"""
        return {
            phone: session.to_dict()
            for phone, session in self._sessions.items()
            if not session.is_expired()
        }


# Instance singleton
session_manager = SessionManager()
