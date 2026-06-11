"""Tests de l'adaptateur DeepSeek (stub du client HTTP — zéro réseau)."""
from app.services.dialogue.deepseek_adapter import DeepSeekAdapter


class StubDS:
    """Imite DeepSeekClient.chat_completion ; enregistre les prompts."""
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    async def chat_completion(self, messages, temperature=0.7, max_tokens=400,
                              system_prompt=None):
        self.calls.append({"messages": messages, "system": system_prompt,
                           "temperature": temperature})
        return self.replies.pop(0) if self.replies else None


async def test_classify_parses_json_array():
    ds = StubDS(['[{"type": "ask_photo"}, {"type": "price_offer", "amount": 9000}]'])
    out = await DeepSeekAdapter(ds).classify("fais voir et 9000", {})
    assert out == [{"type": "ask_photo"}, {"type": "price_offer", "amount": 9000}]


async def test_classify_strips_code_fences():
    ds = StubDS(['```json\n[{"type": "ask_location"}]\n```'])
    out = await DeepSeekAdapter(ds).classify("c'est où", {})
    assert out == [{"type": "ask_location"}]


async def test_classify_bad_json_returns_none():
    ds = StubDS(["je ne sais pas trop"])
    assert await DeepSeekAdapter(ds).classify("msg", {}) is None


async def test_classify_prompt_contains_catalog():
    ds = StubDS(['[]'])
    await DeepSeekAdapter(ds).classify("msg", {"last_bot_message": "Le sac est à 10 000 F"})
    system = ds.calls[0]["system"]
    assert "ask_photo" in system and "price_offer" in system and "unclear" in system
    assert "Le sac est à 10 000 F" in ds.calls[0]["messages"][0]["content"]


async def test_speak_returns_text_and_prompt_carries_brief():
    ds = StubDS(["Voilà la photo mon ami ! 😊"])
    brief = {"actions": [{"type": "send_photo", "price": None, "facts": []}],
             "state": "renseignement", "product_name": "Sac", "listed_price": 10000.0,
             "client_message": "fais voir", "persona": {"bot_catchphrase": "On est ensemble !"},
             "memory": None, "forbidden": ["conclure la vente"]}
    out = await DeepSeekAdapter(ds).speak(brief)
    assert out == "Voilà la photo mon ami ! 😊"
    user = ds.calls[0]["messages"][0]["content"]
    assert "send_photo" in user and "conclure la vente" in user
    assert "On est ensemble !" in user


async def test_adapter_never_raises():
    class Boom:
        async def chat_completion(self, *a, **k):
            raise RuntimeError("réseau mort")
    a = DeepSeekAdapter(Boom())
    assert await a.classify("x", {}) is None
    assert await a.speak({"actions": [], "forbidden": []}) is None
