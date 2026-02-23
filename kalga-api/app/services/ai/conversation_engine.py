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

import re
import logging
import unicodedata
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime
import random

logger = logging.getLogger("kalga.conversation_engine")


# =============================================================================
# PARTIE 1: MACHINE À ÉTATS FINIS (FSM) - Flux de Conversation
# =============================================================================

class ConversationState(Enum):
    """
    États possibles de la conversation.
    Chaque état définit le comportement du bot.
    """
    # États initiaux
    GREETING = auto()           # Premier contact
    PRODUCT_INQUIRY = auto()    # Client demande des infos produit

    # États de négociation
    PRICE_PRESENTED = auto()    # Prix présenté, attente réaction
    NEGOTIATING = auto()        # En pleine négociation
    COUNTER_OFFER = auto()      # Bot fait une contre-offre
    FINAL_OFFER = auto()        # Dernier prix proposé

    # États de clôture positive
    DEAL_AGREED = auto()        # Accord sur le prix
    CHOOSING_DELIVERY = auto()  # Choix livraison/pickup
    COLLECTING_ADDRESS = auto() # Collecte adresse livraison
    PENDING_DELIVERY = auto()   # Attente livraison
    PENDING_PICKUP = auto()     # Attente récupération
    COMPLETED = auto()          # Transaction terminée

    # États de clôture négative
    OBJECTION_HANDLING = auto() # Gestion d'objection
    FRUSTRATED_CLIENT = auto()  # Client frustré - mode empathie
    COOLING_OFF = auto()        # Client veut réfléchir
    ENDED = auto()              # Conversation terminée


class ConversationEvent(Enum):
    """
    Événements qui déclenchent les transitions d'état.
    """
    # Événements client
    FIRST_MESSAGE = auto()
    PRICE_QUESTION = auto()
    PRICE_OFFER = auto()
    ACCEPT_OFFER = auto()
    REJECT_OFFER = auto()
    COUNTER_OFFER = auto()

    # Choix de livraison
    CHOOSE_DELIVERY = auto()
    CHOOSE_PICKUP = auto()
    PROVIDE_ADDRESS = auto()
    ASK_LOCATION = auto()

    # Émotions/Sentiments
    EXPRESS_FRUSTRATION = auto()
    EXPRESS_DOUBT = auto()
    EXPRESS_INTEREST = auto()

    # Objections
    OBJECTION_PRICE = auto()
    OBJECTION_QUALITY = auto()
    OBJECTION_TRUST = auto()
    OBJECTION_TIMING = auto()

    # Fin de conversation
    SAY_GOODBYE = auto()
    NO_RESPONSE = auto()
    TIMEOUT = auto()


@dataclass
class StateTransition:
    """Définit une transition d'état"""
    from_state: ConversationState
    event: ConversationEvent
    to_state: ConversationState
    condition: Optional[callable] = None  # Condition optionnelle


class ConversationFSM:
    """
    Machine à États Finis pour la gestion du flux de conversation.
    Inspirée des meilleures pratiques de dialog management.
    """

    # Définition des transitions
    TRANSITIONS: List[StateTransition] = [
        # === Transitions initiales ===
        StateTransition(ConversationState.GREETING, ConversationEvent.FIRST_MESSAGE, ConversationState.PRICE_PRESENTED),
        StateTransition(ConversationState.GREETING, ConversationEvent.PRICE_QUESTION, ConversationState.PRICE_PRESENTED),

        # === Négociation ===
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.PRICE_OFFER, ConversationState.NEGOTIATING),
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.ACCEPT_OFFER, ConversationState.DEAL_AGREED),
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.EXPRESS_INTEREST, ConversationState.PRICE_PRESENTED),

        StateTransition(ConversationState.NEGOTIATING, ConversationEvent.PRICE_OFFER, ConversationState.NEGOTIATING),
        StateTransition(ConversationState.NEGOTIATING, ConversationEvent.ACCEPT_OFFER, ConversationState.DEAL_AGREED),
        StateTransition(ConversationState.NEGOTIATING, ConversationEvent.COUNTER_OFFER, ConversationState.COUNTER_OFFER),

        StateTransition(ConversationState.COUNTER_OFFER, ConversationEvent.PRICE_OFFER, ConversationState.NEGOTIATING),
        StateTransition(ConversationState.COUNTER_OFFER, ConversationEvent.ACCEPT_OFFER, ConversationState.DEAL_AGREED),
        StateTransition(ConversationState.COUNTER_OFFER, ConversationEvent.REJECT_OFFER, ConversationState.FINAL_OFFER),

        StateTransition(ConversationState.FINAL_OFFER, ConversationEvent.ACCEPT_OFFER, ConversationState.DEAL_AGREED),
        StateTransition(ConversationState.FINAL_OFFER, ConversationEvent.REJECT_OFFER, ConversationState.ENDED),
        StateTransition(ConversationState.FINAL_OFFER, ConversationEvent.PRICE_OFFER, ConversationState.FINAL_OFFER),

        # === Clôture positive ===
        # Le client peut choisir pickup/delivery depuis N'IMPORTE QUEL état de négociation
        # (ex: "je passe récupérer" sans avoir dit "ok" d'abord = acceptation implicite)
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.PRICE_QUESTION, ConversationState.PRICE_PRESENTED),  # Question prix → rester actif
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.CHOOSE_PICKUP, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.ASK_LOCATION, ConversationState.PRICE_PRESENTED),  # Reste en PRICE_PRESENTED, envoie juste la location
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.CHOOSE_DELIVERY, ConversationState.COLLECTING_ADDRESS),
        StateTransition(ConversationState.NEGOTIATING, ConversationEvent.CHOOSE_PICKUP, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.NEGOTIATING, ConversationEvent.ASK_LOCATION, ConversationState.NEGOTIATING),       # Localisation ≠ vente
        StateTransition(ConversationState.NEGOTIATING, ConversationEvent.CHOOSE_DELIVERY, ConversationState.COLLECTING_ADDRESS),
        StateTransition(ConversationState.COUNTER_OFFER, ConversationEvent.CHOOSE_PICKUP, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.COUNTER_OFFER, ConversationEvent.ASK_LOCATION, ConversationState.COUNTER_OFFER),   # Localisation ≠ vente
        StateTransition(ConversationState.FINAL_OFFER, ConversationEvent.CHOOSE_PICKUP, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.FINAL_OFFER, ConversationEvent.ASK_LOCATION, ConversationState.FINAL_OFFER),       # Localisation ≠ vente

        StateTransition(ConversationState.DEAL_AGREED, ConversationEvent.CHOOSE_DELIVERY, ConversationState.COLLECTING_ADDRESS),
        StateTransition(ConversationState.DEAL_AGREED, ConversationEvent.CHOOSE_PICKUP, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.DEAL_AGREED, ConversationEvent.ASK_LOCATION, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.DEAL_AGREED, ConversationEvent.PROVIDE_ADDRESS, ConversationState.PENDING_DELIVERY),
        # Client continue de parler après accord - rester en DEAL_AGREED
        StateTransition(ConversationState.DEAL_AGREED, ConversationEvent.EXPRESS_INTEREST, ConversationState.DEAL_AGREED),
        StateTransition(ConversationState.DEAL_AGREED, ConversationEvent.PRICE_OFFER, ConversationState.DEAL_AGREED),
        StateTransition(ConversationState.DEAL_AGREED, ConversationEvent.ACCEPT_OFFER, ConversationState.DEAL_AGREED),
        StateTransition(ConversationState.DEAL_AGREED, ConversationEvent.EXPRESS_FRUSTRATION, ConversationState.DEAL_AGREED),
        StateTransition(ConversationState.DEAL_AGREED, ConversationEvent.OBJECTION_PRICE, ConversationState.DEAL_AGREED),
        StateTransition(ConversationState.DEAL_AGREED, ConversationEvent.FIRST_MESSAGE, ConversationState.DEAL_AGREED),

        StateTransition(ConversationState.COLLECTING_ADDRESS, ConversationEvent.PROVIDE_ADDRESS, ConversationState.PENDING_DELIVERY),
        StateTransition(ConversationState.COLLECTING_ADDRESS, ConversationEvent.EXPRESS_INTEREST, ConversationState.COLLECTING_ADDRESS),
        StateTransition(ConversationState.CHOOSING_DELIVERY, ConversationEvent.CHOOSE_DELIVERY, ConversationState.COLLECTING_ADDRESS),
        StateTransition(ConversationState.CHOOSING_DELIVERY, ConversationEvent.CHOOSE_PICKUP, ConversationState.PENDING_PICKUP),

        # === Gestion des objections ===
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.OBJECTION_PRICE, ConversationState.OBJECTION_HANDLING),
        StateTransition(ConversationState.NEGOTIATING, ConversationEvent.OBJECTION_PRICE, ConversationState.OBJECTION_HANDLING),
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.OBJECTION_QUALITY, ConversationState.OBJECTION_HANDLING),
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.OBJECTION_TRUST, ConversationState.OBJECTION_HANDLING),
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.OBJECTION_TIMING, ConversationState.COOLING_OFF),

        StateTransition(ConversationState.OBJECTION_HANDLING, ConversationEvent.PRICE_OFFER, ConversationState.NEGOTIATING),
        StateTransition(ConversationState.OBJECTION_HANDLING, ConversationEvent.ACCEPT_OFFER, ConversationState.DEAL_AGREED),
        StateTransition(ConversationState.OBJECTION_HANDLING, ConversationEvent.EXPRESS_INTEREST, ConversationState.NEGOTIATING),

        # === Client frustré ===
        StateTransition(ConversationState.NEGOTIATING, ConversationEvent.EXPRESS_FRUSTRATION, ConversationState.FRUSTRATED_CLIENT),
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.EXPRESS_FRUSTRATION, ConversationState.FRUSTRATED_CLIENT),
        StateTransition(ConversationState.COUNTER_OFFER, ConversationEvent.EXPRESS_FRUSTRATION, ConversationState.FRUSTRATED_CLIENT),

        StateTransition(ConversationState.FRUSTRATED_CLIENT, ConversationEvent.PRICE_OFFER, ConversationState.NEGOTIATING),
        StateTransition(ConversationState.FRUSTRATED_CLIENT, ConversationEvent.EXPRESS_INTEREST, ConversationState.NEGOTIATING),
        StateTransition(ConversationState.FRUSTRATED_CLIENT, ConversationEvent.SAY_GOODBYE, ConversationState.ENDED),

        # === Refroidissement ===
        StateTransition(ConversationState.COOLING_OFF, ConversationEvent.FIRST_MESSAGE, ConversationState.NEGOTIATING),
        StateTransition(ConversationState.COOLING_OFF, ConversationEvent.PRICE_OFFER, ConversationState.NEGOTIATING),

        # === Fin de conversation ===
        StateTransition(ConversationState.NEGOTIATING, ConversationEvent.SAY_GOODBYE, ConversationState.ENDED),
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.SAY_GOODBYE, ConversationState.ENDED),

        # === PENDING_PICKUP — conserver l'état pour tous messages entrants ===
        StateTransition(ConversationState.PENDING_PICKUP, ConversationEvent.EXPRESS_INTEREST, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.PENDING_PICKUP, ConversationEvent.FIRST_MESSAGE, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.PENDING_PICKUP, ConversationEvent.ACCEPT_OFFER, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.PENDING_PICKUP, ConversationEvent.PRICE_OFFER, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.PENDING_PICKUP, ConversationEvent.PRICE_QUESTION, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.PENDING_PICKUP, ConversationEvent.OBJECTION_PRICE, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.PENDING_PICKUP, ConversationEvent.CHOOSE_PICKUP, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.PENDING_PICKUP, ConversationEvent.ASK_LOCATION, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.PENDING_PICKUP, ConversationEvent.SAY_GOODBYE, ConversationState.ENDED),

        # === PENDING_DELIVERY — conserver l'état pour tous messages entrants ===
        StateTransition(ConversationState.PENDING_DELIVERY, ConversationEvent.EXPRESS_INTEREST, ConversationState.PENDING_DELIVERY),
        StateTransition(ConversationState.PENDING_DELIVERY, ConversationEvent.FIRST_MESSAGE, ConversationState.PENDING_DELIVERY),
        StateTransition(ConversationState.PENDING_DELIVERY, ConversationEvent.ACCEPT_OFFER, ConversationState.PENDING_DELIVERY),
        StateTransition(ConversationState.PENDING_DELIVERY, ConversationEvent.PRICE_OFFER, ConversationState.PENDING_DELIVERY),
        StateTransition(ConversationState.PENDING_DELIVERY, ConversationEvent.PRICE_QUESTION, ConversationState.PENDING_DELIVERY),
        StateTransition(ConversationState.PENDING_DELIVERY, ConversationEvent.ASK_LOCATION, ConversationState.PENDING_DELIVERY),
        StateTransition(ConversationState.PENDING_DELIVERY, ConversationEvent.SAY_GOODBYE, ConversationState.ENDED),

        # === ENDED — conversation terminée, ignorer tous messages ===
        StateTransition(ConversationState.ENDED, ConversationEvent.EXPRESS_INTEREST, ConversationState.ENDED),
        StateTransition(ConversationState.ENDED, ConversationEvent.FIRST_MESSAGE, ConversationState.ENDED),
        StateTransition(ConversationState.ENDED, ConversationEvent.ACCEPT_OFFER, ConversationState.ENDED),
        StateTransition(ConversationState.ENDED, ConversationEvent.PRICE_OFFER, ConversationState.ENDED),
        StateTransition(ConversationState.ENDED, ConversationEvent.PRICE_QUESTION, ConversationState.ENDED),
        StateTransition(ConversationState.ENDED, ConversationEvent.SAY_GOODBYE, ConversationState.ENDED),
        StateTransition(ConversationState.ENDED, ConversationEvent.ASK_LOCATION, ConversationState.ENDED),

        # === COMPLETED — terminé positivement, ignorer tous messages ===
        StateTransition(ConversationState.COMPLETED, ConversationEvent.EXPRESS_INTEREST, ConversationState.COMPLETED),
        StateTransition(ConversationState.COMPLETED, ConversationEvent.FIRST_MESSAGE, ConversationState.COMPLETED),
        StateTransition(ConversationState.COMPLETED, ConversationEvent.PRICE_OFFER, ConversationState.COMPLETED),
        StateTransition(ConversationState.COMPLETED, ConversationEvent.ACCEPT_OFFER, ConversationState.COMPLETED),
        StateTransition(ConversationState.COMPLETED, ConversationEvent.PRICE_QUESTION, ConversationState.COMPLETED),
        StateTransition(ConversationState.COMPLETED, ConversationEvent.SAY_GOODBYE, ConversationState.COMPLETED),
    ]

    def __init__(self, initial_state: ConversationState = ConversationState.GREETING):
        self.current_state = initial_state
        self._build_transition_map()

    def _build_transition_map(self):
        """Construit une map pour lookup rapide des transitions"""
        self.transition_map: Dict[Tuple[ConversationState, ConversationEvent], ConversationState] = {}
        for t in self.TRANSITIONS:
            key = (t.from_state, t.event)
            self.transition_map[key] = t.to_state

    def can_transition(self, event: ConversationEvent) -> bool:
        """Vérifie si une transition est possible"""
        return (self.current_state, event) in self.transition_map

    def transition(self, event: ConversationEvent) -> Optional[ConversationState]:
        """
        Effectue une transition si possible.
        Retourne le nouvel état ou None si transition impossible.
        """
        key = (self.current_state, event)
        if key in self.transition_map:
            old_state = self.current_state
            self.current_state = self.transition_map[key]
            logger.debug(f"FSM: {old_state.name} --[{event.name}]--> {self.current_state.name}")
            return self.current_state

        logger.warning(f"FSM: No transition from {self.current_state.name} with event {event.name}")
        return None

    def force_state(self, state: ConversationState):
        """Force un changement d'état (pour récupération)"""
        logger.info(f"FSM: Force state change to {state.name}")
        self.current_state = state


