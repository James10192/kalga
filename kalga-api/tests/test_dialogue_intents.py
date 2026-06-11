"""Tests du catalogue d'intentions fermé."""
from app.services.dialogue.intents import Intent, IntentType, PRIORITY


def test_catalog_is_closed_and_complete():
    expected = {
        "GREETING", "ASK_INFO", "ASK_PHOTO", "ASK_OTHER_PHOTOS", "ASK_VARIANTS",
        "ASK_OTHER_PRODUCTS", "ASK_LOCATION", "ASK_PAYMENT", "ASK_DELIVERY_INFO",
        "PRICE_OFFER", "ACCEPT_PRICE", "CHOOSE_DELIVERY", "CHOOSE_PICKUP",
        "GIVE_ADDRESS", "GOODBYE", "FRUSTRATION", "CORRECTION", "HUMAN_REQUEST",
        "UNCLEAR",
    }
    assert {t.name for t in IntentType} == expected


def test_every_intent_type_has_a_priority():
    assert set(PRIORITY) == set(IntentType)


def test_requests_rank_before_transactions():
    # Les demandes client passent avant la mécanique de vente (spec §7)
    assert PRIORITY[IntentType.ASK_PHOTO] < PRIORITY[IntentType.PRICE_OFFER]
    assert PRIORITY[IntentType.ASK_VARIANTS] < PRIORITY[IntentType.ACCEPT_PRICE]
    assert PRIORITY[IntentType.CORRECTION] < PRIORITY[IntentType.ASK_PHOTO]


def test_intent_is_frozen_and_hashable():
    a = Intent(IntentType.PRICE_OFFER, amount=9000)
    b = Intent(IntentType.PRICE_OFFER, amount=9000)
    assert a == b
    assert len({a, b}) == 1


def test_intent_optional_fields_default_none():
    i = Intent(IntentType.GREETING)
    assert i.amount is None and i.text is None
