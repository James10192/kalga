"""
Injection de dépendances FastAPI
Fournit les factories pour les repositories et services
"""
from functools import lru_cache
from typing import Generator, Optional

from fastapi import Header, HTTPException

from .core.config import settings
from .database.repositories import (
    MerchantRepository,
    ProductRepository,
    ConversationRepository
)
from .services.notification_service import NotificationService
from .services.chat_service import ChatService


# === Sécurité interne (verrou bridge <-> API) ===

async def verify_internal_key(
    x_internal_key: Optional[str] = Header(default=None, alias="X-Internal-Key")
) -> None:
    """
    Vérifie le header `X-Internal-Key` sur les endpoints d'ingestion appelés par
    le bridge WhatsApp (`/api/chat/incoming`, `/api/chat/incoming-media`).

    Parité dev avec le bridge Node : si `INTERNAL_API_KEY` n'est pas configurée,
    on laisse passer (mode dev). En prod, la clé DOIT être posée des deux côtés.
    """
    if not settings.internal_api_key:
        return  # mode dev : clé non configurée -> pas de protection
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Internal-Key")


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
