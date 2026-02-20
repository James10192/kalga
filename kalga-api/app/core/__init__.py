"""
Core module - Configuration centrale de l'application
"""
from .config import settings, Settings
from .exceptions import (
    KalgaException,
    MerchantNotFoundError,
    ProductNotFoundError,
    ConversationNotFoundError,
    SessionExpiredError,
    ValidationError,
)
from .events import lifespan

__all__ = [
    "settings",
    "Settings",
    "KalgaException",
    "MerchantNotFoundError",
    "ProductNotFoundError",
    "ConversationNotFoundError",
    "SessionExpiredError",
    "ValidationError",
    "lifespan",
]
