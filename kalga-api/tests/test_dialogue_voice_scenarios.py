"""Scénarios bout-en-bout NIVEAU VOIX : message → intentions → plan → texte final.

Le pipeline complet ①→⑤ sans réseau (FakeLLM). Vérifie que même un LLM
malveillant/dérapant ne peut plus produire les bugs terrain.
"""
from app.services.dialogue.policy import PolicyContext, decide_plan
from app.services.dialogue.sale_state import SaleState
from app.services.dialogue.speech import SpeechContext, render
from app.services.dialogue.understanding import extract_intents
from app.services.dialogue.llm_protocol import FakeLLMClient


async def speak_through_pipeline(message, state, llm, last_bot=None, **kw):
    defaults = dict(listed_price=10000.0, floor_price=8000.0, current_offer=None,
                    has_variants=True, has_photo=True, stock_out=False,
                    last_bot_price=None)
    defaults.update(kw)
    intents = extract_intents(message, last_bot_message=last_bot)
    plan = decide_plan(intents, PolicyContext(state=state, **defaults))
    sctx = SpeechContext(product_name="Chemise", listed_price=10000.0,
                         floor_price=8000.0, client_message=message)
    return plan, await render(plan, sctx, llm)


async def test_voice_bug2_banco_structurally_impossible():
    """Capture 2 complète : demande photos + LLM qui s'obstine à conclure."""
    rogue = FakeLLMClient(speak_results=[
        "Banco à 10 000 F! On fait comment pour la livraison?",
        "On s'entend pour 10 000 F! Livraison ou tu viens?",
    ])
    plan, text = await speak_through_pipeline("Je veux d'autres photos",
                                              SaleState.NEGOCIATION, rogue)
    assert "banco" not in text.lower() and "livraison" not in text.lower()
    assert plan.new_state == SaleState.NEGOCIATION


async def test_voice_bug1_photo_plus_price_noted():
    plan, text = await speak_through_pipeline(
        "Je veux ça à 9000 et envoie moi plus de photo",
        SaleState.NEGOCIATION, None)   # sans LLM : gabarits
    assert "9 000" in text             # prix noté, dit au client
    assert "modèle" in text.lower()    # variantes annoncées
    assert "livraison" not in text.lower()  # pas de clôture


async def test_voice_legit_conclusion_speaks_delivery():
    plan, text = await speak_through_pipeline(
        "ok pour 9000", SaleState.NEGOCIATION, None, last_bot_price=9000.0)
    assert "9 000" in text and "livraison" in text.lower()


async def test_voice_hold_floor_varies_with_seed():
    intents = extract_intents("5000 dernier prix")
    plan = decide_plan(intents, PolicyContext(
        state=SaleState.NEGOCIATION, listed_price=10000.0, floor_price=8000.0,
        current_offer=None, has_variants=True, has_photo=True,
        last_bot_price=8000.0))
    texts = set()
    for seed in range(3):
        sctx = SpeechContext(product_name="Chemise", listed_price=10000.0,
                             floor_price=8000.0, round_seed=seed)
        texts.add(await render(plan, sctx, None))
    assert len(texts) >= 2             # le radin n'entend pas un disque rayé
