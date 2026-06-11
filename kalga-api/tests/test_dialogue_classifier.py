"""Tests du classifieur LLM de secours — catalogue imposé, jamais d'action."""
from app.services.dialogue.intents import Intent, IntentType
from app.services.dialogue.llm_classifier import classify_with_llm
from app.services.dialogue.llm_protocol import FakeLLMClient


async def test_valid_intents_are_built():
    fake = FakeLLMClient(classify_result=[
        {"type": "ask_photo"},
        {"type": "price_offer", "amount": 9000},
    ])
    intents = await classify_with_llm("le truc là, fais voir et 9000", fake, {})
    assert Intent(IntentType.ASK_PHOTO) in intents
    assert Intent(IntentType.PRICE_OFFER, amount=9000.0) in intents


async def test_unknown_types_are_dropped():
    fake = FakeLLMClient(classify_result=[
        {"type": "buy_now_with_credit_card"},   # n'existe pas au catalogue
        {"type": "ask_location"},
    ])
    intents = await classify_with_llm("msg", fake, {})
    assert intents == [Intent(IntentType.ASK_LOCATION)]


async def test_llm_failure_returns_unclear():
    fake = FakeLLMClient(fail=True)
    intents = await classify_with_llm("msg", fake, {})
    assert intents == [Intent(IntentType.UNCLEAR)]


async def test_empty_or_garbage_returns_unclear():
    fake = FakeLLMClient(classify_result=[{"no_type": True}, "garbage"])
    intents = await classify_with_llm("msg", fake, {})
    assert intents == [Intent(IntentType.UNCLEAR)]


async def test_no_llm_returns_unclear():
    intents = await classify_with_llm("msg", None, {})
    assert intents == [Intent(IntentType.UNCLEAR)]
