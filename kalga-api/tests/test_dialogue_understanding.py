"""Tests des règles d'extraction — prix et acceptation."""
from app.services.dialogue.intents import Intent, IntentType
from app.services.dialogue.understanding import (
    extract_price_amount,
    detect_price_intents,
)


# --- extract_price_amount : extraction robuste d'un montant FCFA ---

def test_amount_k_suffix():
    assert extract_price_amount("je veux ça à 18K") == 18000.0


def test_amount_spaced_thousands():
    assert extract_price_amount("je te donne 15 000") == 15000.0


def test_amount_plain():
    assert extract_price_amount("9000 et on est bons") == 9000.0


def test_amount_with_currency_word():
    assert extract_price_amount("10000 fcfa dernier prix") == 10000.0


def test_no_amount_returns_none():
    assert extract_price_amount("c'est trop cher") is None


def test_product_code_is_not_an_amount():
    # #K053 ne doit jamais devenir une offre de prix
    assert extract_price_amount("je parle du K053") is None


# --- detect_price_intents : (message_normalisé, last_bot_message) -> list[Intent] ---

def test_offer_with_amount():
    intents = detect_price_intents("je veux ça à 9000", None)
    assert Intent(IntentType.PRICE_OFFER, amount=9000.0) in intents


def test_price_objection_without_amount():
    intents = detect_price_intents("c'est trop cher, fais un effort", None)
    assert Intent(IntentType.PRICE_OFFER) in intents


def test_explicit_priced_acceptance_is_accept_not_offer():
    intents = detect_price_intents("ok pour 18 000", None)
    assert Intent(IntentType.ACCEPT_PRICE, amount=18000.0) in intents
    assert all(i.type != IntentType.PRICE_OFFER for i in intents)


def test_strong_acceptance_without_amount():
    for msg in ("ok je prends", "banco", "deal", "vendu", "marché conclu"):
        intents = detect_price_intents(msg, None)
        assert Intent(IntentType.ACCEPT_PRICE) in intents, msg


def test_weak_ok_with_priced_bot_context_is_acceptance():
    intents = detect_price_intents("ok", "Je peux faire 9 500 F, ça marche ?")
    assert Intent(IntentType.ACCEPT_PRICE) in intents


def test_weak_ok_without_priced_context_is_nothing():
    # « Oui » à « ça t'intéresse ? » → AUCUNE intention transactionnelle
    assert detect_price_intents("oui", "Ça t'intéresse ?") == []


def test_je_prends_soin_is_not_acceptance():
    assert detect_price_intents("je prends soin de mes affaires", None) == []


def test_question_price_is_still_an_offer():
    # « tu peux faire 9000 ? » est bien une offre à négocier
    intents = detect_price_intents("tu peux faire 9000 ?", None)
    assert Intent(IntentType.PRICE_OFFER, amount=9000.0) in intents
