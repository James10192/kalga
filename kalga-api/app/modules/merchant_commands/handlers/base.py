"""
Classe de base pour les handlers de commandes
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import re

from ..session_manager import ProductSession
from ..schemas import CommandResponse, CommandAction


class BaseHandler(ABC):
    """Classe de base abstraite pour tous les handlers"""

    @abstractmethod
    async def handle(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any
    ) -> CommandResponse:
        """Traite une étape du flux"""
        pass

    def _response(
        self,
        text: str,
        action: CommandAction,
        product_code: Optional[str] = None
    ) -> CommandResponse:
        """Helper pour créer une réponse"""
        return CommandResponse(
            response=text,
            action=action,
            product_code=product_code
        )

    def _error(self, message: str) -> CommandResponse:
        """Helper pour créer une réponse d'erreur"""
        return self._response(message, CommandAction.ERROR)

    def _ignored(self) -> CommandResponse:
        """Helper pour créer une réponse ignorée"""
        return self._response("", CommandAction.IGNORED)


class PriceExtractor:
    """Utilitaire pour extraire les prix des messages"""

    @staticmethod
    def extract(text: str) -> Optional[float]:
        """
        Extrait un prix d'un message.
        Supporte: 15k, 15000, 15 000, 15000 fcfa, etc.
        """
        text_lower = text.lower().strip()

        # Pattern pour "15k" ou "15K"
        k_match = re.search(r'(\d+)\s*k\b', text_lower)
        if k_match:
            return float(k_match.group(1)) * 1000

        # Pattern pour nombres avec FCFA/F explicite
        fcfa_match = re.search(r'(\d[\d\s]*\d|\d+)\s*(?:fcfa|f|francs)\b', text_lower)
        if fcfa_match:
            value = fcfa_match.group(1).replace(' ', '')
            return float(value)

        # Si le message est uniquement un nombre
        clean_text = text.strip().replace(' ', '')
        if clean_text.isdigit() and len(clean_text) >= 4:
            return float(clean_text)

        # Pattern pour nombres >= 1000 si message court
        if len(text) < 20:
            num_match = re.search(r'\b(\d{4,})\b', text)
            if num_match:
                return float(num_match.group(1))

        return None