# =============================================================================
# PARTIE 2: MÉMOIRE ET CONTEXTE
# =============================================================================

@dataclass
class ConversationMemory:
    """
    Système de mémoire multi-niveaux inspiré de Mem0 et MemGPT.

    - short_term: Messages récents (buffer limité)
    - facts: Faits extraits de la conversation
    - summary: Résumé compressé de l'historique
    """
    # Mémoire court terme (derniers messages)
    short_term: List[Dict[str, Any]] = field(default_factory=list)
    max_short_term: int = 10

    # Faits extraits
    facts: Dict[str, Any] = field(default_factory=dict)

    # Résumé de conversation
    summary: str = ""

    # Métriques
    total_messages: int = 0
    client_messages: int = 0
    bot_messages: int = 0

    def add_message(self, content: str, is_from_client: bool, metadata: Dict = None):
        """Ajoute un message à la mémoire"""
        message = {
            "content": content,
            "is_from_client": is_from_client,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        self.short_term.append(message)
        self.total_messages += 1

        if is_from_client:
            self.client_messages += 1
        else:
            self.bot_messages += 1

        # Gestion de la limite (garder les N derniers)
        if len(self.short_term) > self.max_short_term:
            # Comprimer les anciens messages dans le résumé
            old_messages = self.short_term[:len(self.short_term) - self.max_short_term]
            self._compress_to_summary(old_messages)
            self.short_term = self.short_term[-self.max_short_term:]

    def _compress_to_summary(self, messages: List[Dict]):
        """Compresse les anciens messages en résumé"""
        if not messages:
            return

        # Simple compression: extraire les points clés
        key_points = []
        for msg in messages:
            if msg["is_from_client"]:
                # Extraire les offres de prix
                price_match = re.search(r'(\d+)\s*k', msg["content"].lower())
                if price_match:
                    key_points.append(f"Client a proposé {price_match.group(1)}K")

        if key_points:
            if self.summary:
                self.summary += " | " + " | ".join(key_points)
            else:
                self.summary = " | ".join(key_points)

    def set_fact(self, key: str, value: Any):
        """Enregistre un fait"""
        self.facts[key] = value
        logger.debug(f"Memory: Fact set [{key}] = {value}")

    def get_fact(self, key: str, default: Any = None) -> Any:
        """Récupère un fait"""
        return self.facts.get(key, default)

    def get_context_window(self) -> List[Dict]:
        """Retourne le contexte actuel pour l'IA"""
        return self.short_term.copy()

    def get_formatted_history(self) -> str:
        """Retourne l'historique formaté pour le prompt"""
        lines = []

        if self.summary:
            lines.append(f"[Résumé précédent: {self.summary}]")
            lines.append("")

        for msg in self.short_term:
            role = "Client" if msg["is_from_client"] else "Vendeur"
            lines.append(f"{role}: {msg['content']}")

        return "\n".join(lines)


# =============================================================================
# PARTIE 3: ANALYSE DE SENTIMENT ET ÉMOTIONS
# =============================================================================

class Emotion(Enum):
    """Émotions détectables dans les messages"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    INTERESTED = "interested"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"
    DOUBTFUL = "doubtful"
    IMPATIENT = "impatient"
    CONFUSED = "confused"


@dataclass
class SentimentAnalysis:
    """Résultat de l'analyse de sentiment"""
    emotion: Emotion
    confidence: float  # 0.0 à 1.0
    is_positive: bool
    is_negative: bool
    intensity: float  # 0.0 à 1.0 (faible à forte)

    # Indicateurs spécifiques
    has_insults: bool = False
    has_urgency: bool = False
    has_questions: bool = False

    # Mots-clés détectés
    detected_keywords: List[str] = field(default_factory=list)


class SentimentAnalyzer:
    """
    Analyseur de sentiment avancé pour le contexte commercial africain.
    Détecte les émotions, l'intensité et les signaux d'achat.
    """

    # Lexiques par catégorie
    POSITIVE_WORDS = {
        'ok', 'oui', 'bien', 'super', 'parfait', 'excellent', 'génial', 'genial',
        'merci', 'thanks', 'cool', 'nice', 'top', 'intéressé', 'interesse',
        'j\'aime', 'jaime', 'deal', 'marché', 'vendu', 'd\'accord', 'daccord',
        'ça marche', 'ca marche', 'je prends', 'je veux', 'envoi', 'envoie'
    }

    NEGATIVE_WORDS = {
        'non', 'pas', 'jamais', 'cher', 'trop', 'beaucoup', 'arnaque',
        'voleur', 'escroc', 'menteur', 'faux', 'nul', 'nulle', 'mauvais',
        'impossible', 'ridicule', 'abuse', 'abusé', 'exagère', 'exagéré'
    }

    FRUSTRATION_MARKERS = {
        'voleur', 'arnaqueur', 'arnaque', 'escroc', 'menteur', 'idiot',
        'imbécile', 'imbecile', 'con', 'fou', 'folle', 'dingue', 'malade',
        'merde', 'bordel', 'putain', 'n\'importe quoi', 'nimporte quoi',
        'tu rigoles', 'tu plaisantes', 'tu délires', 'tu abuses',
        'c\'est du vol', 'tu te moques', 'tu te fous de moi'
    }

    DOUBT_MARKERS = {
        'sûr', 'sur', 'certain', 'vrai', 'vraiment', 'original', 'authentique',
        'garanti', 'garantie', 'confiance', 'peur', 'méfiant', 'doute',
        'qualité', 'qualite', 'faux', 'copie', 'contrefaçon'
    }

    INTEREST_MARKERS = {
        'intéress', 'interesse', 'veux', 'veut', 'prend', 'achète', 'acheter',
        'combien', 'prix', 'dispo', 'disponible', 'livr', 'envoi', 'photo',
        'image', 'voir', 'couleur', 'taille', 'modèle', 'adresse', 'où'
    }

    URGENCY_MARKERS = {
        'vite', 'urgent', 'rapidement', 'maintenant', 'aujourd\'hui',
        'tout de suite', 'immédiatement', 'asap', 'pressé'
    }

    def analyze(self, message: str) -> SentimentAnalysis:
        """Analyse complète du sentiment d'un message"""
        msg_lower = message.lower()
        words = set(msg_lower.split())

        # Comptage des indicateurs
        positive_count = sum(1 for w in self.POSITIVE_WORDS if w in msg_lower)
        negative_count = sum(1 for w in self.NEGATIVE_WORDS if w in msg_lower)

        # Détection spécifique
        has_frustration = any(m in msg_lower for m in self.FRUSTRATION_MARKERS)
        has_doubt = any(m in msg_lower for m in self.DOUBT_MARKERS)
        has_interest = any(m in msg_lower for m in self.INTEREST_MARKERS)
        has_urgency = any(m in msg_lower for m in self.URGENCY_MARKERS)
        has_questions = '?' in message

        # Indicateurs de colère (MAJUSCULES, !!!, ???)
        uppercase_ratio = sum(1 for c in message if c.isupper()) / max(len(message), 1)
        exclamation_count = message.count('!')
        question_count = message.count('?')

        is_shouting = uppercase_ratio > 0.5 and len(message) > 10
        is_emphatic = exclamation_count >= 2 or question_count >= 3

        # Déterminer l'émotion principale
        emotion = self._determine_emotion(
            has_frustration, has_doubt, has_interest,
            positive_count, negative_count, is_shouting, is_emphatic
        )

        # Calculer l'intensité
        intensity = self._calculate_intensity(
            positive_count, negative_count, is_shouting, is_emphatic,
            has_frustration, exclamation_count
        )

        # Collecter les mots-clés détectés
        detected = []
        if has_frustration:
            detected.extend([m for m in self.FRUSTRATION_MARKERS if m in msg_lower])
        if has_doubt:
            detected.extend([m for m in self.DOUBT_MARKERS if m in msg_lower])
        if has_interest:
            detected.extend([m for m in self.INTEREST_MARKERS if m in msg_lower])

        return SentimentAnalysis(
            emotion=emotion,
            confidence=min(0.9, 0.5 + intensity * 0.4),
            is_positive=emotion in [Emotion.HAPPY, Emotion.INTERESTED],
            is_negative=emotion in [Emotion.ANGRY, Emotion.FRUSTRATED],
            intensity=intensity,
            has_insults=has_frustration,
            has_urgency=has_urgency,
            has_questions=has_questions,
            detected_keywords=detected[:5]  # Limiter à 5
        )

    def _determine_emotion(
        self, has_frustration: bool, has_doubt: bool, has_interest: bool,
        positive_count: int, negative_count: int,
        is_shouting: bool, is_emphatic: bool
    ) -> Emotion:
        """Détermine l'émotion principale"""

        # Priorité aux émotions fortes négatives
        if has_frustration and (is_shouting or is_emphatic):
            return Emotion.ANGRY
        if has_frustration:
            return Emotion.FRUSTRATED

        # Doute
        if has_doubt and negative_count > positive_count:
            return Emotion.DOUBTFUL

        # Impatience
        if is_emphatic and negative_count > 0:
            return Emotion.IMPATIENT

        # Émotions positives
        if has_interest:
            return Emotion.INTERESTED
        if positive_count > negative_count + 1:
            return Emotion.HAPPY

        # Confusion si beaucoup de questions
        if is_emphatic and has_doubt:
            return Emotion.CONFUSED

        return Emotion.NEUTRAL

    def _calculate_intensity(
        self, positive_count: int, negative_count: int,
        is_shouting: bool, is_emphatic: bool,
        has_frustration: bool, exclamation_count: int
    ) -> float:
        """Calcule l'intensité émotionnelle (0.0 à 1.0)"""
        intensity = 0.3  # Base

        if is_shouting:
            intensity += 0.3
        if is_emphatic:
            intensity += 0.2
        if has_frustration:
            intensity += 0.3

        intensity += min(0.1, exclamation_count * 0.03)
        intensity += min(0.1, (positive_count + negative_count) * 0.02)

        return min(1.0, intensity)


# =============================================================================
# PARTIE 4: EXTRACTION D'INTENTIONS
# =============================================================================

@dataclass
class Intent:
    """Intention détectée dans un message"""
    event: ConversationEvent
    confidence: float
    extracted_data: Dict[str, Any] = field(default_factory=dict)


class IntentExtractor:
    """
    Extracteur d'intentions sophistiqué.
    Analyse les messages pour déterminer l'intention du client.
    """

    def extract(self, message: str, context: ConversationMemory, current_state: ConversationState = None, merchant_data: Dict = None, last_bot_message: str = None, intent_history: List[str] = None) -> Intent:
        """Extrait l'intention principale du message"""
        msg_lower = self._normalize_message(message.lower())

        # -1. PRIORITÉ ABSOLUE: Le client conteste un achat prématurément déclaré
        # "j'ai rien acheté", "j'ai pas commandé", etc.
        if self._is_status_correction(msg_lower):
            return Intent(
                event=ConversationEvent.EXPRESS_FRUSTRATION,
                confidence=0.95,
                extracted_data={"status_correction": True}
            )

        # -0.5 GOODBYE HAUTE PRIORITÉ: dépasse localisation, objections et livraison
        # ι08: "au revoir et envoie la position quand même" → goodbye gagne (pas ASK_LOCATION)
        # ζ03: "ça dégage ici trop cher" → goodbye gagne (pas OBJECTION_PRICE)
        high_priority_goodbyes = ['au revoir', 'ca degage', 'je degage']
        if any(hpg in msg_lower for hpg in high_priority_goodbyes):
            return Intent(
                event=ConversationEvent.SAY_GOODBYE,
                confidence=0.9,
                extracted_data={}
            )

        # 0.2 CONTEXTE BOT: résolution d'intention basée sur la dernière action du bot
        # "bon" après une contre-offre → ACCEPT_OFFER et non EXPRESS_INTEREST
        # "pickup" après "livraison ou pickup ?" → CHOOSE_PICKUP
        if last_bot_message:
            context_intent = self._resolve_with_bot_context(msg_lower, last_bot_message)
            if context_intent:
                return context_intent

        # 0. PRIORITÉ MAXIMALE: Vérifier pickup/localisation AVANT l'acceptation
        # Car "oui oui mais je veux passer recuperer" n'est PAS une acceptation,
        # c'est un choix de pickup. Fonctionne depuis tout état de négociation.
        # MAIS PAS au premier message (le client explore, pas encore d'accord)
        negotiation_states = {
            ConversationState.DEAL_AGREED,
            ConversationState.PRICE_PRESENTED,
            ConversationState.NEGOTIATING,
            ConversationState.COUNTER_OFFER,
            ConversationState.FINAL_OFFER,
        }
        has_enough_context = context.total_messages > 1  # Pas au premier message
        # Pickup/delivery seulement après accord ou négociation avancée
        # Pas depuis PRICE_PRESENTED (le client n'a pas encore négocié)
        pickup_ready_states = {
            ConversationState.DEAL_AGREED,
            ConversationState.NEGOTIATING,
            ConversationState.COUNTER_OFFER,
            ConversationState.FINAL_OFFER,
        }
        if current_state in pickup_ready_states and has_enough_context:
            _money_words = ('sous', 'monnaie', 'argent', 'cash', 'billets')
            if (self._is_pickup_request(msg_lower) and
                    not any(mw in msg_lower for mw in _money_words)):
                return Intent(
                    event=ConversationEvent.CHOOSE_PICKUP,
                    confidence=0.95,
                    extracted_data={}
                )
            if self._is_location_request(msg_lower):
                return Intent(
                    event=ConversationEvent.ASK_LOCATION,
                    confidence=0.95,
                    extracted_data={}
                )
            delivery_result = self._check_delivery_request(msg_lower, context)
            if delivery_result:
                return delivery_result

        # 0b. Vérifier d'abord si c'est une objection ou frustration (priorité sur le prix)
        # Car "450K?? C'est cher!" n'est PAS une offre, c'est une objection
        has_objection_markers = any(m in msg_lower for m in [
            'cher', 'trop', 'beaucoup', '??', '?!', 'c\'est', 'quand même',
            'quand meme', 'vraiment', 'serieux', 'sérieux'
        ])

        # Contexte compétiteur : "j'ai vu à 24000 ailleurs" = objection, pas offre du client
        competitor_markers = [
            'ailleurs', 'concurrent', 'voisin', 'voisine',
            'on me propose', 'on m a propose', 'j ai vu', 'j ai eu une offre',
            'j ai une offre', 'quelqu un qui vend', 'quelqu un vend',
            'chez amazon', 'sur jumia', 'en ligne', 'en face',
            'le marchandeur', 'j ai mieux', 'j ai trouve moins',
        ]
        has_competitor_context = any(m in msg_lower for m in competitor_markers)

        # Si marqueurs d'objection OU contexte compétiteur + prix mentionné = c'est une objection
        price = self._extract_price(message)
        if price and (has_objection_markers or has_competitor_context):
            # C'est une objection sur le prix, pas une offre
            return Intent(
                event=ConversationEvent.OBJECTION_PRICE,
                confidence=0.85,
                extracted_data={"type": "price", "mentioned_price": price}
            )

        # 1. Extraction de prix comme offre réelle
        # L'offre doit être accompagnée de mots d'offre ou être seule
        if price:
            offer_markers = [
                'je fais', 'je propose', 'je donne', 'je mets', 'je paye',
                'je peux faire',  # δ07: "sans déconner je peux faire 15000"
                'mon offre', 'mon prix', 'maximum', 'dernier prix',
                'ok pour', 'd\'accord pour', 'ca te va', 'ça te va',
                'on dit', 'on fait', 'deal a', 'deal à'
            ]
            is_clear_offer = any(m in msg_lower for m in offer_markers)
            # Un prix seul (message court) est aussi considéré comme une offre
            is_short_price_message = len(message.strip()) < 30

            if is_clear_offer or is_short_price_message:
                return Intent(
                    event=ConversationEvent.PRICE_OFFER,
                    confidence=0.95,
                    extracted_data={"price": price}
                )

        # 1.5 Demande de localisation — AVANT visit_intent et acceptation
        # "Oui envoie", "envoie la position" contiennent "oui" qui matcherait l'acceptation
        # "je veux passer", "je viens demain" → implicitement besoin de la localisation
        # Note: localisation toujours détectable, même au 1er message
        if self._is_location_request(msg_lower):
            # 1.5b Vérifier si le client mentionne un MAUVAIS emplacement
            # Ex: "Vous êtes à Koumassi ?" alors que le magasin est à Bassam
            if merchant_data and '?' in message:
                correct_address = self._is_wrong_location_question(msg_lower, merchant_data)
                if correct_address:
                    return Intent(
                        event=ConversationEvent.ASK_LOCATION,
                        confidence=0.95,
                        extracted_data={"wrong_location": True, "correct_address": correct_address}
                    )
            return Intent(
                event=ConversationEvent.ASK_LOCATION,
                confidence=0.9,
                extracted_data={}
            )

        # 1.6 Intention de visite (APRÈS localisation, AVANT acceptation)
        # "je veux passer à la boutique" contient "je veux" qui serait détecté comme acceptation
        # Note: les messages avec localisation implicite ('je viens demain') sont déjà
        # capturés ci-dessus par _is_location_request
        is_early_stage = not has_enough_context or current_state == ConversationState.PRICE_PRESENTED
        if is_early_stage and self._is_visit_intent(msg_lower):
            return Intent(
                event=ConversationEvent.EXPRESS_INTEREST,
                confidence=0.85,
                extracted_data={"visit_intent": True}
            )

        # 2. Acceptation (pas au premier message — "je veux" n'est pas une acceptation)
        if self._is_acceptance(msg_lower) and has_enough_context:
            return Intent(
                event=ConversationEvent.ACCEPT_OFFER,
                confidence=0.9,
                extracted_data={}
            )

        # 3. Demande de livraison (avec contexte, pas au 1er message)
        if has_enough_context:
            delivery_result = self._check_delivery_request(msg_lower, context)
            if delivery_result:
                return delivery_result

        # 4. Demande de pickup/localisation (pas au 1er message)
        _money_words2 = ('sous', 'monnaie', 'argent', 'cash', 'billets')
        if (has_enough_context and self._is_pickup_request(msg_lower) and
                not any(mw in msg_lower for mw in _money_words2)):
            return Intent(
                event=ConversationEvent.CHOOSE_PICKUP,
                confidence=0.85,
                extracted_data={}
            )

        if self._is_location_request(msg_lower):
            return Intent(
                event=ConversationEvent.ASK_LOCATION,
                confidence=0.85,
                extracted_data={}
            )

        # 5. Fourniture d'adresse
        address = self._extract_address(message)
        if address:
            return Intent(
                event=ConversationEvent.PROVIDE_ADDRESS,
                confidence=0.8,
                extracted_data={"address": address}
            )

        # 6. Objections
        objection = self._detect_objection(msg_lower)
        if objection:
            return objection

        # 7. Frustration
        if self._is_frustrated(msg_lower, message):
            return Intent(
                event=ConversationEvent.EXPRESS_FRUSTRATION,
                confidence=0.85,
                extracted_data={}
            )

        # 8. Fin de conversation
        if self._is_goodbye(msg_lower):
            return Intent(
                event=ConversationEvent.SAY_GOODBYE,
                confidence=0.8,
                extracted_data={}
            )

        # 9. Question sur le prix
        if self._is_price_question(msg_lower):
            return Intent(
                event=ConversationEvent.PRICE_QUESTION,
                confidence=0.8,
                extracted_data={}
            )

        # 9.5 Question d'horaires (jamais inventés par le bot)
        if self._is_hours_question(msg_lower):
            return Intent(
                event=ConversationEvent.EXPRESS_INTEREST,
                confidence=0.8,
                extracted_data={"hours_question": True}
            )

        # 10. Expression d'intérêt (défaut si message court)
        if len(message) < 50 or self._shows_interest(msg_lower):
            return Intent(
                event=ConversationEvent.EXPRESS_INTEREST,
                confidence=0.6,
                extracted_data={}
            )

        # 10.5 BOOST SÉQUENCE: si le client répète un pattern → amplifier la confiance
        # Le bot analyse les 3-4 dernières intentions du client pour briser l'ambiguïté
        if intent_history and len(msg_lower.strip()) < 50:
            last = intent_history[-2:] if len(intent_history) >= 2 else intent_history

            # Pattern: client qui a enchaîné des objections de prix → prochain message négatif = au revoir
            if (last.count('OBJECTION_PRICE') >= 2 and
                    any(neg in msg_lower for neg in ['non', 'nan', 'pas', 'jamais', 'laisse', 'oublie', 'finalement'])):
                return Intent(
                    event=ConversationEvent.SAY_GOODBYE,
                    confidence=0.72,
                    extracted_data={"history_boosted": True}
                )

            # Pattern: client qui a fait 2+ offres consécutives → message avec prix = nouvelle offre (pas objection)
            if last.count('PRICE_OFFER') >= 2:
                boosted_price = self._extract_price(message)
                if boosted_price:
                    return Intent(
                        event=ConversationEvent.PRICE_OFFER,
                        confidence=0.92,
                        extracted_data={"price": boosted_price, "history_boosted": True}
                    )

            # Pattern: client qui a accepté puis pose une question → rester en accord, pas re-négociation
            if 'ACCEPT_OFFER' in last and current_state == ConversationState.DEAL_AGREED:
                return Intent(
                    event=ConversationEvent.EXPRESS_INTEREST,
                    confidence=0.75,
                    extracted_data={"post_deal_followup": True}
                )

        # Défaut: premier message ou intérêt général
        return Intent(
            event=ConversationEvent.FIRST_MESSAGE,
            confidence=0.5,
            extracted_data={}
        )

    def _resolve_with_bot_context(self, msg_lower: str, last_bot_message: str) -> Optional[Intent]:
        """
        Résout les intentions ambiguës grâce au contexte du dernier message du bot.

        Exemples concrets:
        - Bot: "Je te propose 16 000 F, ça te va ?" → Client: "ok" → ACCEPT_OFFER
        - Bot: "Livraison ou pickup ?" → Client: "pickup" / "je passe" → CHOOSE_PICKUP
        - Bot: "Ton adresse ?" → Client: "Cocody Angré" → PROVIDE_ADDRESS
        """
        bot_lower = last_bot_message.lower()
        msg_stripped = msg_lower.strip().rstrip('?.! ')

        # Petits mots de confirmation (positifs courts)
        short_confirmations = {
            'ok', 'bon', 'bien', 'd accord', 'daccord', 'ça marche', 'ca marche',
            'ok ok', 'oui', 'ouais', 'weh', 'yep', 'parfait', 'super', 'top',
            'yes', 'marche', 'cool', 'nickel', 'ça le fait', 'ca le fait',
            'deal', 'accord', 'dja', 'on dit quoi', 'on dit',
        }
        negative_words = {'non', 'nan', 'nah', 'trop', 'cher', 'pas', 'jamais', 'impossible'}
        is_short_positive = (
            msg_stripped in short_confirmations or
            len(msg_lower.strip()) <= 12
        ) and not any(neg in msg_lower for neg in negative_words)

        # --- Pattern 1: Bot vient de faire une contre-offre → court oui = ACCEPT_OFFER ---
        counter_offer_signals = [
            'je te propose', 'pour toi je fais', 'je peux faire', 'je descends à',
            'je baisse à', 'je t\'offre', 'dernier prix', 'prix spécial', 'prix special',
            'pour toi,', 'pour toi.', 'tu veux bien', 'ça te va', 'ca te va',
            'je te fais', 'je vous propose', 'on peut faire',
        ]
        if is_short_positive and any(sig in bot_lower for sig in counter_offer_signals):
            return Intent(
                event=ConversationEvent.ACCEPT_OFFER,
                confidence=0.82,
                extracted_data={"context_resolved": True, "ctx": "after_counter_offer"}
            )

        # --- Pattern 1.5: Bot a posé une question d'information (pas une contre-offre) ---
        # "Tu veux plus de détails ?" + "oui oui" → EXPRESS_INTEREST (info demandée, pas accord d'achat)
        # CRITIQUE: sans ça, "oui" après une question info = faux deal déclaré
        info_question_signals = [
            'plus de details', 'plus d info', 'plus d infos', 'plus d information',
            'tu veux savoir', 'je t explique', 'tu veux que j', "t'en dire plus",
            'te dire plus', 'te donner plus', 'te montrer', 'voir des photos',
            'tu veux voir', 'je peux t expliquer', 'je peux expliquer',
            'tu veux des photos', 'tu veux la description',
        ]
        if is_short_positive and any(sig in bot_lower for sig in info_question_signals):
            return Intent(
                event=ConversationEvent.EXPRESS_INTEREST,
                confidence=0.80,
                extracted_data={"context_resolved": True, "ctx": "after_info_question"}
            )

        # --- Pattern 2: Bot a demandé le choix livraison/pickup ---
        # IMPORTANT: exclure les questions ("vous livrez?") — c'est une question, pas un choix
        delivery_choice_signals = [
            'livraison ou', 'pickup ou livraison', 'livrer ou', 'récupérer ou',
            'recuperer ou', 'je te livre ou', 'tu préfères', 'tu preferes',
            'livraison ou pickup', 'pickup ou',
        ]
        is_question = '?' in msg_lower
        if not is_question and any(sig in bot_lower for sig in delivery_choice_signals):
            pickup_words = [
                'pickup', 'je passe', 'je viens', 'je recupere', 'je récupère',
                'retrait', 'boutique', 'magasin', 'recuperer', 'récupérer', 'je passe chercher',
            ]
            delivery_words = [
                'livraison', 'livre moi', 'livre-moi', 'chez moi',
                'à domicile', 'a domicile',
            ]
            if any(pw in msg_lower for pw in pickup_words):
                return Intent(
                    event=ConversationEvent.CHOOSE_PICKUP,
                    confidence=0.88,
                    extracted_data={"context_resolved": True, "ctx": "after_delivery_question"}
                )
            if any(dw in msg_lower for dw in delivery_words):
                return Intent(
                    event=ConversationEvent.CHOOSE_DELIVERY,
                    confidence=0.88,
                    extracted_data={"context_resolved": True, "ctx": "after_delivery_question"}
                )

        # --- Pattern 3: Bot a demandé l'adresse de livraison ---
        address_request_signals = [
            'ton adresse', 'votre adresse', 'tu habites', 'tu es situé',
            'tu te trouves', 'tu livres où', 'adresse de livraison', 'livraison c est où',
            'quartier', 'zone de livraison',
        ]
        if any(sig in bot_lower for sig in address_request_signals):
            quartiers = [
                'cocody', 'yopougon', 'abobo', 'adjamé', 'adjame', 'plateau',
                'koumassi', 'marcory', 'treichville', 'attécoubé', 'attecoube',
                'port bouet', 'bassam', 'bingerville', 'angré', 'angre',
                'riviera', 'deux plateaux', '2 plateaux', 'williamsville',
            ]
            if any(q in msg_lower for q in quartiers):
                return Intent(
                    event=ConversationEvent.PROVIDE_ADDRESS,
                    confidence=0.88,
                    extracted_data={"context_resolved": True, "ctx": "after_address_request"}
                )

        return None

    def _normalize_message(self, msg: str) -> str:
        """
        Normalise le message pour mieux comprendre:
        - Fautes de frappe courantes
        - Abréviations WhatsApp
        - Expressions nouchi/ivoiriennes
        - Raccourcis numériques
        """
        # PRIORITÉ 0: Normaliser apostrophes et accents EN PREMIER
        # pour que le nouchi_map et les patterns matchent les formes ASCII
        # Ex: 'solder ça' → 'solder ca' → matche 'solder ca' dans nouchi_map
        msg = msg.replace('\u2019', ' ').replace('\u2018', ' ').replace("'", ' ')
        try:
            msg_nfd = unicodedata.normalize('NFD', msg)
            msg = ''.join(c for c in msg_nfd if unicodedata.category(c) != 'Mn')
        except Exception:
            pass

        # Abréviations WhatsApp → forme complète
        abbreviations = {
            'svp': 's il vous plait',
            'stp': 's il te plait',
            'pk': 'pourquoi',
            'pr': 'pour',
            'bcp': 'beaucoup',
            'tjrs': 'toujours',
            'tt': 'tout',
            'mnt': 'maintenant',
            'mtn': 'maintenant',
            'pcq': 'parce que',
            'jsp': 'je sais pas',
            'jpp': 'j en peux plus',
            'lol': '',
            'bjr': 'bonjour',
            'bsr': 'bonsoir',
            'slt': 'salut',
            'nn': 'non',
            'mm': 'meme',
            'ac': 'avec',
            'ss': 'sans',
            'pb': 'probleme',
            'rdv': 'rendez vous',
            'cmt': 'comment',
            'koi': 'quoi',
            'kan': 'quand',
            'ki': 'qui',
            'ya': 'il y a',
            # Abréviations africaines fréquentes
            'dispo': 'disponible',
            'livr': 'livraison',
            'qd': 'quand',
            'dc': 'donc',
            'stp': 's il te plait',
            'pq': 'pourquoi',
            'biz': 'bisous',
            'wsh': 'bonjour',       # verlan familier
            'frr': 'frere',
            'frero': 'frere',
            'gros': 'ami',
            'chef': 'vendeur',      # "chef c est combien" = ivoirien/sénégalais
            'patron': 'vendeur',
            'boss': 'vendeur',
        }
        for abbr, full in abbreviations.items():
            msg = re.sub(r'\b' + abbr + r'\b', full, msg)

        # Expressions nouchi/ivoiriennes → intention équivalente
        nouchi_map = {
            # ── Expressions complexes AVANT les mots simples (ordre critique) ──
            'wari yeke obe': 'combien',  # dioula: "combien ça coûte" (AVANT 'wari')
            'combien c est': 'combien',
            'c est combien du coup': 'combien',
            'ca fait combien': 'combien',
            'ca coute combien': 'combien',

            # ── Acceptation / achat ──
            'wari': 'argent',
            'dja': 'accord',
            'djaa': 'accord',
            'on se comprend': 'accord',
            'on dit quoi': 'accord',
            'c est dit': 'accord',          # CI: "c'est dit" = deal (sans apostrophe)
            'c est regle': 'accord',        # CI: "c'est réglé" = deal
            'c est plie': 'accord',         # CI: "c'est plié" = deal
            'c est scelle': 'accord',       # CI: "c'est scellé" = deal
            'on est bon': 'accord',         # CI: on s'est mis d'accord
            'on est d accord': 'accord',    # CI: idem
            'ca tombe': 'accord',           # CI: ça tombe = deal
            'ca chute': 'accord',           # CI: ça chute = deal
            'je ramasse': 'je le prends',   # CI: je ramasse = je prends
            'ca passe': 'accord',           # CI: ça passe = deal
            'ca coule': 'accord',           # CI: ça coule = deal
            'na djeu': 'accord',            # CI: na djeu = deal
            'on se met': 'accord',          # CI: on se met d'accord
            'ca coupe': 'accord',           # CI: ça coupe = deal
            'solder ca': 'je le prends',    # CI: solder ça = acheter
            'deal on dit': 'accord',
            'on fait comment': 'comment on fait',
            'c est comment': 'c est combien',
            'c\'est comment': 'c est combien',
            'c comment': 'c est combien',
            'hein': '',                      # particule vide
            'oo': 'oui',
            'weh': 'oui',                   # AVANT 'we'
            'wê': 'oui',
            'we': 'oui',
            'ehen': 'oui',                  # CI/béninois: oui marqué
            'eeh': 'oui',
            'nan': 'non',
            'nah': 'non',
            'nope': 'non',
            'laisses tomber': 'annuler',
            'laisse tomber': 'annuler',
            'laisse': 'annuler',
            'j abandonne': 'annuler',
            'oublie': 'annuler',            # "oublie ça" = annuler
            'oublie ca': 'annuler',

            # ── Prix / négociation ──
            'je cherche pas': 'c est trop cher',
            'c est cho': 'c est cher',
            'c\'est cho': 'c est cher',
            'c cho': 'c est cher',
            'cho': 'cher',
            'c est pas possible': 'c est trop cher',
            'trop fort': 'trop cher',
            'fort trop': 'trop cher',
            'gonfle': 'cher',
            'gonflé': 'cher',
            'salé': 'cher',                 # "c'est salé" = c'est cher
            'sale': 'cher',
            'exagere': 'trop cher',
            'exagéré': 'trop cher',
            'djara': 'prix',                # dioula: "prix" → aide extract_price
            'ka doni': 'combien',           # bambara: "combien ça coûte"

            # ── Localisation ──
            # Note: 'c est ou', 'vous etes ou' RETIRÉS du nouchi_map car ils matchent
            # en sous-chaîne 'c est ouvert', 'vous etes ouverts' → faux positifs localisation
            # Ces patterns sont désormais gérés par regex word-boundary dans _is_location_request
            'vous etes a': 'vous êtes à',
            'vous situez': 'vous êtes situé',
            'votre plan': 'votre adresse',  # "envoie ton plan" = envoie la localisation
            'envoie le plan': 'envoie la localisation',
            'envoie ton plan': 'envoie la localisation',
            'la position': 'la localisation',

            # ── Désignation d'un produit ──
            'lui la': 'je veux celui-la',
            'lui là': 'je veux celui-la',
            'elle la': 'je veux celle-la',
            'elle là': 'je veux celle-la',
            'celui la': 'je veux celui-la',
            'celle la': 'je veux celle-la',
            'le truc la': 'l article',
            'le machin la': 'l article',

            # ── Qualité / confiance ──
            'c est quoi comme qualite': 'quelle est la qualite',
            'c est original': 'c est authentique',
            'c est fake': 'c est faux',
            'c est genuine': 'c est authentique',

            # ── Divers particules / réactions ──
            'au revoir hein': 'au revoir',
            'merci hein': 'merci',
            'je kiffe': 'j aime',
            'kiffe': 'aime',
            'waw': 'super',
            'waow': 'super',
            'OMG': 'super',
            'lol': '',
            'mdr': '',
            'xd': '',
            'ahah': '',
            'haha': '',
        }
        for nouchi, french in nouchi_map.items():
            if nouchi in msg:
                msg = msg.replace(nouchi, french)

        # Fautes de frappe courantes
        typos = {
            'combient': 'combien',
            'dispobible': 'disponible',
            'disponnible': 'disponible',
            'dispoble': 'disponible',
            'disponble': 'disponible',
            'lvirasion': 'livraison',
            'livrason': 'livraison',
            'boutque': 'boutique',
            'boutiqe': 'boutique',
            'magsin': 'magasin',
            'magasen': 'magasin',
            'adrese': 'adresse',
            'adrsse': 'adresse',
            'qualitee': 'qualite',
            'qualité': 'qualite',
            'j\'veux': 'je veux',
            'j\'prends': 'je prends',
            'j\'peux': 'je peux',
            'j\'ai': 'j ai',
        }
        for typo, correct in typos.items():
            msg = msg.replace(typo, correct)

        return msg

    def _extract_price(self, message: str) -> Optional[float]:
        """Extrait un prix du message"""
        msg = message.lower()

        # Pattern "450k" ou "450K"
        k_match = re.search(r'(\d+)\s*k\b', msg)
        if k_match:
            return float(k_match.group(1)) * 1000

        # Pattern "450 000" avec espaces
        space_match = re.search(r'(\d{1,3}(?:\s\d{3})+)', msg)
        if space_match:
            return float(space_match.group(1).replace(' ', ''))

        # Pattern "450000" simple (4+ chiffres)
        simple_match = re.search(r'\b(\d{4,})\b', msg)
        if simple_match:
            return float(simple_match.group(1))

        return None

    def _is_acceptance(self, msg: str) -> bool:
        """Détecte si le client accepte — français + nouchi + abréviations"""
        exact_accepts = [
            # Français standard
            'ok', 'oui', 'deal', 'vendu', 'marche', 'adjuge',
            'd accord', 'daccord', 'je le prends', 'je la prends', 'je les prends',
            # Note: 'je prends' et 'je veux' seuls → for-phrase loop (avec exclusions)
            'ca marche', 'c est bon', 'parfait', 'top', 'impec',
            'on fait comme ca', 'je suis d accord', 'je valide',
            'je le veux', 'je la veux', 'c est deal',
            'je suis partant', 'je suis partante', 'banco',
            # Accord après négociation
            'c est pris', 'va pour ca', 'ca ira', 'on y va', 'allez',
            'ca roule', 'c est valide', 'c est ok', 'c est pour moi', 'regle',
            'ca me va', 'ca me convient', 'me convient',
            # Nouchi / ivoirien courant
            'dja', 'djaa', 'on se comprend', 'on dit quoi', 'accord',
            'we', 'oo',
            # Nouchi / ivoirien avancé
            'na djeu', 'on se met', 'ca coupe', 'finit', 'c bon', 'c clair',
            'on est bon', 'ca tombe', 'ca chute', 'je ramasse', 'ca passe', 'ca coule',
            'c est plie', 'c est scelle', 'c est regle',
            'on est d accord', 'c est dit',
            # Anglais / franglais courant
            'yes', 'yep', 'yop', 'agreed', 'done', 'let s go', 'go',
            'let s do it', 'i ll take it', 'sold', 'confirmed',
            # Paiement imminent (accord implicite)
            'je viens avec les sous', 'je viens avec la monnaie', 'je viens avec l argent',
            'je ramene les sous', 'j amene les sous', 'avec les sous', 'avec la monnaie',
            # Décisions finales / commandes explicites
            'c est fait', 'j achete', 'je veux acheter', 'je veux commander',
            'j ai decide de prendre', 'j ai pris ma decision',
            'je passe commande', 'je fais l achat', 'ma commande',
        ]

        # Phrases annulant l'accord ("ok mais trop cher" ≠ accord, "deal si tu baisses" ≠ accord)
        retraction_phrases = [
            'mais non', 'trop cher', 'j ai change d avis', 'change d avis',
            'pour une autre fois', 'si tu baisses', 'si la qualite',
            'mais quand meme', 'pas sur',
            # Annulations explicites
            'annuler', 'bye', 'j abandonne',
            # Négation explicite dans le message (ex: "deal deal deal (non)")
            '(non)',
            # Abandon vers la concurrence ("c'est bon j'ai trouvé ailleurs")
            'trouve ailleurs', 'j ai trouve ailleurs', 'j ai trouve mieux',
            'achete ailleurs', 'commande ailleurs', 'moins cher ailleurs',
        ]

        msg_stripped = msg.strip()
        # Supprimer ponctuation terminale: "go!" → "go", "banco!" → "banco"
        msg_stripped_clean = msg_stripped.rstrip('!?.,:;…')

        # Message court d'acceptation exacte (jamais si c'est une question)
        if msg_stripped_clean in exact_accepts and '?' not in msg_stripped:
            return True

        # "pas sur" n'est pas une rétractation si un prix est présent dans le message
        # Ex: "ok 14000 mais je suis pas encore 100%" → prix auto-accepté, hésitation ignorée
        has_price_in_msg = bool(self._extract_price(msg))
        effective_retractions = retraction_phrases if not has_price_in_msg else [
            r for r in retraction_phrases if r != 'pas sur'
        ]

        # Indicateur: le message est une question (ex: "ok c'est combien?" ≠ accord)
        is_question_msg = '?' in msg_stripped

        # Mots indiquant une hésitation ou un compliment (non-achat) après un mot d'acceptation
        hesitation_starters = (
            'mais', 'merci', 'vois', 'je vois', 'je verrai', 'voir', 'reflechir',
            'vais reflechir', 'et si', 'si jamais', 'je pense', 'je vais voir',
            # Délais et report
            'a demain', 'plus tard', 'bonne journee', 'on verra', 'j attends',
            'reviens', 'je reviens', 'ok ok',
            # Effort / négociation (pour "allez fais un geste")
            'geste', 'effort', 'un geste', 'petit effort',
        )
        # Noms qui transforment "top/parfait" en compliment (pas achat)
        compliment_nouns = ('produit', 'article', 'truc', 'comme', 'qualite', 'affaire', 'machin')

        # Phrases d'acceptation au début du message
        for accept in exact_accepts:
            if msg_stripped_clean.startswith(accept + ' ') or msg_stripped_clean.startswith(accept + ','):
                # "ok mais c'est cher?" n'est pas une acceptation
                if is_question_msg:
                    continue
                # Vérifier si suivi d'une hésitation ("ok je vois", "ok merci", "ok je vais réfléchir")
                rest = msg_stripped_clean[len(accept):].strip().lstrip(',').strip()
                if any(rest == hw or hw in rest for hw in hesitation_starters):
                    continue
                # "top produit", "parfait comme produit" → compliment, pas achat
                if accept in ('top', 'parfait', 'super', 'excellent') and rest:
                    if any(cn in rest for cn in compliment_nouns):
                        continue
                # Négation directe après le mot d'acceptation ("j'achète pas ça", "ok plus")
                if rest and rest.split()[0] in ('pas', 'plus', 'jamais', 'non', 'no', 'nah', 'nan', 'nope'):
                    continue
                # Vérifier l'absence de rétractation ("ok mais trop cher" ≠ accord)
                if not any(r in msg_stripped_clean for r in effective_retractions):
                    return True

        # Phrases d'acceptation à la FIN du message (accord tardif)
        # Ex: "non c'est bon je le prends", "pas de problème banco"
        _negations = ('pas', 'non', 'jamais', 'plus', 'nah', 'nan', 'nope', 'no')
        for accept in exact_accepts:
            if msg_stripped_clean.endswith(' ' + accept):
                # "c'est quoi ce deal?" n'est pas une acceptation
                if is_question_msg:
                    continue
                # Vérifier qu'il n'y a pas de négation directe avant le mot d'acceptation
                prefix = msg_stripped_clean[:-(len(accept) + 1)].strip()
                if any(prefix == neg or prefix.endswith(' ' + neg) for neg in _negations):
                    continue
                # Répétition du même mot = hésitation ("ok ok ok", "deal deal deal")
                if prefix.endswith(' ' + accept) or prefix == accept:
                    continue
                if not any(r in msg_stripped_clean for r in effective_retractions):
                    return True

        # "je prends" ou "je veux" sans négation ni exclusion
        # Note: 'plus' est une négation implicite ("je veux plus ça" = "je ne veux plus ça")
        for phrase in ['je prends', 'je veux']:
            if phrase in msg and 'pas' not in msg and 'ne ' not in msg and 'plus' not in msg:
                exclusions = ['soin', 'note', 'noter', 'en compte', 'le temps', 'savoir',
                              'dire', 'passer', 'voir', 'connaitre', 'regarder', 'visiter',
                              # Quantités → négociation sur le nombre, pas encore accord
                              'paquets', 'paquet', 'kilo', 'kg', 'piece', 'pieces', 'unites',
                              'carton', 'cartons', 'douzaine', 'dizaine']
                if not any(excl in msg for excl in exclusions):
                    return True

        # "c'est good/cool/parfait" → acceptation
        if any(p in msg for p in ['c est good', 'c est cool', 'c est top', 'impeccable', 'nickel', 'impec']):
            return True

        return False

    def _check_delivery_request(self, msg: str, context: ConversationMemory) -> Optional[Intent]:
        """
        Détecte une demande de livraison EN CONTEXTE.
        Évite les faux positifs (plaintes, questions sur le prix de livraison).
        """
        # Contextes négatifs - ce n'est PAS une demande
        negative_contexts = [
            'pas de livraison', 'sans livraison', 'livraison?', 'livraison ?',
            'combien la livraison', 'prix de la livraison', 'frais de livraison',
            'coût de livraison', 'cout de livraison', 'cher', 'trop',
            'voleur', 'arnaque', 'abuse', 'abusé', 'exagère'
        ]

        if any(neg in msg for neg in negative_contexts):
            return None

        # Question sur la livraison (pas une demande)
        if '?' in msg and 'livr' in msg:
            return None

        # Demandes affirmatives
        # Note: svp/stp normalisés en "s il vous/te plait" → inclure les deux formes
        delivery_requests = [
            'je veux la livraison',
            'livraison svp', 'livraison stp',
            'livraison s il vous plait', 'livraison s il te plait',
            'livre-moi', 'livrez-moi', 'livrer chez moi', 'livraison chez moi',
            'je préfère la livraison', 'je prefere la livraison',
            'oui livraison', 'ok livraison', 'avec livraison',
            'fais-moi livrer', 'fais moi livrer', 'pour la livraison'
        ]

        if any(req in msg for req in delivery_requests):
            return Intent(
                event=ConversationEvent.CHOOSE_DELIVERY,
                confidence=0.9,
                extracted_data={}
            )

        return None

    def _is_pickup_request(self, msg: str) -> bool:
        """Détecte une demande de pickup — français + nouchi"""
        pickup_keywords = [
            # Français standard
            'je viens', 'je passe', 'passer chercher', 'viens chercher',
            'recuperer', 'sur place', 'en personne',
            'moi meme', 'je me deplace', 'je viens chercher',
            'je viendrai', 'je passerai', 'je vais passer',
            'retrait', 'enlever moi meme', 'venir chercher',
            # Nouchi / ivoirien
            'je viens ramasser', 'je viens prendre', 'je passe prendre',
            'je viens voir', 'on se voit', 'on se retrouve',
            # Expressions courantes
            'je me deplace', 'je viens a la boutique', 'je viens au magasin',
            'je vais venir', 'je compte venir', 'je peux venir',
        ]
        # Exclure toutes les questions (pickup = engagement, pas question)
        if '?' in msg:
            return False
        # Exclure les messages avec argent → c'est une acceptation de paiement, pas juste pickup
        if any(mw in msg for mw in ['sous', 'monnaie', 'argent', 'cash', 'billets']):
            return False
        # Exclure "je vais passer commande" (= passer une commande ≠ venir chercher)
        if 'commande' in msg:
            return False
        return any(kw in msg for kw in pickup_keywords)

    def _is_location_request(self, msg: str) -> bool:
        """Détecte une demande de localisation du magasin — français + nouchi + anglais"""
        # EXCLUSION PRIORITAIRE: Questions d'horaires (avant toute autre vérification)
        # "c'est ouvert maintenant?", "la boutique ouvre quand?" ≠ demande de localisation
        hours_markers = ('ouvert', 'ouvre', 'ferme', 'horaire', 'ouverts', 'ouverte',
                         'ouverture', 'fermeture')
        if '?' in msg and any(h in msg for h in hours_markers):
            return False

        # Phrases explicites de demande d'adresse
        explicit_location = [
            # Français (accent-normalisé par le normalizer)
            # Note: 'c est ou', 'vous etes ou', 'tu es ou' → vérification word-boundary ci-dessous
            'ou se trouve', 'ou est le magasin', 'ou est la boutique',
            'adresse du magasin', 'localisation', 'position du magasin',
            'position de la boutique', 'envoie la position',
            'envoie moi la position', 'la position', 'avoir la position',
            'ou je peux venir', 'je viens ou', 'comment venir', 'comment je viens',
            'comment on peut venir', 'comment on vient',
            'situe ou', 'situer',
            # Visites implicites → besoin de l'adresse
            'je veux passer', 'je veux venir',
            'je viens demain', 'je passerai demain', 'je viendrai demain',
            'je passe demain', 'je viens ce soir', 'je viens ce matin',
            'je passerai vous voir', 'je viens vous voir', 'je passe vous voir',
            'je veux passer prendre', 'je passerai prendre', 'je viendrai prendre',
            # Demandes d'adresse directe
            'l adresse', 'quelle adresse', 'adresse stp', 'adresse svp',
            'adresse s il vous plait', 'adresse s il te plait',
            'c est quoi l adresse', 'donnez moi l adresse', 'donne moi l adresse',
            'envoie moi l adresse', 'envoie l adresse', 'envoyez l adresse',
            'pin de localisation', 'partagez la localisation', 'partager la localisation',
            # Demandes d'envoi
            'envoie', 'envoi', 'oui envoie', 'oui envoi',
            'envoie moi', 'envoi moi', 'oui la position',
            'donne moi la position', 'donne la position',
            'partage la position', 'partage ton adresse',
            # Nouchi / ivoirien + questions sur la venue au magasin
            'c est comment pour venir', 'comment je fais pour venir',
            'vous etes situe ou', 'ou vous etes', 'dans quel coin',
            'on peut venir comment', 'votre adresse', 'ton adresse',
            'quel secteur', 'c est quel zone', 'quel zone', 'quel quartier',
            'quel endroit', 'a quel endroit', 'dans quel endroit',
            'je peux venir', 'on peut venir',
            'le local c est ou', 'ton local c est ou', 'le shop c est ou',
            'vous garez ou', 'votre coin c est ou', 'le coin c est ou',
            'chez vous c est ou', 'dans quel bled', 'tu fais ton business',
            'ton business ou', 'tu es au marche',
            # Anglais
            'where are you', 'what s your address', 'where is your shop',
            'where is your store', 'how do i get there', 'how can i come',
            'i want to come', 'i ll come pick', 'send me your location',
            'share your location', 'the address please', 'where are you located',
            'what s the location', 'i want to pick up', 'i ll come by',
            'your address', 'where do you', 'how to get to',
        ]

        if any(loc in msg for loc in explicit_location):
            # Exclure les adresses non-physiques (mail, facturation, commerciale...)
            non_physical_ctx = (
                'mail', 'email', 'commerciale', 'facturation', 'fabricant',
                'sur la boite', 'noter', 'pour apres', 'interesse pas',
                'm interesse pas', 'pas l adresse', 'pas maintenant',
                'votre site', 'un site', 'whatsapp', 'livraison ca',
            )
            if any(np in msg for np in non_physical_ctx):
                return False
            return True

        # Vérification word-boundary pour les patterns courts susceptibles de faux positifs
        # "c est ou" ne doit PAS matcher "c est ouvert" (où 'ou' est préfixe de 'ouvert')
        if (re.search(r'\bc est ou\b', msg) or
                re.search(r'\bvous etes ou\b', msg) or
                re.search(r'\btu es ou\b', msg)):
            return True

        # "magasin" ou "boutique" + question ou demande de lieu
        # Note: 'ou' doit être un mot isolé (éviter "boutique" qui contient "ou")
        location_words = ['magasin', 'boutique', 'shop', 'chez vous', 'local', 'bled', 'business']
        direction_words_exact = ['?', 'comment', 'adresse', 'situe', 'localise', 'trouve',
                                  'aller', 'venir', 'endroit']
        has_location_word = any(lw in msg for lw in location_words)
        has_direction = (any(dw in msg for dw in direction_words_exact) or
                         bool(re.search(r'\bou\b', msg)))  # 'ou' isolé, pas substr de boutique
        if has_location_word and has_direction:
            # Exclure questions d'existence pure ("tu as une boutique?" ≠ "où est ta boutique?")
            existence_questions = [
                'tu as une boutique', 'vous avez une boutique',
                'il y a une boutique', 'tu as un magasin', 'vous avez un magasin',
            ]
            is_existence_question = any(eq in msg for eq in existence_questions)
            # Exclure questions d'horaires même avec location_words
            is_hours_with_location = ('?' in msg and
                                      any(h in msg for h in hours_markers))
            if not is_existence_question and not is_hours_with_location:
                return True
            # Si c'est une question d'existence → tomber sur le check quartier

        # Question avec un nom de quartier/ville = demande de confirmation de localisation
        quartiers = [
            'abobo', 'yopougon', 'cocody', 'plateau', 'adjame',
            'marcory', 'treichville', 'koumassi', 'port-bouet', 'port bouet',
            'bingerville', 'anyama', 'angre', 'riviera',
            'williamsville', 'attoban', 'palmeraie', 'bassam', 'grand-bassam',
            'mocville', 'mokcville', 'zone 4', 'vallon', '2 plateaux',
        ]
        # γ03: "vous livrez à Cocody?" = zone de livraison, PAS localisation du magasin
        delivery_zone_indicators = ['livrez', 'livraison', 'livrer', 'livrable']
        if '?' in msg and any(q in msg for q in quartiers):
            if not any(dk in msg for dk in delivery_zone_indicators):
                return True

        return False

    def _extract_address(self, message: str) -> Optional[str]:
        """Extrait une adresse du message"""
        msg_lower = message.lower()

        # Si c'est une question → ce n'est PAS une adresse fournie
        # Ex: "Vous a koumassi ?" = question, pas une adresse
        if '?' in message:
            return None

        # Quartiers d'Abidjan
        quartiers = [
            'abobo', 'yopougon', 'cocody', 'plateau', 'adjamé', 'adjame',
            'marcory', 'treichville', 'koumassi', 'port-bouet', 'port bouet',
            'bingerville', 'anyama', 'angré', 'angre', 'riviera', '2 plateaux',
            'deux plateaux', 'williamsville', 'attoban', 'palmeraie'
        ]

        # Vérifier si un quartier est mentionné
        for quartier in quartiers:
            if quartier in msg_lower:
                return message.strip()

        # Vérifier si un numéro de téléphone est présent (signe d'adresse)
        if re.search(r'\d{8,}', message):
            return message.strip()

        # Mots-clés d'adresse
        address_keywords = ['rue', 'avenue', 'boulevard', 'quartier', 'commune', 'près de', 'à côté']
        if any(kw in msg_lower for kw in address_keywords):
            return message.strip()

        return None

    def _detect_objection(self, msg: str) -> Optional[Intent]:
        """Détecte le type d'objection"""
        # Prix
        price_objections = [
            'trop cher', 'cher', 'budget', 'pas les moyens',
            'moins cher ailleurs', 'ailleurs moins cher', 'concurrent',
            'soi disant',   # δ03: "soi-disant 18500?" → ironie sur le prix
            'raisonnable',  # δ06: "tu crois c'est raisonnable?" → question rhétorique
            'c est fort',   # ζ07: "c'est fort ce prix" → nouchi = c'est cher
        ]
        if any(obj in msg for obj in price_objections):
            return Intent(
                event=ConversationEvent.OBJECTION_PRICE,
                confidence=0.85,
                extracted_data={"type": "price"}
            )

        # Qualité
        quality_objections = [
            'original', 'authentique', 'vrai', 'faux', 'copie',
            'contrefaçon', 'qualité', 'qualite'
        ]
        if any(obj in msg for obj in quality_objections) and '?' in msg:
            return Intent(
                event=ConversationEvent.OBJECTION_QUALITY,
                confidence=0.8,
                extracted_data={"type": "quality"}
            )

        # Confiance
        # Note: 'sur' retiré car trop large ("plus sur la qualité" → faux positif)
        trust_objections = [
            'confiance', 'arnaque', 'peur', 'méfiant', 'sûr', 'pas sûr', 'doute'
        ]
        # "arnaqueur", "escroc" = accusation directe = frustration, pas objection
        trust_exclusions = ['arnaqueur', 'escroque', 'escroc']
        if any(obj in msg for obj in trust_objections) and not any(excl in msg for excl in trust_exclusions):
            return Intent(
                event=ConversationEvent.OBJECTION_TRUST,
                confidence=0.8,
                extracted_data={"type": "trust"}
            )

        # Timing
        timing_objections = [
            'réfléchir', 'reflechir', 'plus tard', 'pas maintenant',
            'demain', 'la semaine prochaine', 'rappeler'
        ]
        if any(obj in msg for obj in timing_objections):
            return Intent(
                event=ConversationEvent.OBJECTION_TIMING,
                confidence=0.8,
                extracted_data={"type": "timing"}
            )

        return None

    def _is_frustrated(self, msg: str, original: str) -> bool:
        """Détecte la frustration"""
        frustration_words = [
            'voleur', 'arnaque', 'arnaqueur', 'escroc', 'escroque', 'menteur', 'idiot',
            'fou', 'folle', 'dingue', 'merde', 'putain',
            'tu abuses', 'tu exagères', 'n\'importe quoi', 'c\'est du vol'
        ]

        if any(fw in msg for fw in frustration_words):
            return True

        # Majuscules excessives
        if len(original) > 10:
            uppercase_count = sum(1 for c in original if c.isupper())
            if uppercase_count > len(original) * 0.5:
                return True

        # Ponctuation excessive
        if original.count('!') >= 3 or original.count('?') >= 3:
            return True

        return False

    def _is_goodbye(self, msg: str) -> bool:
        """Détecte une fin de conversation — français + nouchi"""
        goodbyes = [
            # Français
            'bye', 'au revoir', 'ciao', 'non merci', 'pas interesse',
            'laisse tomber', 'laisse', 'c est bon laisse',
            'bonne continuation', 'bonne journee', 'a une autre fois',
            'c est pas pour moi', 'ca m interesse pas',
            # Nouchi / ivoirien
            'annuler', 'j abandonne', 'partez',
            'on oublie', 'oublie', 'c est bon oublie',
            'j ai change d avis', 'finalement non',
            'ca degage', 'je degage',   # ζ03: "ça dégage ici" = je pars = SAY_GOODBYE
            # Anglais courant
            'forget it', 'never mind', 'not interested', 'no thanks',
        ]

        if len(msg) < 50:
            return msg.strip() in goodbyes or any(g in msg for g in goodbyes)

        return False

    def _is_price_question(self, msg: str) -> bool:
        """Détecte une question sur le prix — français + nouchi"""
        price_questions = [
            # Français
            'combien', 'prix', 'coute', 'a combien', 'le tarif',
            'ca fait combien', 'c est a combien', 'vous vendez a combien',
            'c est quoi le prix', 'quel est le prix', 'le cout',
            # Nouchi / ivoirien
            'c est comment', 'c comment', 'c est quoi comme prix',
            'vous avez le prix', 'wari yeke obe',  # dioula: combien ça coûte
            # Abréviations
            'le px', 'le $', 'le pr',
        ]
        return any(pq in msg for pq in price_questions)

    def _is_visit_intent(self, msg: str) -> bool:
        """Détecte une intention de visite au premier message"""
        visit_keywords = [
            'passer voir', 'passe voir', 'venir voir', 'viens voir',
            'passer a la boutique', 'passer à la boutique',
            'venir a la boutique', 'venir à la boutique',
            'visiter la boutique', 'visiter le magasin',
            'je passe', 'je viens', 'passer au magasin',
            'voir a la boutique', 'voir à la boutique',
            'voir au magasin'
        ]
        if any(kw in msg for kw in visit_keywords):
            # "je viens avec les sous" = paiement = accord, pas visite
            if any(mw in msg for mw in ('sous', 'monnaie', 'argent', 'cash')):
                return False
            # "je passe commande" = commander = accord, pas visite au magasin
            if 'commande' in msg:
                return False
            return True
        return False

    def _is_wrong_location_question(self, msg: str, merchant_data: Dict) -> Optional[str]:
        """
        Détecte si le client mentionne un mauvais emplacement.
        Retourne l'adresse correcte du marchand si le client se trompe, None sinon.
        """
        if not merchant_data or not merchant_data.get('address'):
            return None

        merchant_address = merchant_data['address'].lower()

        # Liste des quartiers/villes connus
        known_locations = [
            'abobo', 'yopougon', 'cocody', 'plateau', 'adjamé', 'adjame',
            'marcory', 'treichville', 'koumassi', 'port-bouet', 'port bouet',
            'bingerville', 'anyama', 'angré', 'angre', 'riviera',
            'williamsville', 'attoban', 'palmeraie', 'bassam', 'grand-bassam',
            'mocville', 'mokcville', 'bouaké', 'bouake', 'yamoussoukro',
            'san pedro', 'daloa', 'korhogo', 'man', 'aboisso',
            '2 plateaux', 'deux plateaux', 'zone 4', 'vallon',
        ]

        # Trouver les lieux mentionnés par le client
        mentioned_locations = [loc for loc in known_locations if loc in msg]

        if not mentioned_locations:
            return None

        # Vérifier si le lieu mentionné est DANS l'adresse du marchand
        for loc in mentioned_locations:
            if loc in merchant_address:
                return None  # Le client a raison

        # Le client mentionne un lieu qui N'EST PAS dans l'adresse du marchand
        return merchant_data['address']

    def _is_status_correction(self, msg: str) -> bool:
        """Détecte quand le client conteste un achat prématurément déclaré par le bot."""
        patterns = [
            # Avec accents (après normalisation unicode)
            "j ai rien acheté", "j'ai rien acheté", "j ai pas acheté",
            "j'ai pas acheté", "j ai rien commandé", "j'ai rien commandé",
            "j'ai pas commandé", "j ai pas commandé", "je n ai rien acheté",
            "je n ai pas commandé", "j ai rien décidé", "j ai rien signé",
            "pas encore acheté", "pas encore commandé", "pas encore décidé",
            "on a rien conclu", "on n a pas conclu", "j ai pas dit oui",
            "j'ai pas dit oui", "j ai pas encore dit", "j ai rien dit",
            # Sans accents (comme dans les messages WhatsApp courants)
            "j ai rien achete", "j'ai rien achete", "j ai pas achete",
            "j'ai pas achete", "j ai rien commande", "j'ai rien commande",
            "j'ai pas commande", "j ai pas commande", "je n ai rien achete",
            "je n ai pas commande", "j ai rien decide", "pas encore achete",
            "pas encore commande", "pas encore decide", "j ai rien achet",
            "n ai pas achete", "n ai rien achete",
        ]
        return any(p in msg for p in patterns)

    def _is_hours_question(self, msg: str) -> bool:
        """Détecte une question sur les horaires d'ouverture — patterns précis pour éviter faux positifs"""
        hours_patterns = [
            'horaire', 'ouverture', 'fermeture',
            'quelle heure', 'jusqu a quelle heure', 'a partir de quelle heure',
            'de quel heure', 'ouvert quand', 'quand vous ouvrez', 'quand vous fermez',
            'vous ouvrez a', 'vous fermez a', 'vous etes ouvert',
            'tu es ouvert', 'c est ouvert', 'vous ouvrez', 'vous fermez',
            'ouvert jusqu', 'ferme quand', 'ouvert de',
        ]
        return any(p in msg for p in hours_patterns)

    def _shows_interest(self, msg: str) -> bool:
        """Détecte un intérêt général"""
        interest_keywords = [
            'intéress', 'interesse', 'dispo', 'disponible',
            'photo', 'image', 'voir', 'couleur', 'taille'
        ]
        return any(kw in msg for kw in interest_keywords)


# =============================================================================
# PARTIE 5: NÉGOCIATION INTELLIGENTE
# =============================================================================

@dataclass
class NegotiationContext:
    """Contexte de négociation"""
    product_name: str
    listed_price: float       # Prix affiché
    min_price: float          # Prix minimum (secret)
    current_offer: Optional[float] = None
    counter_offers: List[float] = field(default_factory=list)
    client_offers: List[float] = field(default_factory=list)
    low_offers_count: int = 0

    @property
    def margin(self) -> float:
        """Marge entre prix affiché et minimum"""
        return self.listed_price - self.min_price

    @property
    def is_final_price_mode(self) -> bool:
        """Mode dernier prix après 2+ offres basses"""
        return self.low_offers_count >= 2

    @property
    def should_end_negotiation(self) -> bool:
        """Arrêter après 3+ offres basses persistantes"""
        return self.low_offers_count >= 3

    def calculate_counter_offer(self, client_offer: float) -> float:
        """
        Calcule une contre-offre intelligente.

        Stratégie:
        - Si offre >= min_price: accepter
        - Si offre proche (80%+): petite concession
        - Si offre basse: rester ferme avec explication
        """
        if client_offer >= self.min_price:
            return client_offer  # Accepter

        # Calculer le point médian dynamique
        if self.counter_offers:
            last_counter = self.counter_offers[-1]
            # Descendre progressivement mais jamais sous min_price
            new_counter = max(
                self.min_price,
                last_counter - (self.margin * 0.1)  # -10% de la marge
            )
        else:
            # Première contre-offre: milieu entre prix client et prix affiché
            new_counter = (client_offer + self.listed_price) / 2
            # Mais pas en dessous du minimum
            new_counter = max(self.min_price, new_counter)

        return int(new_counter)

    def record_client_offer(self, offer: float):
        """Enregistre une offre client"""
        self.client_offers.append(offer)
        self.current_offer = offer

        if offer < self.min_price:
            self.low_offers_count += 1

    def record_counter_offer(self, counter: float):
        """Enregistre une contre-offre bot"""
        self.counter_offers.append(counter)


# =============================================================================
# PARTIE 6: GÉNÉRATION DE RÉPONSES
# =============================================================================

class ResponseGenerator:
    """
    Générateur de réponses contextuelles et naturelles.
    Adapte le ton et le contenu selon l'état, le sentiment et le contexte.
    """

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, List[str]]:
        """Charge les templates de réponses — variés, naturels, style WhatsApp ivoirien"""
        return {
            # === Salutations (premier message uniquement) ===
            "greeting_first": [
                "Salut! Oui c'est disponible à {price} F. Ça t'intéresse?",
                "Hey! Le {product} est là à {price} F. Tu veux?",
                "Coucou! Oui c'est dispo. {price} F. Ça te dit?",
                "Bonjour! Le {product} est disponible à {price} F. On peut discuter!",
                "Salut! C'est le {product} à {price} F. Tu veux plus d'infos?",
                "Oui c'est bien disponible! Prix: {price} F. Ça t'interesse?",
            ],

            # === Premier message avec intention de visite ===
            "first_message_visit": [
                "Merci pour ton intérêt! Tu sais où se trouve la boutique?",
                "Content que ça te plaise! Tu connais notre adresse?",
                "Super! Tu sais où on est situé?",
                "Cool! Tu connais déjà l'emplacement de la boutique?",
                "Avec plaisir! Tu as déjà l'adresse ou je t'envoie la localisation?",
            ],

            # === Prix présenté (pas de salutation) ===
            "price_presented": [
                "C'est {price} F. Tu veux qu'on discute?",
                "{price} F pour celui-là. Ça t'intéresse?",
                "Le prix c'est {price} F. On peut s'arranger!",
                "On est à {price} F. Tu as une offre à faire?",
                "Le {product} c'est {price} F. Qu'est-ce que t'en penses?",
            ],

            # === Acceptation de l'offre ===
            "offer_accepted": [
                "OK {client_price} F c'est bon! Livraison ou tu passes chercher?",
                "C'est deal à {client_price} F! Tu préfères livraison ou pickup?",
                "Parfait pour {client_price} F! Comment tu veux récupérer?",
                "On s'entend pour {client_price} F! Livraison ou tu viens?",
                "Banco à {client_price} F! On fait comment pour la livraison?",
                "C'est bon pour {client_price} F! Tu viens au magasin ou on t'envoie?",
            ],

            # === Contre-offre ===
            "counter_offer": [
                "Ah {client_price} F c'est un peu bas! On dit {counter} F?",
                "{client_price} F je peux pas... Allez {counter} F et on se comprend!",
                "Pour {client_price} F c'est chaud! {counter} F ça te va?",
                "Hm {client_price} F c'est juste. On peut faire {counter} F, c'est déjà un effort!",
                "{client_price} F c'est vraiment peu pour ce produit. {counter} F et on deal?",
                "Je comprends tu veux un bon prix. {counter} F c'est mon mieux là!",
                "Ah non {client_price} c'est trop bas. Je peux faire {counter} F, pas moins!",
            ],

            # === Dernier prix ===
            "final_offer": [
                "{price} F c'est vraiment mon DERNIER prix. À prendre ou à laisser!",
                "Je fais un gros effort: {price} F point final. C'est le minimum!",
                "Bon, {price} F et on arrête là. C'est mon prix plancher!",
                "Écoute, {price} F c'est tout ce que je peux faire. C'est sincère!",
                "Là c'est {price} F, je peux vraiment pas faire moins. Qu'est-ce que tu dis?",
            ],

            # === Fin de négociation (refus persistant) ===
            "negotiation_ended": [
                "J'ai fait mon maximum. Je peux vraiment pas descendre plus. Reviens quand tu veux!",
                "C'est vraiment mon dernier prix. Si ça te va pas, pas de souci!",
                "J'ai atteint ma limite là. N'hésite pas à revenir si tu changes d'avis!",
                "Désolé, je peux pas aller plus bas. Reviens quand tu veux, le produit reste dispo!",
            ],

            # === Client frustré — empathie ===
            "frustrated_empathy": [
                "Je comprends que ça puisse sembler cher, c'est de la vraie qualité!",
                "Écoute, je suis désolé si ça te semble élevé. C'est quoi ton budget?",
                "Je comprends ta réaction. Dis-moi ce qui te conviendrait?",
                "Hé je vois tu es frustré. Je veux qu'on trouve un accord. Ton budget c'est quoi?",
                "Calme, on va trouver quelque chose! Fais-moi une offre sérieuse.",
            ],

            # === Objection prix ===
            "objection_price": [
                "Je comprends! Dis-moi ton budget et on voit ce qu'on peut faire.",
                "C'est de la qualité, mais je peux faire un effort. Tu proposes combien?",
                "Je comprends que c'est un investissement. Fais-moi une offre!",
                "OK donne-moi un chiffre sérieux et on discute!",
                "Tout le monde veut un bon prix! C'est quoi ton budget max?",
            ],

            # === Objection qualité ===
            "objection_quality": [
                "C'est du {product} original, qualité garantie!",
                "Je te garantis la qualité. Si y'a un souci, tu reviens me voir!",
                "C'est du vrai, pas de la copie. Tu peux vérifier à la livraison!",
                "Garanti original! On fait même le retour si tu n'es pas satisfait.",
                "La qualité est top! C'est pas de la copie. Tu vas voir toi-même.",
            ],

            # === Objection confiance ===
            "objection_trust": [
                "Je comprends ta méfiance, c'est normal. Je suis un vendeur sérieux!",
                "Pas de souci, tu peux vérifier le produit avant de payer.",
                "On peut faire cash à la livraison si tu préfères!",
                "Ta confiance c'est important pour moi. Cash à la livraison, ça te va?",
                "Paiement à la livraison possible. Tu paies quand tu reçois le produit!",
            ],

            # === Objection timing ===
            "objection_timing": [
                "Pas de problème, prends ton temps! Je garde le produit.",
                "OK réfléchis bien. Je reste dispo quand tu veux!",
                "Aucun souci! Tu me recontactes quand tu es prêt.",
                "Prends le temps qu'il faut. Je suis là quand tu décides!",
                "Pas de rush! Reviens quand tu es sûr, le produit t'attend.",
            ],

            # === Choix livraison ===
            "ask_delivery_choice": [
                "Tu préfères la livraison ou tu passes au magasin?",
                "Livraison ou tu viens chercher?",
                "Comment tu veux faire? Livraison ou pickup?",
                "On te livre ou tu passes récupérer?",
                "Tu veux qu'on t'envoie ou tu viens directement?",
            ],

            # === Demande d'adresse ===
            "ask_address": [
                "Super! Envoie-moi ton adresse et numéro pour la livraison.",
                "OK pour la livraison! C'est où pour toi? Donne-moi l'adresse.",
                "Livraison c'est noté! Ton adresse et numéro stp?",
                "Parfait! Où est-ce qu'on te livre? Adresse + numéro.",
                "C'est bon! Envoie ton adresse complète et on règle ça.",
            ],

            # === Adresse reçue ===
            "address_received": [
                "Parfait! Je note. On te contacte pour organiser la livraison.",
                "C'est noté! Le vendeur te rappelle pour la livraison.",
                "Super! Tu seras contacté rapidement pour la livraison.",
                "Bien reçu! On te rappelle très vite pour confirmer.",
                "Noté! Le vendeur va te contacter pour fixer la livraison.",
            ],

            # === Localisation envoyée ===
            "location_sent": [
                "Je t'envoie la localisation!",
                "Voici l'adresse du magasin!",
                "Tiens, c'est ici!",
                "La position arrive!",
                "Je t'envoie le GPS!",
            ],

            # === Localisation demandée tôt dans la conversation ===
            "location_early": [
                "Je t'envoie la position! N'hésite pas si tu as des questions sur le {product}.",
                "Voici la localisation! Le {product} est à {display_price} F si ça t'intéresse.",
                "Tiens, voilà où on est! Passe quand tu veux.",
                "Je t'envoie l'adresse! Le {product} est dispo si tu veux.",
                "Position envoyée! Le {product} t'attend à {display_price} F.",
            ],

            # === Client mentionne un mauvais emplacement ===
            "wrong_location": [
                "Non, on n'est pas là-bas! On est à {merchant_address}. Je t'envoie la position exacte!",
                "Non pas du tout! La boutique est à {merchant_address}. Tiens, je t'envoie la localisation!",
                "Ah non! On est situé à {merchant_address}. Je t'envoie la position!",
                "Pas là! La boutique est à {merchant_address}. Position envoyée!",
                "Tu te trompes d'endroit! On est à {merchant_address}. Je t'envoie le GPS.",
            ],

            # === Attente pickup ===
            "pending_pickup": [
                "On t'attend au magasin!",
                "A tout a l'heure alors!",
                "Parfait, a bientot!",
                "OK on t'attend! A tout de suite.",
                "Super! Viens quand tu veux, on est là.",
                "On t'attend de pied ferme!",
            ],

            # === Questions d'horaires (jamais inventer) ===
            "hours_question": [
                "Pour les horaires, contacte directement le vendeur!",
                "Je ne connais pas les horaires exacts. Contacte le vendeur pour ça!",
                "Pour les heures d'ouverture, le vendeur te répondra directement.",
                "Les horaires varient! Mieux vaut contacter le vendeur pour être sûr.",
            ],

            # === Correction de statut (client nie avoir acheté) ===
            "status_correction": [
                "Pardon pour la confusion! On n'a pas encore finalisé. Tu es intéressé par le {product}?",
                "Toutes mes excuses! Je me suis trompé. On n'a rien conclu. Tu veux continuer?",
                "Excuse-moi pour la confusion! On n'a pas encore validé l'achat. Tu veux reprendre?",
                "Pardon! J'ai mal compris. Qu'est-ce que tu veux faire pour le {product}?",
            ],

            # === Questions générales ===
            "general_question": [
                "Tu veux savoir quoi exactement?",
                "Je t'écoute! Qu'est-ce que tu veux savoir?",
                "Dis-moi ce qui t'intéresse!",
                "Qu'est-ce que je peux faire pour toi?",
            ],

            # === Relance douce ===
            "soft_follow_up": [
                "Alors, ça t'intéresse?",
                "Tu veux qu'on procède?",
                "Des questions?",
                "Qu'est-ce que tu en penses?",
                "On avance?",
            ],

            # === Ambiguïté détectée (Phase 4) ===
            "ambiguity_clarify": [
                "Désolé, je n'ai pas bien compris. Tu parles du prix ou d'autre chose?",
                "Peux-tu préciser? Tu veux savoir quoi exactement?",
                "Je suis pas sûr de comprendre. Tu peux reformuler?",
                "Hmm dis-moi plus clairement ce que tu veux savoir!",
            ],
        }

    def generate(
        self,
        state: ConversationState,
        sentiment: SentimentAnalysis,
        negotiation: NegotiationContext,
        intent: Intent,
        memory: ConversationMemory,
        merchant_data: Dict = None
    ) -> str:
        """
        Génère une réponse appropriée basée sur tous les contextes.
        """
        # Variables de contexte
        merchant_address = ""
        if merchant_data and merchant_data.get('address'):
            merchant_address = merchant_data['address']

        # Prix à afficher : prix négocié si un accord est en cours, sinon prix catalogue
        display_price_value = negotiation.current_offer if negotiation.current_offer and negotiation.current_offer >= negotiation.min_price else negotiation.listed_price

        context = {
            "product": negotiation.product_name,
            "price": f"{negotiation.listed_price:,.0f}".replace(",", " "),
            "display_price": f"{display_price_value:,.0f}".replace(",", " "),
            "min_price": f"{negotiation.min_price:,.0f}".replace(",", " "),
            "client_price": f"{negotiation.current_offer:,.0f}".replace(",", " ") if negotiation.current_offer else "",
            "merchant_address": merchant_address,
        }

        # Sélectionner le template selon l'état
        template_key = self._select_template_key(state, sentiment, intent, negotiation, memory, merchant_data)

        # Traitement spécial pour les contre-offres
        if template_key == "counter_offer" and negotiation.current_offer:
            counter = negotiation.calculate_counter_offer(negotiation.current_offer)
            context["counter"] = f"{counter:,.0f}".replace(",", " ")
            negotiation.record_counter_offer(counter)

        # Sélectionner et formater le template
        templates = self.templates.get(template_key, self.templates["general_question"])
        template = random.choice(templates)

        try:
            response = template.format(**context)
        except KeyError:
            response = template

        return response

    def _select_template_key(
        self,
        state: ConversationState,
        sentiment: SentimentAnalysis,
        intent: Intent,
        negotiation: NegotiationContext,
        memory: ConversationMemory,
        merchant_data: Dict = None
    ) -> str:
        """Sélectionne la clé de template appropriée"""

        # Correction de statut — priorité absolue
        if intent.extracted_data.get("status_correction"):
            return "status_correction"

        # Mauvais emplacement mentionné par le client - priorité maximale
        if intent.extracted_data.get("wrong_location") and merchant_data and merchant_data.get('address'):
            return "wrong_location"

        # Demande de localisation — envoie la position SANS changer l'état de négociation
        # Demander où se trouve la boutique ≠ accepter d'acheter
        if intent.event == ConversationEvent.ASK_LOCATION:
            return "location_early"

        # Question d'horaires - priorité haute (jamais inventer)
        if intent.extracted_data.get("hours_question"):
            return "hours_question"

        # Client frustré - priorité haute
        if state == ConversationState.FRUSTRATED_CLIENT or sentiment.emotion in [Emotion.ANGRY, Emotion.FRUSTRATED]:
            return "frustrated_empathy"

        # Gestion des objections
        if state == ConversationState.OBJECTION_HANDLING:
            obj_type = intent.extracted_data.get("type", "price")
            return f"objection_{obj_type}"

        # États de négociation
        if state == ConversationState.GREETING:
            return "greeting_first"

        if state == ConversationState.PRICE_PRESENTED:
            # Si le client veut passer à la boutique → demander s'il connaît l'adresse
            if intent.extracted_data.get("visit_intent"):
                return "first_message_visit"
            # Si le client demande la localisation en early stage
            if intent.event == ConversationEvent.ASK_LOCATION:
                return "location_early"
            if memory.total_messages <= 1:
                return "greeting_first"
            return "price_presented"

        if state == ConversationState.DEAL_AGREED:
            if negotiation.current_offer:
                return "offer_accepted"
            return "ask_delivery_choice"

        if state == ConversationState.NEGOTIATING:
            if negotiation.current_offer and negotiation.current_offer >= negotiation.min_price:
                return "offer_accepted"
            return "counter_offer"

        if state == ConversationState.COUNTER_OFFER:
            return "counter_offer"

        if state == ConversationState.FINAL_OFFER:
            if negotiation.should_end_negotiation:
                return "negotiation_ended"
            return "final_offer"

        if state == ConversationState.ENDED:
            return "negotiation_ended"

        # États de livraison
        if state == ConversationState.CHOOSING_DELIVERY:
            return "ask_delivery_choice"

        if state == ConversationState.COLLECTING_ADDRESS:
            return "ask_address"

        if state == ConversationState.PENDING_DELIVERY:
            return "address_received"

        if state == ConversationState.PENDING_PICKUP:
            return "pending_pickup"

        if state == ConversationState.COOLING_OFF:
            return "objection_timing"

        return "soft_follow_up"


