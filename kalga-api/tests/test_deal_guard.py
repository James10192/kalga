"""Tests du garde-fou déterministe accept_deal (resolve_accept_deal).

Reproduit le bug terrain : sur « Je veux ça à 9000 et envoie moi plus de photo »
le bot concluait la vente (pending_pickup + localisation + goodbye) au lieu
d'envoyer la photo / négocier. Le garde-fou doit bloquer la clôture.
"""
from app.services.ai.deal_guard import (
    resolve_accept_deal,
    is_explicit_photo_request,
    wants_other_photos,
    strip_context_prefix,
)


# === Assainissement des préfixes de contexte (bridge/système) ===
# Bug terrain : « hello » en réponse à un Statut arrive comme
# [Répond à la photo: "#K053"] Hello → le mot « photo » de la MÉTADONNÉE
# déclenchait send_photo. Les détecteurs ne doivent voir que les mots du client.

def test_strip_context_prefix_removes_bridge_reply():
    assert strip_context_prefix('[Répond à la photo: "#K053"] Hello') == "Hello"


def test_strip_context_prefix_removes_voice_prefix():
    assert strip_context_prefix("[🎤 Vocal transcrit (fr)]: je veux la photo") == "je veux la photo"


def test_strip_context_prefix_plain_message_untouched():
    assert strip_context_prefix("je veux la photo") == "je veux la photo"


def test_hello_replying_to_status_does_not_trigger_photo():
    """Le scénario exact de la capture : « hello » sur un Statut → PAS de photo."""
    assert is_explicit_photo_request('[Répond à la photo: "#K053"] Hello') is False


def test_real_photo_request_with_prefix_still_triggers():
    assert is_explicit_photo_request('[Répond à la photo: "Modèle X"] je veux la photo') is True


def test_resolve_accept_deal_ignores_bridge_prefix():
    """« ok je prends » en réponse à un Statut ne doit pas être rétrogradé en photo."""
    override = resolve_accept_deal(
        client_message='[Répond à la photo: "#K053"] ok je prends',
        current_offer=10000, min_price=8000, listed_price=10000,
    )
    assert override is None


# === « d'autres photos » doit être honoré (capture 2) ===

def test_wants_other_photos_true():
    assert wants_other_photos("Je veux d'autres photos") is True
    assert wants_other_photos("Je peux avoir d'autre photo") is True


def test_wants_other_photos_false_for_pure_variant_request():
    # « d'autres couleurs » sans mot visuel → flux variantes normal (pas photo)
    assert wants_other_photos("tu as d'autres couleurs ?") is False


def test_wants_other_photos_false_for_simple_acceptance():
    assert wants_other_photos("ok je prends") is False


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


async def test_generate_response_other_photos_with_variants_sends_variants():
    """Capture 2 : « Je veux d'autres photos » + le produit A des variantes → send_variants."""
    from app.services.ai.conversation_ai import generate_response

    product = {"name": "Chemise", "price": 10000, "min_price": 8000,
               "image_path": "chemise.jpg", "group_id": "GRP-X1"}
    history = [
        {"content": "hello", "is_from_client": True},
        {"content": "Salut! C'est la Chemise à 10 000 F.", "is_from_client": False},
    ]
    resp, *_ = await generate_response(
        client_message="Je veux d'autres photos",
        product=product,
        conversation_history=history,
        current_offer=None,
        conversation_status="active",
    )
    assert resp.startswith("__tool__:send_variants"), f"attendu send_variants, obtenu: {resp[:60]}"


async def test_generate_response_other_photos_without_variants_resends_photo():
    """« Je veux d'autres photos » sans variantes → on renvoie la photo (honnêtement)."""
    from app.services.ai.conversation_ai import generate_response

    product = {"name": "Chemise", "price": 10000, "min_price": 8000,
               "image_path": "chemise.jpg", "group_id": None}
    history = [
        {"content": "hello", "is_from_client": True},
        {"content": "Salut! C'est la Chemise à 10 000 F.", "is_from_client": False},
    ]
    resp, *_ = await generate_response(
        client_message="Je veux d'autres photos",
        product=product,
        conversation_history=history,
        current_offer=None,
        conversation_status="active",
    )
    assert resp.startswith("__tool__:send_photo"), f"attendu send_photo, obtenu: {resp[:60]}"


async def test_generate_response_hello_with_status_prefix_goes_to_llm_not_photo():
    """Capture 1 : « hello » sur un Statut ne doit PAS court-circuiter vers la photo.

    Sans clé API DeepSeek en test, le flux tombe sur le moteur fallback → la
    réponse ne doit en aucun cas être un tool send_photo déterministe.
    """
    from app.services.ai.conversation_ai import generate_response

    product = {"name": "Chemise", "price": 10000, "min_price": 8000, "image_path": "c.jpg"}
    resp, *_ = await generate_response(
        client_message='[Répond à la photo: "#K053"] Hello',
        product=product,
        conversation_history=[{"content": "hello", "is_from_client": True}],
        current_offer=None,
        conversation_status="active",
    )
    assert resp is None or not str(resp).startswith("__tool__:send_photo"), \
        f"la photo ne doit pas partir sur un simple hello: {str(resp)[:60]}"
