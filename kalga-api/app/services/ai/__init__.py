"""
Module IA pour KALGA v2.0
=========================
Système de conversation IA avancé avec:
- Machine à États Finis (FSM) pour le flux de conversation
- Analyse de sentiment et détection d'émotions
- Mémoire multi-niveaux (court terme + résumé)
- Négociation intelligente avec contre-offres dynamiques
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
    count_low_offers
)

# Client API DeepSeek
from .deepseek_client import DeepSeekClient, get_deepseek_client

# Réponses de secours
from .fallback_responses import FallbackResponses

# Moteur de conversation principal
from .conversation_ai import generate_response, analyze_conversation_health

# Nouveau moteur avancé
from .conversation_engine import (
    ConversationEngine,
    get_conversation_engine,
    ConversationState,
    ConversationEvent,
    ConversationFSM,
    ConversationMemory,
    SentimentAnalyzer,
    SentimentAnalysis,
    Emotion,
    IntentExtractor,
    Intent,
    NegotiationContext,
    ResponseGenerator
)

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

    # === DeepSeek Client ===
    "DeepSeekClient",
    "get_deepseek_client",

    # === Fallback ===
    "FallbackResponses",

    # === Main API ===
    "generate_response",
    "analyze_conversation_health",

    # === Conversation Engine v2.0 ===
    "ConversationEngine",
    "get_conversation_engine",
    "ConversationState",
    "ConversationEvent",
    "ConversationFSM",
    "ConversationMemory",
    "SentimentAnalyzer",
    "SentimentAnalysis",
    "Emotion",
    "IntentExtractor",
    "Intent",
    "NegotiationContext",
    "ResponseGenerator"
]
