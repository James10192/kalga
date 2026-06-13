"""
Module IA pour KALGA
====================
Briques IA partagées par le moteur de dialogue v2 (`app/services/dialogue/`) :
- Détecteurs d'intentions / extracteurs (purs)
- Client API DeepSeek
- Réponses de secours statiques (FallbackResponses) quand v2 -> None

Le cerveau v1 (conversation_ai / conversation_engine) a été supprimé en
plan 004 : v2 est le SEUL cerveau. Plus de toggle, plus de fallback v1.
"""

# Détecteurs d'intentions
from .detectors import (
    extract_product_code,
    extract_price_offer,
    detect_delivery_request,
    detect_pickup_request,
    detect_end_conversation,
    detect_agreement,
    detect_variant_request,
    detect_photo_request,
    detect_location_request,
    detect_frustration,
    detect_objection,
    is_product_related_message,
    count_low_offers,
    analyze_conversation_health,
)

# Client API DeepSeek
from .deepseek_client import DeepSeekClient, get_deepseek_client

# Réponses de secours (utilisées quand le moteur v2 renvoie None)
from .fallback_responses import FallbackResponses

__all__ = [
    # === Detectors ===
    "extract_product_code",
    "extract_price_offer",
    "detect_delivery_request",
    "detect_pickup_request",
    "detect_end_conversation",
    "detect_agreement",
    "detect_variant_request",
    "detect_photo_request",
    "detect_location_request",
    "detect_frustration",
    "detect_objection",
    "is_product_related_message",
    "count_low_offers",
    "analyze_conversation_health",

    # === DeepSeek Client ===
    "DeepSeekClient",
    "get_deepseek_client",

    # === Fallback ===
    "FallbackResponses",
]
