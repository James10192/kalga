"""
Étage ③ — Décision de négociation (spec §8). 100 % code, 0 % LLM.

Règles (validées par le marchand) :
- offre ≥ prix demandé → accepter (plafonné au prix affiché : jamais surfacturer) ;
- offre ≥ plancher → accepter à l'offre (un deal au-dessus du plancher ne se risque pas) ;
- offre < plancher → contre-offre au milieu entre le prix demandé et
  max(offre, plancher), arrondie commerçant (500 F), jamais sous le plancher —
  concessions naturellement décroissantes, convergence vers le plancher ;
- déjà au plancher → TENIR, sans limite de tours (« jusqu'à l'entente ») ;
  la variation des formulations est l'affaire de la parole (P3).
"""
from dataclasses import dataclass
from typing import Optional

_ROUND_STEP = 500


@dataclass(frozen=True)
class NegotiationDecision:
    kind: str          # "accept" | "counter" | "hold_floor"
    price: float


def _round_commercant(price: float) -> float:
    return round(price / _ROUND_STEP) * _ROUND_STEP


def decide(
    client_offer: Optional[float],
    listed_price: float,
    floor_price: float,
    last_bot_price: Optional[float],
) -> NegotiationDecision:
    ask = last_bot_price if last_bot_price is not None else listed_price

    if client_offer is not None:
        if client_offer >= ask:
            return NegotiationDecision("accept", min(client_offer, listed_price))
        if client_offer >= floor_price:
            return NegotiationDecision("accept", float(client_offer))

    # Offre basse ou objection sans chiffre → concession vers le plancher
    if ask <= floor_price:
        return NegotiationDecision("hold_floor", float(floor_price))

    anchor = max(client_offer or floor_price, floor_price)
    target = max(floor_price, _round_commercant((ask + anchor) / 2))
    if target >= ask:  # l'arrondi ne doit jamais remonter le prix
        target = max(floor_price, ask - _ROUND_STEP)
    return NegotiationDecision("counter", float(target))
