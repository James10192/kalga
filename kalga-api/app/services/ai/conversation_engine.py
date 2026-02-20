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
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.CHOOSE_PICKUP, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.ASK_LOCATION, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.PRICE_PRESENTED, ConversationEvent.CHOOSE_DELIVERY, ConversationState.COLLECTING_ADDRESS),
        StateTransition(ConversationState.NEGOTIATING, ConversationEvent.CHOOSE_PICKUP, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.NEGOTIATING, ConversationEvent.ASK_LOCATION, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.NEGOTIATING, ConversationEvent.CHOOSE_DELIVERY, ConversationState.COLLECTING_ADDRESS),
        StateTransition(ConversationState.COUNTER_OFFER, ConversationEvent.CHOOSE_PICKUP, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.COUNTER_OFFER, ConversationEvent.ASK_LOCATION, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.FINAL_OFFER, ConversationEvent.CHOOSE_PICKUP, ConversationState.PENDING_PICKUP),
        StateTransition(ConversationState.FINAL_OFFER, ConversationEvent.ASK_LOCATION, ConversationState.PENDING_PICKUP),

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

    def extract(self, message: str, context: ConversationMemory, current_state: ConversationState = None) -> Intent:
        """Extrait l'intention principale du message"""
        msg_lower = message.lower()

        # 0. PRIORITÉ MAXIMALE: Vérifier pickup/localisation AVANT l'acceptation
        # Car "oui oui mais je veux passer recuperer" n'est PAS une acceptation,
        # c'est un choix de pickup. Fonctionne depuis tout état de négociation.
        negotiation_states = {
            ConversationState.DEAL_AGREED,
            ConversationState.PRICE_PRESENTED,
            ConversationState.NEGOTIATING,
            ConversationState.COUNTER_OFFER,
            ConversationState.FINAL_OFFER,
        }
        if current_state in negotiation_states:
            if self._is_pickup_request(msg_lower):
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

        # Si marqueurs d'objection + prix mentionné = c'est une objection, pas une offre
        price = self._extract_price(message)
        if price and has_objection_markers:
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

        # 2. Acceptation
        if self._is_acceptance(msg_lower):
            return Intent(
                event=ConversationEvent.ACCEPT_OFFER,
                confidence=0.9,
                extracted_data={}
            )

        # 3. Demande de livraison (avec contexte)
        delivery_result = self._check_delivery_request(msg_lower, context)
        if delivery_result:
            return delivery_result

        # 4. Demande de pickup/localisation
        if self._is_pickup_request(msg_lower):
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

        # 10. Expression d'intérêt (défaut si message court)
        if len(message) < 50 or self._shows_interest(msg_lower):
            return Intent(
                event=ConversationEvent.EXPRESS_INTEREST,
                confidence=0.6,
                extracted_data={}
            )

        # Défaut: premier message ou intérêt général
        return Intent(
            event=ConversationEvent.FIRST_MESSAGE,
            confidence=0.5,
            extracted_data={}
        )

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
        """Détecte si le client accepte"""
        exact_accepts = [
            'ok', 'oui', 'deal', 'vendu', 'marché', 'adjugé',
            'd\'accord', 'daccord', 'je prends', 'je le prends',
            'ça marche', 'ca marche', 'c\'est bon', 'parfait',
            'on fait comme ça', 'je suis d\'accord', 'je valide',
            'je veux', 'je le veux', 'je la veux'
        ]

        # Message court d'acceptation
        if msg.strip() in exact_accepts:
            return True

        # Phrases d'acceptation au début
        for accept in exact_accepts:
            if msg.startswith(accept):
                return True

        # "je prends" ou "je veux" sans négation
        for phrase in ['je prends', 'je veux']:
            if phrase in msg and 'pas' not in msg:
                exclusions = ['soin', 'note', 'en compte', 'le temps', 'savoir', 'dire']
                if not any(excl in msg for excl in exclusions):
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
        delivery_requests = [
            'je veux la livraison', 'livraison svp', 'livraison stp',
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
        """Détecte une demande de pickup"""
        pickup_keywords = [
            'je viens', 'je passe', 'passer chercher', 'viens chercher',
            'récupérer', 'recuperer', 'sur place', 'en personne',
            'moi-même', 'moi même', 'je me déplace', 'je me deplace'
        ]
        return any(kw in msg for kw in pickup_keywords)

    def _is_location_request(self, msg: str) -> bool:
        """Détecte une demande de localisation du magasin"""
        # Phrases explicites de demande d'adresse
        explicit_location = [
            'c\'est où', 'c\'est ou', 'vous êtes où', 'tu es où',
            'où se trouve', 'ou se trouve', 'où est le magasin',
            'adresse du magasin', 'localisation', 'position du magasin',
            'position de la boutique', 'envoie la position',
            'envoie moi la position', 'la position', 'avoir la position',
            'où je peux venir', 'je viens où',
            'comment venir', 'situé où', 'situe ou', 'situer',
            'ou c\'est', 'ou c est'
        ]

        if any(loc in msg for loc in explicit_location):
            return True

        # "magasin" ou "boutique" seuls ne suffisent pas
        # Il faut une question ou une demande
        if ('magasin' in msg or 'boutique' in msg) and ('?' in msg or 'où' in msg or 'ou' in msg):
            return True

        return False

    def _extract_address(self, message: str) -> Optional[str]:
        """Extrait une adresse du message"""
        msg_lower = message.lower()

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
            'moins cher ailleurs', 'ailleurs moins cher', 'concurrent'
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
        trust_objections = [
            'confiance', 'arnaque', 'peur', 'méfiant', 'sûr', 'sur'
        ]
        if any(obj in msg for obj in trust_objections):
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
            'voleur', 'arnaque', 'escroc', 'menteur', 'idiot',
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
        """Détecte une fin de conversation"""
        goodbyes = [
            'bye', 'au revoir', 'ciao', 'non merci', 'pas intéressé',
            'pas interesse', 'laisse tomber', 'laisse'
        ]

        # Seulement si c'est le message principal (court)
        if len(msg) < 30:
            return msg.strip() in goodbyes or any(g in msg for g in goodbyes)

        return False

    def _is_price_question(self, msg: str) -> bool:
        """Détecte une question sur le prix"""
        price_questions = [
            'combien', 'prix', 'coûte', 'coute', 'c\'est à combien',
            'ça fait combien', 'ca fait combien', 'le tarif'
        ]
        return any(pq in msg for pq in price_questions)

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
        """Charge les templates de réponses par situation"""
        return {
            # === Salutations (premier message uniquement) ===
            "greeting_first": [
                "Salut! Oui c'est disponible à {price} F. Ça t'intéresse?",
                "Hey! Oui le {product} est là à {price} F. Tu veux?",
                "Coucou! Oui c'est dispo. {price} F. Ça te dit?"
            ],

            # === Prix présenté (pas de salutation) ===
            "price_presented": [
                "C'est {price} F. Tu veux qu'on discute?",
                "{price} F pour celui-là. Ça t'intéresse?",
                "Le prix c'est {price} F. On peut négocier!"
            ],

            # === Acceptation de l'offre ===
            "offer_accepted": [
                "OK {client_price} F c'est bon! Tu veux la livraison ou tu passes chercher?",
                "Ça marche pour {client_price} F! Livraison ou tu viens?",
                "Deal à {client_price} F! Tu préfères livraison ou pickup?"
            ],

            # === Contre-offre ===
            "counter_offer": [
                "Ah {client_price} F c'est un peu bas! On dit {counter} F et c'est bon?",
                "{client_price} F je peux pas... Allez {counter} F et on se comprend!",
                "Pour {client_price} F c'est chaud! Dernier prix {counter} F."
            ],

            # === Dernier prix ===
            "final_offer": [
                "Écoute, {price} F c'est vraiment mon DERNIER prix. À prendre ou à laisser!",
                "Je fais un effort énorme: {price} F point final. C'est le prix du patron!",
                "Bon, {price} F et on arrête là. C'est mon minimum!"
            ],

            # === Fin de négociation (refus persistant) ===
            "negotiation_ended": [
                "J'ai fait mon maximum. Je peux vraiment pas descendre plus. Reviens quand tu veux!",
                "C'est vraiment mon dernier prix. Si ça te va pas, pas de souci!",
                "J'ai atteint ma limite. Reviens pour d'autres produits!"
            ],

            # === Client frustré ===
            "frustrated_empathy": [
                "Je comprends que ça puisse sembler cher, mais c'est vraiment de la qualité!",
                "Écoute, je suis désolé si ça te semble élevé. C'est quoi ton budget?",
                "Je comprends ta réaction. Dis-moi ce qui te conviendrait?"
            ],

            # === Objection prix ===
            "objection_price": [
                "Je comprends! Dis-moi ton budget et on voit ce qu'on peut faire.",
                "C'est de la bonne qualité, mais je peux faire un effort. Tu proposes combien?",
                "Je comprends que c'est un investissement. Fais-moi une offre!"
            ],

            # === Objection qualité ===
            "objection_quality": [
                "C'est du {product} original, qualité garantie!",
                "Je te garantis la qualité. Si y'a un souci, tu reviens me voir!",
                "C'est du vrai, pas de la copie. Tu peux vérifier!"
            ],

            # === Objection confiance ===
            "objection_trust": [
                "Je comprends ta méfiance. Je suis un vendeur sérieux!",
                "Pas de souci, tu peux vérifier le produit avant de payer.",
                "On peut faire cash à la livraison si tu préfères!"
            ],

            # === Objection timing ===
            "objection_timing": [
                "Pas de problème, prends ton temps! Je garde le produit.",
                "OK réfléchis bien. Je reste dispo quand tu veux!",
                "Aucun souci! Tu me recontactes quand tu es prêt."
            ],

            # === Choix livraison ===
            "ask_delivery_choice": [
                "Tu préfères la livraison ou tu passes au magasin?",
                "Livraison ou tu viens chercher?",
                "Comment tu veux faire? Livraison ou pickup?"
            ],

            # === Demande d'adresse ===
            "ask_address": [
                "Super! Envoie-moi ton adresse et numéro pour la livraison.",
                "OK pour la livraison! C'est où pour toi? Donne-moi l'adresse.",
                "Livraison c'est noté! Ton adresse et numéro stp?"
            ],

            # === Adresse reçue ===
            "address_received": [
                "Parfait! Je note. On te contacte pour organiser la livraison.",
                "C'est noté! Le vendeur te rappelle pour la livraison.",
                "Super! Tu seras contacté rapidement pour la livraison."
            ],

            # === Localisation envoyée ===
            "location_sent": [
                "Je t'envoie la localisation!",
                "Voici l'adresse du magasin!",
                "Tiens, c'est ici!"
            ],

            # === Attente pickup ===
            "pending_pickup": [
                "On t'attend au magasin!",
                "À tout à l'heure alors!",
                "Parfait, à bientôt!"
            ],

            # === Questions générales ===
            "general_question": [
                "Tu veux savoir quoi exactement?",
                "Je t'écoute! Qu'est-ce que tu veux savoir?",
                "Dis-moi ce qui t'intéresse!"
            ],

            # === Relance douce ===
            "soft_follow_up": [
                "Alors, ça t'intéresse?",
                "Tu veux qu'on procède?",
                "Des questions?"
            ]
        }

    def generate(
        self,
        state: ConversationState,
        sentiment: SentimentAnalysis,
        negotiation: NegotiationContext,
        intent: Intent,
        memory: ConversationMemory
    ) -> str:
        """
        Génère une réponse appropriée basée sur tous les contextes.
        """
        # Variables de contexte
        context = {
            "product": negotiation.product_name,
            "price": f"{negotiation.listed_price:,.0f}".replace(",", " "),
            "min_price": f"{negotiation.min_price:,.0f}".replace(",", " "),
            "client_price": f"{negotiation.current_offer:,.0f}".replace(",", " ") if negotiation.current_offer else "",
        }

        # Sélectionner le template selon l'état
        template_key = self._select_template_key(state, sentiment, intent, negotiation, memory)

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
        memory: ConversationMemory
    ) -> str:
        """Sélectionne la clé de template appropriée"""

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
        current_offer: Optional[float] = None
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

        # 5. Extraire l'intention (passer l'état courant pour prioriser pickup/delivery en DEAL_AGREED)
        intent = self.intent_extractor.extract(client_message, memory, current_state=fsm_state)

        # 6. Enregistrer l'offre si présente
        if intent.event == ConversationEvent.PRICE_OFFER:
            price_offered = intent.extracted_data.get("price")
            if price_offered:
                negotiation.record_client_offer(price_offered)

                # Vérifier si l'offre est acceptable
                if price_offered >= negotiation.min_price:
                    intent = Intent(
                        event=ConversationEvent.ACCEPT_OFFER,
                        confidence=0.95,
                        extracted_data={"price": price_offered, "auto_accepted": True}
                    )

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
            memory=memory
        )

        # 9. Déterminer les flags de sortie
        deal_accepted = new_state_enum in [
            ConversationState.DEAL_AGREED,
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
                "is_final_price_mode": negotiation.is_final_price_mode
            }
        }

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
