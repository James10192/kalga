"""
KALGA Conversation Engine — Negotiation
=========================================
Contexte et logique de négociation intelligente.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List

logger = logging.getLogger("kalga.conversation_engine")


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
