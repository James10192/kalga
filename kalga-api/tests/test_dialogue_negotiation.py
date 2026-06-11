"""Tests du calcul de négociation (pur, déterministe)."""
from app.services.dialogue.negotiation import decide, NegotiationDecision


def test_offer_at_or_above_ask_accepts_at_offer_capped_to_listed():
    d = decide(client_offer=10000, listed_price=10000, floor_price=8000, last_bot_price=None)
    assert d.kind == "accept" and d.price == 10000


def test_offer_above_listed_is_capped():
    d = decide(client_offer=12000, listed_price=10000, floor_price=8000, last_bot_price=None)
    assert d.kind == "accept" and d.price == 10000


def test_offer_between_floor_and_ask_accepts_at_offer():
    # Décision marchand : un prix ≥ plancher est un deal — on ne le risque pas
    d = decide(client_offer=9000, listed_price=10000, floor_price=8000, last_bot_price=None)
    assert d.kind == "accept" and d.price == 9000


def test_low_offer_counters_midway_rounded_500():
    # ask=10000, max(offre,plancher)=8000 → milieu 9000
    d = decide(client_offer=5000, listed_price=10000, floor_price=8000, last_bot_price=None)
    assert d.kind == "counter" and d.price == 9000


def test_counter_decreases_across_rounds_until_floor():
    # Tour 2 : ask=9000 → milieu (9000+8000)/2 = 8500
    d = decide(client_offer=5000, listed_price=10000, floor_price=8000, last_bot_price=9000)
    assert d.kind == "counter" and d.price == 8500
    # Tour 3 : ask=8500 → milieu 8250 → arrondi 500 = 8000 (plancher, pas en dessous)
    d = decide(client_offer=5000, listed_price=10000, floor_price=8000, last_bot_price=8500)
    assert d.kind == "counter" and d.price == 8000


def test_at_floor_holds_forever():
    # Déjà au plancher → on TIENT, sans limite de tours (décision marchand)
    d = decide(client_offer=5000, listed_price=10000, floor_price=8000, last_bot_price=8000)
    assert d.kind == "hold_floor" and d.price == 8000


def test_objection_without_amount_concedes_midway_to_floor():
    d = decide(client_offer=None, listed_price=10000, floor_price=8000, last_bot_price=None)
    assert d.kind == "counter" and d.price == 9000


def test_objection_at_floor_holds():
    d = decide(client_offer=None, listed_price=10000, floor_price=8000, last_bot_price=8000)
    assert d.kind == "hold_floor" and d.price == 8000


def test_counter_never_below_floor():
    d = decide(client_offer=7900, listed_price=8200, floor_price=8000, last_bot_price=None)
    assert d.price >= 8000
