"""
FICHIER DE COMPATIBILITÉ
Ce fichier réexporte les fonctions depuis le nouveau module ai/
pour garantir la compatibilité avec le code existant.

Pour le nouveau code, importez directement depuis app.services.ai
"""
from .ai import (
    generate_response,
    analyze_conversation_health,
    extract_product_code,
    extract_price_offer,
    detect_delivery_request,
    detect_pickup_request,
    detect_end_conversation,
    detect_agreement,
    detect_variant_request,
    detect_photo_request,
    is_product_related_message,
    count_low_offers,
)
__all__ = [
    "generate_response",
    "analyze_conversation_health",
    "extract_product_code",
    "extract_price_offer",
    "detect_delivery_request",
    "detect_pickup_request",
    "detect_end_conversation",
    "detect_agreement",
    "detect_variant_request",
    "detect_photo_request",
    "is_product_related_message",
    "count_low_offers",
]
