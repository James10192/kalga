"""
KALGA Conversation Engine — Orchestrator
==========================================
Moteur de conversation principal et instance globale.
"""

import re
import logging
from typing import Optional, List, Dict, Any

from .states import ConversationState, ConversationEvent, ConversationFSM
from .memory import ConversationMemory
from .sentiment import SentimentAnalyzer
from .intent import Intent, IntentExtractor
from .negotiation import NegotiationContext
from .response_generator import ResponseGenerator

logger = logging.getLogger("kalga.conversation_engine")


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
