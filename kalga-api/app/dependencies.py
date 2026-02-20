"""
Injection de dépendances FastAPI
Fournit les factories pour les repositories et services
"""
from functools import lru_cache
from typing import Generator

from .database.repositories import (
    MerchantRepository,
    ProductRepository,
    ConversationRepository
)
from .services.notification_service import NotificationService
from .services.chat_service import ChatService


# === Repositories ===

@lru_cache()
def get_merchant_repository() -> MerchantRepository:
    """Retourne une instance singleton du MerchantRepository"""
    return MerchantRepository()


@lru_cache()
def get_product_repository() -> ProductRepository:
    """Retourne une instance singleton du ProductRepository"""
    return ProductRepository()


@lru_cache()
def get_conversation_repository() -> ConversationRepository:
    """Retourne une instance singleton du ConversationRepository"""
    return ConversationRepository()


# === Services ===

@lru_cache()
def get_notification_service() -> NotificationService:
    """Retourne une instance singleton du NotificationService"""
    return NotificationService()


@lru_cache()
def get_chat_service() -> ChatService:
    """Retourne une instance singleton du ChatService"""
    return ChatService(
        merchant_repo=get_merchant_repository(),
        product_repo=get_product_repository(),
        conversation_repo=get_conversation_repository(),
        notification_service=get_notification_service()
    )
