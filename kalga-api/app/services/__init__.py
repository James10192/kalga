"""
Services métier de KALGA
"""
from .notification_service import NotificationService, get_notification_service
from .chat_service import ChatService, get_chat_service

# Re-export des fonctions IA pour la rétrocompatibilité
# (cerveau v1 supprimé en plan 004 — plus de `generate_response`)
from .ai import (
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
    "extract_product_code",
    "extract_price_offer",
    "detect_variant_request",
    "detect_photo_request",
    "detect_delivery_request",
    "detect_pickup_request",
    "detect_agreement",
    "detect_end_conversation",
]
