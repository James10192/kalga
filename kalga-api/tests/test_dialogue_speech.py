"""Tests de la parole : gabarits de secours puis rendu LLM contraint."""
from app.services.dialogue.actions import Action, ActionPlan, ActionType
from app.services.dialogue.sale_state import SaleState
from app.services.dialogue.speech import SpeechContext, render_fallback


def _sctx(**kw):
    defaults = dict(product_name="Sac cuir", listed_price=10000.0,
                    floor_price=8000.0, round_seed=0)
    defaults.update(kw)
    return SpeechContext(**defaults)


def _plan(*actions, state=SaleState.RENSEIGNEMENT, offer=None):
    return ActionPlan(actions=list(actions), new_state=state, new_offer=offer)


def test_fallback_greeting_mentions_product():
    plan = _plan(Action(ActionType.SEND_TEXT, facts=("greeting",)))
    text = render_fallback(plan, _sctx())
    assert "Sac cuir" in text


def test_fallback_counter_offer_formats_price():
    plan = _plan(Action(ActionType.COUNTER_OFFER, price=9000.0, facts=("counter",)),
                 state=SaleState.NEGOCIATION)
    text = render_fallback(plan, _sctx())
    assert "9 000" in text


def test_fallback_hold_floor_varies_by_round():
    plan = _plan(Action(ActionType.COUNTER_OFFER, price=8000.0, facts=("hold_floor",)),
                 state=SaleState.NEGOCIATION)
    texts = {render_fallback(plan, _sctx(round_seed=i)) for i in range(3)}
    assert len(texts) >= 2          # anti-boucle : formulations différentes
    assert all("8 000" in t for t in texts)


def test_fallback_confirm_deal_asks_delivery_or_pickup():
    plan = _plan(Action(ActionType.CONFIRM_DEAL, price=9000.0),
                 state=SaleState.CONCLUSION)
    text = render_fallback(plan, _sctx())
    assert "9 000" in text and "livraison" in text.lower()


def test_fallback_combines_multiple_actions():
    plan = _plan(Action(ActionType.SEND_VARIANTS),
                 Action(ActionType.SEND_TEXT, facts=("price_ok_pending",), price=9000.0),
                 state=SaleState.NEGOCIATION)
    text = render_fallback(plan, _sctx())
    assert "9 000" in text          # le prix noté est dit
    assert "modèle" in text.lower() # et les variantes annoncées


def test_fallback_every_action_type_produces_text():
    from app.services.dialogue.actions import ActionType as AT
    cases = [
        Action(AT.SEND_PHOTO), Action(AT.SEND_VARIANTS), Action(AT.SEND_LOCATION),
        Action(AT.SEND_PAYMENT_INFO), Action(AT.REQUEST_ADDRESS),
        Action(AT.END_CONVERSATION), Action(AT.JOIN_WAITLIST),
        Action(AT.HANDOVER_HUMAN),
        Action(AT.SEND_TEXT, facts=("clarify",)),
        Action(AT.SEND_TEXT, facts=("clarify_deal",)),
        Action(AT.SEND_TEXT, facts=("apaisement",)),
        Action(AT.SEND_TEXT, facts=("correction",)),
        Action(AT.SEND_TEXT, facts=("info:prix",)),
        Action(AT.SEND_TEXT, facts=("delivery_info",)),
        Action(AT.SEND_TEXT, facts=("catalogue",)),
        Action(AT.SEND_TEXT, facts=("out_of_stock",)),
        Action(AT.SEND_TEXT, facts=("address_confirmed",)),
        Action(AT.SEND_TEXT, facts=("delivery_noted",)),
        Action(AT.SEND_TEXT, facts=("only_photo",)),
        Action(AT.SEND_TEXT, facts=("greeting",)),
    ]
    for action in cases:
        text = render_fallback(_plan(action), _sctx())
        assert isinstance(text, str) and len(text) >= 3, action


def test_fallback_notify_merchant_is_silent():
    # Action interne : aucun texte client
    plan = _plan(Action(ActionType.NOTIFY_MERCHANT, reason="x"))
    assert render_fallback(plan, _sctx()) == ""


# === Rendu LLM contraint ===
from app.services.dialogue.llm_protocol import FakeLLMClient
from app.services.dialogue.speech import build_brief, render


async def test_render_uses_llm_text_when_guard_passes():
    plan = _plan(Action(ActionType.COUNTER_OFFER, price=9000.0, facts=("counter",)),
                 state=SaleState.NEGOCIATION)
    fake = FakeLLMClient(speak_result="Allez, 9 000 F et c'est réglé mon ami !")
    text = await render(plan, _sctx(), fake)
    assert text == "Allez, 9 000 F et c'est réglé mon ami !"


async def test_render_blocks_banco_and_falls_back():
    """LE test capture 2 au niveau voix : le LLM tente Banco, le filet bloque."""
    plan = _plan(Action(ActionType.SEND_VARIANTS), state=SaleState.NEGOCIATION)
    fake = FakeLLMClient(speak_results=[
        "Banco à 10 000 F! On fait comment pour la livraison?",   # violation
        "Banco quand même, livraison ou tu viens ?",               # re-violation
    ])
    text = await render(plan, _sctx(), fake)
    assert "banco" not in text.lower()
    assert "livraison" not in text.lower()
    assert "modèle" in text.lower()      # gabarit SEND_VARIANTS


async def test_render_retry_once_then_accepts_corrected():
    plan = _plan(Action(ActionType.COUNTER_OFFER, price=9000.0, facts=("counter",)),
                 state=SaleState.NEGOCIATION)
    fake = FakeLLMClient(speak_results=[
        "Je peux te faire 7 000 F !",     # sous le plancher → reprise
        "Je peux te faire 9 000 F !",     # corrigé → accepté
    ])
    text = await render(plan, _sctx(), fake)
    assert text == "Je peux te faire 9 000 F !"
    assert len(fake.speak_briefs) == 2
    assert "violations" in fake.speak_briefs[1]   # la reprise reçoit le motif


async def test_render_falls_back_when_llm_none():
    plan = _plan(Action(ActionType.SEND_PHOTO))
    fake = FakeLLMClient(fail=True)
    text = await render(plan, _sctx(), fake)
    assert "photo" in text.lower()


async def test_render_without_llm_uses_fallback():
    plan = _plan(Action(ActionType.SEND_PHOTO))
    text = await render(plan, _sctx(), None)
    assert "photo" in text.lower()


async def test_brief_contains_plan_persona_and_forbidden():
    plan = _plan(Action(ActionType.COUNTER_OFFER, price=9000.0, facts=("counter",)),
                 state=SaleState.NEGOCIATION)
    brief = build_brief(plan, _sctx(persona={"bot_catchphrase": "On est ensemble !"}))
    assert brief["actions"][0]["type"] == "counter_offer"
    assert brief["persona"]["bot_catchphrase"] == "On est ensemble !"
    assert any("conclure" in f for f in brief["forbidden"])
