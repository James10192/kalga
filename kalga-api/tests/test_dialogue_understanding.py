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


# === Demandes visuelles & produits ===
from app.services.dialogue.understanding import detect_visual_intents


def test_photo_request():
    for msg in ("envoie la photo", "tu as une image ?", "montre-moi",
                "je peux voir le produit ?", "à quoi ça ressemble"):
        intents = detect_visual_intents(msg.lower())
        assert Intent(IntentType.ASK_PHOTO) in intents, msg


def test_other_photos_request():
    for msg in ("je veux d'autres photos", "je peux avoir d'autre photo",
                "envoie moi plus de photos"):
        intents = detect_visual_intents(msg.lower())
        assert Intent(IntentType.ASK_OTHER_PHOTOS) in intents, msg


def test_variants_request():
    for msg in ("tu as d'autres couleurs ?", "il existe en rouge ?",
                "autre taille ?", "autre modèle ?"):
        intents = detect_visual_intents(msg.lower())
        assert Intent(IntentType.ASK_VARIANTS) in intents, msg


def test_other_products_request():
    for msg in ("tu vends quoi d'autre ?", "vous avez autre chose ?",
                "montre ton catalogue"):
        intents = detect_visual_intents(msg.lower())
        assert Intent(IntentType.ASK_OTHER_PRODUCTS) in intents, msg


def test_location_send_is_not_a_photo():
    assert detect_visual_intents("envoie moi la localisation") == []


def test_variant_beats_photo_for_same_phrase():
    # « d'autres couleurs » ne doit pas déclencher ASK_PHOTO en plus
    intents = detect_visual_intents("tu as d'autres couleurs ?")
    assert Intent(IntentType.ASK_PHOTO) not in intents


# === Logistique, social & signaux ===
from app.services.dialogue.understanding import detect_logistics_intents, detect_signal_intents


def test_location_request():
    for msg in ("où vous êtes ?", "l'adresse ?", "envoie la localisation",
                "c'est où le magasin ?"):
        assert Intent(IntentType.ASK_LOCATION) in detect_logistics_intents(msg.lower(), None), msg


def test_payment_request():
    for msg in ("comment payer ?", "orange money ?", "wave ?", "numéro de paiement"):
        assert Intent(IntentType.ASK_PAYMENT) in detect_logistics_intents(msg.lower(), None), msg


def test_delivery_info_question_vs_choice():
    # Question sur la livraison ≠ choix de la livraison
    q = detect_logistics_intents("c'est combien la livraison ?", None)
    assert Intent(IntentType.ASK_DELIVERY_INFO) in q
    assert Intent(IntentType.CHOOSE_DELIVERY) not in q

    c = detect_logistics_intents("je veux me faire livrer", None)
    assert Intent(IntentType.CHOOSE_DELIVERY) in c


def test_pickup_choice():
    for msg in ("je viens chercher", "je passe au magasin", "je vais venir sur place"):
        assert Intent(IntentType.CHOOSE_PICKUP) in detect_logistics_intents(msg.lower(), None), msg


def test_give_address_when_bot_asked():
    intents = detect_logistics_intents(
        "cocody angré 7e tranche, près de la pharmacie",
        "Parfait ! Donne-moi ton adresse de livraison ?",
    )
    assert any(i.type == IntentType.GIVE_ADDRESS and "cocody" in i.text for i in intents)


def test_no_give_address_without_bot_asking():
    intents = detect_logistics_intents("cocody angré 7e tranche", None)
    assert all(i.type != IntentType.GIVE_ADDRESS for i in intents)


def test_greeting():
    for msg in ("hello", "salut", "bonjour", "bonsoir", "cc"):
        assert Intent(IntentType.GREETING) in detect_signal_intents(msg.lower()), msg


def test_goodbye_restrictive():
    assert Intent(IntentType.GOODBYE) in detect_signal_intents("bye")
    assert Intent(IntentType.GOODBYE) in detect_signal_intents("merci bye")
    assert Intent(IntentType.GOODBYE) in detect_signal_intents("laisse tomber")
    # Jamais GOODBYE si signe d'intérêt
    assert detect_signal_intents("bye, mais c'est combien ?") == []


def test_frustration():
    assert Intent(IntentType.FRUSTRATION) in detect_signal_intents("tu te moques de moi, voleur !")


def test_correction():
    assert Intent(IntentType.CORRECTION) in detect_signal_intents("c'est pas ce que j'ai demandé")


def test_human_request():
    for msg in ("je veux parler à quelqu'un", "passez-moi un responsable",
                "je veux parler au vendeur directement"):
        assert Intent(IntentType.HUMAN_REQUEST) in detect_signal_intents(msg.lower()), msg
