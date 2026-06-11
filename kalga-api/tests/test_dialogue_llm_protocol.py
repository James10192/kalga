"""Tests du contrat LLM et du faux client."""
from app.services.dialogue.llm_protocol import FakeLLMClient


async def test_fake_speak_returns_configured_text_and_records_brief():
    fake = FakeLLMClient(speak_result="Salut !")
    out = await fake.speak({"actions": ["send_photo"]})
    assert out == "Salut !"
    assert fake.speak_briefs[0]["actions"] == ["send_photo"]


async def test_fake_speak_sequence_then_none():
    fake = FakeLLMClient(speak_results=["a", None])
    assert await fake.speak({}) == "a"
    assert await fake.speak({}) is None


async def test_fake_classify_returns_configured():
    fake = FakeLLMClient(classify_result=[{"type": "ask_photo"}])
    assert await fake.classify("msg", {}) == [{"type": "ask_photo"}]


async def test_fake_failure_mode_returns_none():
    fake = FakeLLMClient(fail=True)
    assert await fake.speak({}) is None
    assert await fake.classify("x", {}) is None
