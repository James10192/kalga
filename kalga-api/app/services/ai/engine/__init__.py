"""
KALGA Conversation Engine v2.0
==============================
Moteur de conversation IA avancé avec:
- Machine à états finis (FSM) pour le flux de conversation
- Mémoire multi-niveaux (court terme + résumé contextuel)
- Analyse de sentiment et détection d'émotions
- Gestion intelligente du contexte et de la cohérence
- Réponses adaptatives basées sur le comportement client

Architecture inspirée de:
- Pactum AI (négociation automatisée)
- Mem0 (gestion de mémoire LLM)
- MemGPT (pagination de contexte)

Auteur: KALGA Team
"""

# States & FSM
from .states import (
    ConversationState,
    ConversationEvent,
    StateTransition,
    ConversationFSM,
)

# Memory
from .memory import ConversationMemory

# Sentiment
from .sentiment import (
    Emotion,
    SentimentAnalysis,
    SentimentAnalyzer,
)

# Intent
from .intent import (
    Intent,
    IntentExtractor,
)

# Negotiation
from .negotiation import NegotiationContext

# Response Generator
from .response_generator import ResponseGenerator

# Orchestrator (main engine)
from .orchestrator import (
    ConversationEngine,
    get_conversation_engine,
)

__all__ = [
    # States
    "ConversationState",
    "ConversationEvent",
    "StateTransition",
    "ConversationFSM",
    # Memory
    "ConversationMemory",
    # Sentiment
    "Emotion",
    "SentimentAnalysis",
    "SentimentAnalyzer",
    # Intent
    "Intent",
    "IntentExtractor",
    # Negotiation
    "NegotiationContext",
    # Response Generator
    "ResponseGenerator",
    # Orchestrator
    "ConversationEngine",
    "get_conversation_engine",
]
