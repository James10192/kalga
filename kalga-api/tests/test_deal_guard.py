"""Tests du garde-fou déterministe accept_deal (resolve_accept_deal).

Reproduit le bug terrain : sur « Je veux ça à 9000 et envoie moi plus de photo »
le bot concluait la vente (pending_pickup + localisation + goodbye) au lieu
d'envoyer la photo / négocier. Le garde-fou doit bloquer la clôture.
"""
from app.services.ai.deal_guard import resolve_accept_deal


def test_bug_scenario_photo_request_blocks_close():
    """Le scénario exact de la capture : contre-offre + demande photo → on NE clôt PAS."""
    override = resolve_accept_deal(
        client_message="Je veux ça à 9000 et envoie moi plus de photo",
        current_offer=10000,
        min_price=8000,
        listed_price=10000,
    )
    assert override is not None
    # La demande de photo est prioritaire : on laisse le client « aller au bout »
    assert override["name"] == "send_photo"


def test_photo_request_alone_blocks_close():
    override = resolve_accept_deal(
        client_message="envoie moi plus de photo",
        current_offer=10000, min_price=8000, listed_price=10000,
    )
    assert override is not None and override["name"] == "send_photo"


def test_variant_request_blocks_close():
    override = resolve_accept_deal(
        client_message="tu as d'autres couleurs ?",
        current_offer=10000, min_price=8000, listed_price=10000,
    )
    assert override is not None and override["name"] == "send_variants"


def test_counter_below_min_routes_to_min():
    override = resolve_accept_deal(
        client_message="je te donne 5000",
        current_offer=10000, min_price=8000, listed_price=10000,
    )
    assert override is not None
    assert override["name"] == "counter_offer"
    assert override["args"]["price"] == 8000  # ramené au minimum


def test_counter_between_min_and_current_meets_client():
    override = resolve_accept_deal(
        client_message="je veux ça à 9000",
        current_offer=10000, min_price=8000, listed_price=10000,
    )
    assert override is not None
    assert override["name"] == "counter_offer"
    assert override["args"]["price"] == 9000  # on rejoint l'offre (>= min)


def test_clean_acceptance_allows_close():
    """« ok je prends » sans intention concurrente → la clôture est autorisée."""
    override = resolve_accept_deal(
        client_message="ok je prends",
        current_offer=10000, min_price=8000, listed_price=10000,
    )
    assert override is None


def test_bare_oui_allows_close():
    """« Oui » seul : le garde-fou ne bloque pas (défaut A traité par le prompt)."""
    override = resolve_accept_deal(
        client_message="Oui",
        current_offer=10000, min_price=8000, listed_price=10000,
    )
    assert override is None


def test_pickup_acceptance_allows_close():
    """« ok je viens chercher » → clôture pickup légitime, pas de blocage."""
    override = resolve_accept_deal(
        client_message="ok je viens chercher",
        current_offer=10000, min_price=8000, listed_price=10000,
    )
    assert override is None


def test_send_location_phrasing_not_misread_as_photo():
    """« envoie moi la localisation » ne doit PAS être pris pour une demande photo."""
    override = resolve_accept_deal(
        client_message="ok je prends, envoie moi la localisation",
        current_offer=10000, min_price=8000, listed_price=10000,
    )
    # Pas de token visuel → pas de send_photo ; pas de contre-offre → clôture autorisée
    assert override is None


def test_offer_at_or_above_reference_allows_close():
    """Offre >= prix courant → ce n'est pas une contre-offre à la baisse."""
    override = resolve_accept_deal(
        client_message="ok pour 10000",
        current_offer=10000, min_price=8000, listed_price=10000,
    )
    assert override is None