# =============================================================================
# PARTIE 7: ORCHESTRATEUR PRINCIPAL
# =============================================================================

class ConversationEngine:
    """
    Moteur de conversation principal.
    Orchestre tous les composants pour générer des réponses cohérentes.
    """

    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.intent_extractor = IntentExtractor()
        self.response_generator = ResponseGenerator()

    async def process_message(
        self,
        client_message: str,
        product: Dict[str, Any],
        conversation_history: List[Dict],
        current_state: str = "active",
        current_offer: Optional[float] = None,
        merchant_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Traite un message client et génère une réponse.

        Args:
            client_message: Message du client
            product: Données produit (name, price, min_price)
            conversation_history: Historique des messages
            current_state: État actuel de la conversation
            current_offer: Dernière offre en cours

        Returns:
            {
                "response": str,
                "new_state": str,
                "new_offer": Optional[float],
                "deal_accepted": bool,
                "send_location": bool,
                "debug_info": Dict
            }
        """
        # 1. Initialiser la mémoire
        memory = self._build_memory(conversation_history)

        # 2. Initialiser le contexte de négociation
        negotiation = NegotiationContext(
            product_name=product['name'],
            listed_price=product['price'],
            min_price=product['min_price'],
            current_offer=current_offer
        )

        # Compter les offres basses précédentes
        for msg in conversation_history:
            if msg.get('is_from_client'):
                price = self.intent_extractor._extract_price(msg.get('content', ''))
                if price and price < negotiation.min_price:
                    negotiation.low_offers_count += 1

        # 3. Mapper l'état string vers l'enum FSM
        fsm_state = self._map_state_to_fsm(current_state)
        fsm = ConversationFSM(initial_state=fsm_state)

        # 4. Analyser le sentiment
        sentiment = self.sentiment_analyzer.analyze(client_message)

        # 4b. Extraire le dernier message du bot (contexte pour résolution d'intention)
        # Ex: si le bot vient de faire une contre-offre, "ok" = ACCEPT_OFFER (pas EXPRESS_INTEREST)
        last_bot_message = None
        for msg in reversed(conversation_history):
            if not msg.get('is_from_client'):
                last_bot_message = msg.get('content', '')
                break

        # 4d. Dériver les intentions récentes du client (boost de confiance contextuel)
        intent_history = self._get_recent_client_intents(conversation_history)

        # 5. Extraire l'intention (passer l'état courant pour prioriser pickup/delivery en DEAL_AGREED)
        intent = self.intent_extractor.extract(client_message, memory, current_state=fsm_state, merchant_data=merchant_data, last_bot_message=last_bot_message, intent_history=intent_history)

        # 6. Enregistrer l'offre si présente
        if intent.event == ConversationEvent.PRICE_OFFER:
            price_offered = intent.extracted_data.get("price")
            if price_offered:
                negotiation.record_client_offer(price_offered)

                # Vérifier si l'offre est acceptable
                # Règle 1: >= prix affiché → toujours accepter (offre généreuse)
                # Règle 2: >= min_price ET pas question → accepter (offre acceptable, deal garanti)
                # Règle 3: > min ET signal d'acceptation ET pas question → accepter (garde pour compatibilité)
                # Règle 4: = min ET bot venait de contre-offrir ET signal d'acceptation → accepter
                # Note: questions ("2100 F?") → garder PRICE_OFFER
                _norm_msg = self.intent_extractor._normalize_message(client_message.lower())
                _has_accept_signal = self.intent_extractor._is_acceptance(_norm_msg)
                _bot_lower = last_bot_message.lower() if last_bot_message else ''
                _counter_signals = ('mon dernier', 'dernier prix', 'je te propose', 'je peux faire',
                                    'je descends', 'je baisse', 'on peut faire', 'prix special',
                                    'pour toi je fais', 'c est mon dernier', 'dernier')
                _bot_made_counter = any(sig in _bot_lower for sig in _counter_signals)
                if (price_offered >= negotiation.listed_price
                        or (price_offered >= negotiation.min_price and '?' not in client_message)
                        or (price_offered > negotiation.min_price and '?' not in client_message and _has_accept_signal)
                        or (price_offered >= negotiation.min_price and _bot_made_counter and _has_accept_signal)):
                    intent = Intent(
                        event=ConversationEvent.ACCEPT_OFFER,
                        confidence=0.95,
                        extracted_data={"price": price_offered, "auto_accepted": True}
                    )

        # 6b. Acceptation directe sans prix (ex: "lui la", "ok", "parfait") →
        # utiliser le prix affiché comme prix accepté pour le template
        if intent.event == ConversationEvent.ACCEPT_OFFER and not negotiation.current_offer:
            negotiation.current_offer = negotiation.listed_price

        # 6c. Correction de statut — le client nie avoir acheté
        # On réinitialise l'état FSM à PRICE_PRESENTED pour reprendre normalement
        if intent.extracted_data.get("status_correction"):
            fsm.force_state(ConversationState.PRICE_PRESENTED)
            # On retire le flag de deal_accepted pour éviter toute notification
            negotiation.current_offer = None

        # 7. Effectuer la transition FSM
        new_state_enum = fsm.transition(intent.event)
        if new_state_enum is None:
            # Pas de transition valide, rester dans l'état actuel
            new_state_enum = fsm.current_state

        # 8. Générer la réponse
        response = self.response_generator.generate(
            state=new_state_enum,
            sentiment=sentiment,
            negotiation=negotiation,
            intent=intent,
            memory=memory,
            merchant_data=merchant_data
        )

        # 9. Déterminer les flags de sortie
        # PENDING_PICKUP = deal accepté SAUF si localisation demandée pendant négociation
        # Note: ASK_LOCATION depuis NEGOTIATING/COUNTER_OFFER/FINAL_OFFER reste dans ces états (FSM fixé)
        # Donc PENDING_PICKUP via ASK_LOCATION n'est possible QUE depuis DEAL_AGREED (deal déjà conclu)
        deal_accepted = new_state_enum in [
            ConversationState.DEAL_AGREED,
            ConversationState.COLLECTING_ADDRESS,  # Client a dit "livraison" après accord
            ConversationState.PENDING_DELIVERY,
            ConversationState.PENDING_PICKUP
        ]

        send_location = (
            new_state_enum == ConversationState.PENDING_PICKUP or
            intent.event == ConversationEvent.ASK_LOCATION
        )

        # 10. Mapper le nouvel état vers string
        new_state_str = self._map_fsm_to_state(new_state_enum)

        return {
            "response": response,
            "new_state": new_state_str,
            "new_offer": negotiation.current_offer,
            "deal_accepted": deal_accepted,
            "send_location": send_location,
            "debug_info": {
                "fsm_state": new_state_enum.name,
                "intent": intent.event.name,
                "intent_confidence": intent.confidence,
                "sentiment": sentiment.emotion.value,
                "sentiment_intensity": sentiment.intensity,
                "low_offers_count": negotiation.low_offers_count,
                "is_final_price_mode": negotiation.is_final_price_mode,
                "visit_intent": intent.extracted_data.get("visit_intent", False),
                "wrong_location": intent.extracted_data.get("wrong_location", False),
                "hours_question": intent.extracted_data.get("hours_question", False),
                "status_correction": intent.extracted_data.get("status_correction", False)
            }
        }

    def _get_recent_client_intents(self, conversation_history: List[Dict], n: int = 4) -> List[str]:
        """
        Dérive les intentions récentes des messages client par heuristique rapide.
        Évite de relancer le pipeline complet extract() sur chaque message historique.

        Retourne une liste d'étiquettes comme ['PRICE_OFFER', 'OBJECTION_PRICE', 'ACCEPT_OFFER']
        """
        # Prendre les n derniers messages clients
        recent_msgs = [
            msg.get('content', '')
            for msg in conversation_history[-12:]
            if msg.get('is_from_client')
        ][-n:]

        intents = []
        for content in recent_msgs:
            cl = content.lower()
            # Signaux de départ
            if any(w in cl for w in ['au revoir', 'bonne continuation', 'laisse tomber', 'ca degage', 'je degage', 'bye', 'ciao']):
                intents.append('SAY_GOODBYE')
            # Accord/acceptation
            elif any(w in cl for w in ['je prends', 'je prend', 'deal', 'banco', 'accord', 'parfait', 'vendu', 'marche']) and not any(n in cl for n in ['non', 'mais', 'trop cher']):
                intents.append('ACCEPT_OFFER')
            # Objection prix
            elif any(w in cl for w in ['trop cher', 'cher', 'pas les moyens', 'budget', 'impossible']):
                intents.append('OBJECTION_PRICE')
            # Offre de prix (numérique)
            elif re.search(r'\b\d[\d\s]{2,6}\b', cl) and not any(w in cl for w in ['trop', 'cher', 'raisonnable']):
                intents.append('PRICE_OFFER')
            # Localisation
            elif any(w in cl for w in ['où', 'adresse', 'boutique', 'localisation', 'position', 'plan']):
                intents.append('ASK_LOCATION')
            else:
                intents.append('EXPRESS_INTEREST')

        return intents

    def _build_memory(self, history: List[Dict]) -> ConversationMemory:
        """Construit la mémoire à partir de l'historique"""
        memory = ConversationMemory()
        for msg in history:
            memory.add_message(
                content=msg.get('content', ''),
                is_from_client=msg.get('is_from_client', False)
            )
        return memory

    def _map_state_to_fsm(self, state_str: str) -> ConversationState:
        """Mappe un état string vers l'enum FSM"""
        mapping = {
            "active": ConversationState.PRICE_PRESENTED,
            "negotiating": ConversationState.NEGOTIATING,
            "agreed": ConversationState.DEAL_AGREED,
            "pending_delivery": ConversationState.PENDING_DELIVERY,
            "pending_pickup": ConversationState.PENDING_PICKUP,
            "completed": ConversationState.COMPLETED,
            "ended": ConversationState.ENDED,
            "abandoned": ConversationState.ENDED
        }
        return mapping.get(state_str, ConversationState.GREETING)

    def _map_fsm_to_state(self, fsm_state: ConversationState) -> str:
        """Mappe un état FSM vers string pour la DB"""
        mapping = {
            ConversationState.GREETING: "active",
            ConversationState.PRODUCT_INQUIRY: "active",
            ConversationState.PRICE_PRESENTED: "active",
            ConversationState.NEGOTIATING: "negotiating",
            ConversationState.COUNTER_OFFER: "negotiating",
            ConversationState.FINAL_OFFER: "negotiating",
            ConversationState.OBJECTION_HANDLING: "negotiating",
            ConversationState.FRUSTRATED_CLIENT: "negotiating",
            ConversationState.COOLING_OFF: "active",
            ConversationState.DEAL_AGREED: "agreed",
            ConversationState.CHOOSING_DELIVERY: "agreed",
            ConversationState.COLLECTING_ADDRESS: "agreed",
            ConversationState.PENDING_DELIVERY: "pending_delivery",
            ConversationState.PENDING_PICKUP: "pending_pickup",
            ConversationState.COMPLETED: "completed",
            ConversationState.ENDED: "ended"
        }
        return mapping.get(fsm_state, "active")


# =============================================================================
# INSTANCE GLOBALE
# =============================================================================

_engine: Optional[ConversationEngine] = None


def get_conversation_engine() -> ConversationEngine:
    """Retourne l'instance globale du moteur de conversation"""
    global _engine
    if _engine is None:
        _engine = ConversationEngine()
    return _engine
