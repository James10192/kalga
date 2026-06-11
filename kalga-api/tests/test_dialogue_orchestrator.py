"""Tests de l'orchestrateur — le chef d'orchestre mince ①→⑤."""
from app.services.dialogue.llm_protocol import FakeLLMClient
from app.services.dialogue.orchestrator import run_pipeline
from app.services.dialogue.sale_state import SaleState


def _product(**kw):
    p = {"name": "Sac", "price": 10000.0, "min_price": 8000.0,
         "image_path": "sac.jpg", "group_id": None}
    p.update(kw)
    return p


async def test_pipeline_photo_request_returns_plan_and_text():
    result = await run_pipeline(
        client_message="envoie la photo",
        db_status="negotiating", history=[
            {"content": "9000", "is_from_client": True},
            {"content": "Je peux faire 9 500 F", "is_from_client": False},
        ],
        product=_product(), current_offer=None, llm=None,
    )
    assert result is not None
    assert result.plan.new_state == SaleState.NEGOCIATION
    assert "photo" in result.text.lower()
    assert result.db_status == "negotiating"


async def test_pipeline_unclear_uses_llm_classifier():
    # « le truc là même hum » : aucun mot-clé, pas de « ? » → UNCLEAR → classifieur
    fake = FakeLLMClient(classify_result=[{"type": "ask_photo"}])
    result = await run_pipeline(
        client_message="le truc là même hum",
        db_status="active", history=[{"content": "x", "is_from_client": True}] * 3,
        product=_product(), current_offer=None, llm=fake,
    )
    assert any(a.type.value == "send_photo" for a in result.plan.actions)
    assert fake.classify_calls  # le classifieur a bien été sollicité


async def test_pipeline_system_only_message_returns_none():
    result = await run_pipeline(
        client_message="[📸 Le client a envoyé une photo.]",
        db_status="active", history=[], product=_product(),
        current_offer=None, llm=None,
    )
    assert result is None      # → le chemin v1 garde la main


async def test_pipeline_classifier_can_never_close_a_deal():
    """Règle marchand : un message AMBIGU ne conclut jamais — même si le
    classifieur LLM (faillible) prétend que c'est une acceptation."""
    rogue = FakeLLMClient(classify_result=[{"type": "accept_price"}])
    result = await run_pipeline(
        client_message="le machin là même",   # ambigu, sans mot-clé
        db_status="negotiating",
        history=[{"content": "Je peux te faire 18 000 F !", "is_from_client": False}],
        product=_product(), current_offer=18000.0, llm=rogue,
    )
    assert all(a.type.value != "confirm_deal" for a in result.plan.actions)
    assert result.db_status == "negotiating"


async def test_pipeline_classifier_can_never_end_conversation():
    """Terrain 15:16 : « Je t'en prie » classé au revoir → client muré.
    Un message ambigu ne clôt JAMAIS la conversation."""
    rogue = FakeLLMClient(classify_result=[{"type": "goodbye"}])
    result = await run_pipeline(
        client_message="je t'en prie",
        db_status="negotiating",
        history=[{"content": "Merci pour ta confiance !", "is_from_client": False}],
        product=_product(), current_offer=19000.0, llm=rogue,
    )
    assert all(a.type.value != "end_conversation" for a in result.plan.actions)
    assert result.db_status != "ended"


async def test_pipeline_bare_ok_confirms_at_counter_not_listed_price():
    """Bug terrain n°9 : « Au lieu de 20 000 F, je te fais 19 000 F » + « ok »
    → la vente partait à 20 000 (premier montant du texte). Le prix accepté
    doit être la CONTRE-OFFRE, jamais le prix affiché."""
    result = await run_pipeline(
        client_message="ok je prends",
        db_status="negotiating", history=[
            {"content": "c'est trop cher", "is_from_client": True},
            {"content": "Au lieu de 20 000 F, je te fais 19 000 F, mon meilleur prix !",
             "is_from_client": False},
        ],
        product=_product(price=20000.0, min_price=18000.0),
        current_offer=None, llm=None,
    )
    assert result.db_status == "agreed"
    assert result.new_offer == 19000.0          # PAS 20 000


async def test_pipeline_persisted_offer_beats_text_guessing():
    """Le prix persistant (current_offer) fait autorité sur l'extraction texte."""
    result = await run_pipeline(
        client_message="ok",
        db_status="negotiating", history=[
            {"content": "Allez, un dernier geste et on conclut 🌹",  # aucun montant
             "is_from_client": False},
        ],
        product=_product(price=20000.0, min_price=18000.0),
        current_offer=18500.0, llm=None,
    )
    assert result.db_status == "agreed"
    assert result.new_offer == 18500.0


async def test_pipeline_counter_persists_standing_price():
    """Une contre-offre du bot PERSISTE son prix (plus de devinette au tour suivant)."""
    result = await run_pipeline(
        client_message="c'est trop cher",
        db_status="negotiating", history=[],
        product=_product(price=20000.0, min_price=18000.0),
        current_offer=None, llm=None,
    )
    assert result.plan.actions[-1].type.value == "counter_offer"
    assert result.new_offer == 19000.0          # milieu(20 000, 18 000), persisté


async def test_pipeline_confirm_uses_last_bot_price_from_history():
    result = await run_pipeline(
        client_message="ok",
        db_status="negotiating", history=[
            {"content": "9000 c'est trop", "is_from_client": True},
            {"content": "Je peux te faire 9 500 F !", "is_from_client": False},
        ],
        product=_product(), current_offer=None, llm=None,
    )
    assert result.db_status == "agreed"
    assert result.new_offer == 9500.0
