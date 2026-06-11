"""Tests du garde-fou déterministe accept_deal (resolve_accept_deal).

Reproduit le bug terrain : sur « Je veux ça à 9000 et envoie moi plus de photo »
le bot concluait la vente (pending_pickup + localisation + goodbye) au lieu
d'envoyer la photo / négocier. Le garde-fou doit bloquer la clôture.
"""
from app.services.ai.deal_guard import resolve_accept_deal, is_explicit_photo_request


def test_explicit_photo_request_true():
    assert is_explicit_photo_request("je veux des photos") is True
    assert is_explicit_photo_request("envoie la photo") is True
    assert is_explicit_photo_request("montre moi") is True


def test_explicit_photo_request_false_on_variant():
    # demande d'AUTRES couleurs → géré ailleurs, pas une photo du produit actuel
    assert is_explicit_photo_request("tu as d'autres couleurs ?") is False


def test_explicit_photo_request_false_on_location():
    assert is_explicit_photo_request("envoie moi la localisation") is False


def test_explicit_photo_request_false_on_acceptance():
    assert is_explicit_photo_request("ok je prends") is False
    assert is_explicit_photo_request("je veux ça à 18K") is False


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


# === Intégration : la demande photo est honorée même en phase de clôture ===
# (reproduit la 2e capture : « je veux des photos » ignoré une fois le prix accepté)

async def test_generate_response_honors_photo_request_at_agreed():
    """En état 'agreed', « je veux des photos » → send_photo, PAS la livraison.

    Le chemin d'interception est en amont de KB/STM/DeepSeek : aucun appel LLM
    ni DB n'est nécessaire (retour déterministe).
    """
    from app.services.ai.conversation_ai import generate_response

    product = {"name": "Fleur", "price": 20000, "min_price": 16000, "image_path": "fleur.jpg"}
    history = [
        {"content": "hello", "is_from_client": True},
        {"content": "Salut! C'est le Fleur à 20 000 F.", "is_from_client": False},
        {"content": "je veux ça à 18K", "is_from_client": True},
        {"content": "Banco à 18 000 F! On fait comment pour la livraison?", "is_from_client": False},
    ]
    resp, offer, accepted, status, send_location, use_voice = await generate_response(
        client_message="je veux des photos",
        product=product,
        conversation_history=history,
        current_offer=18000,
        conversation_status="agreed",
    )
    assert resp.startswith("__tool__:send_photo"), f"attendu send_photo, obtenu: {resp[:60]}"
    assert send_location is False
