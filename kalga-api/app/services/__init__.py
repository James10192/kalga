"""
Services métier de KALGA
"""
from .notification_service import NotificationService, get_notification_service
from .chat_service import ChatService, get_chat_service

# Re-export des fonctions IA pour la rétrocompatibilité
from .ai import (
    generate_response,
    extract_product_code,
    extract_price_offer,
    detect_variant_request,
    detect_photo_request,
    detect_delivery_request,
    detect_pickup_request,
    detect_agreement,
    detect_end_conversation,
)

__all__ = [
    # Services
    "NotificationService",
    "get_notification_service",
    "ChatService",
    "get_chat_service",
    # IA (rétrocompatibilité)
    "generate_response",
    "extract_product_code",
    "extract_price_offer",
    "detect_variant_request",
    "detect_photo_request",
    "detect_delivery_request",
    "detect_pickup_request",
    "detect_agreement",
    "detect_end_conversation",
]
