"""
KALGA Conversation Engine — States & FSM
=========================================
Machine à états finis (FSM) pour le flux de conversation.
"""

import logging
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger("kalga.conversation_engine")


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
