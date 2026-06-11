# Refonte dialogue — Phase 4 : Branchement — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Brancher le moteur v2 dans le chemin vivant derrière le drapeau `DIALOGUE_ENGINE` (`v1` par défaut) : adaptateur DeepSeek réel, orchestrateur, façade d'intégration, et le branchement minimal dans `chat_service` — testé de bout en bout via `handle_incoming_message`.

**Architecture:** Principe de sécurité absolu : **v2 est opt-in et ne peut, au pire, que retomber sur v1** (façade défensive : toute erreur ou message non-géré → `None` → chemin v1 inchangé). Le branchement remplace UNIQUEMENT l'appel cerveau+voix (section 6 de `chat_service`) ; tout l'aval existant (persistance, notifications, localisation, goodbye, relances) est réutilisé tel quel.

**Tech Stack:** Python 3.12, pydantic settings (drapeau), httpx via DeepSeekClient existant, pytest + temp_db.

**Spec :** `docs/superpowers/specs/2026-06-11-refonte-moteur-dialogue-design.md` §9, §12 (P4).

**Notes :** pytest depuis `kalga-api/`, git racine, branche `refonte/moteur-dialogue` vérifiée avant commit.

---

## Structure des fichiers

| Fichier | Action | Responsabilité |
|---|---|---|
| `kalga-api/app/core/config.py` | Modifier | + `dialogue_engine: str = "v1"` |
| `kalga-api/app/services/dialogue/deepseek_adapter.py` | Créer | LLMClient réel (classify/speak via DeepSeek) |
| `kalga-api/app/services/dialogue/orchestrator.py` | Créer | ①→⑤ : message → DialogueResult (pur, LLM injecté) |
| `kalga-api/app/services/dialogue/engine.py` | Créer | Façade d'intégration : plan → champs BotResponse (images, GPS…) |
| `kalga-api/app/services/chat_service.py` | Modifier | Branche v2 derrière le drapeau (section 6) |
| `kalga-api/tests/test_dialogue_adapter.py` | Créer | Tests adaptateur (stub, sans réseau) |
| `kalga-api/tests/test_dialogue_orchestrator.py` | Créer | Tests orchestrateur (FakeLLM) |
| `kalga-api/tests/test_dialogue_engine_v2.py` | Créer | Tests façade + bout-en-bout chat_service v2 (temp_db) |

---

## Task 1: Drapeau + adaptateur DeepSeek

- [ ] **Step 1: Drapeau** — dans `app/core/config.py`, classe `Settings`, après le bloc DeepSeek (ligne ~28) :

```python
    # === Moteur de dialogue (refonte 2026-06-11) ===
    # "v1" = ancien chemin (generate_response) ; "v2" = pipeline dialogue/ (opt-in)
    dialogue_engine: str = "v1"
```

- [ ] **Step 2: Tests adaptateur (rouge)** — `kalga-api/tests/test_dialogue_adapter.py`

```python
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
```

- [ ] **Step 3: Implémentation** — `kalga-api/app/services/dialogue/deepseek_adapter.py`

```python
"""
Adaptateur DeepSeek du contrat LLMClient (spec §9).

Deux prompts étroits :
- classify : catalogue d'intentions imposé, sortie JSON uniquement ;
- speak    : exécuter le brief (plan décidé + interdits), jamais décider.

Toute erreur (réseau, JSON, timeout) → None : le moteur continue
(règles seules / gabarits). Jamais d'exception vers l'appelant.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from .intents import IntentType

logger = logging.getLogger("kalga.dialogue.adapter")

_CLASSIFY_SYSTEM = (
    "Tu classifies le message d'un client WhatsApp d'une boutique en Côte d'Ivoire.\n"
    "Types possibles (UNIQUEMENT ceux-ci) :\n"
    + "\n".join(f"- {t.value}" for t in IntentType)
    + "\nRéponds UNIQUEMENT un tableau JSON : "
      '[{"type": "...", "amount": nombre éventuel, "text": "détail éventuel"}]. '
      "Plusieurs intentions possibles. Aucun autre texte."
)

_SPEAK_SYSTEM = (
    "Tu es le vendeur d'une boutique WhatsApp en Côte d'Ivoire. "
    "Le système a DÉJÀ décidé quoi faire — tu ne décides RIEN, tu rédiges. "
    "Écris UN court message WhatsApp naturel et chaleureux (tutoiement, "
    "1-3 phrases, émojis sobres) qui exprime exactement les actions du plan. "
    "Respecte ABSOLUMENT les interdits fournis. Réponds uniquement le message."
)


class DeepSeekAdapter:
    """Implémente LLMClient au-dessus du DeepSeekClient existant."""

    def __init__(self, ds_client):
        self._ds = ds_client

    async def classify(self, message: str, context: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        try:
            last_bot = context.get("last_bot_message") or "(aucun)"
            user = (f"Dernier message du bot : {last_bot}\n"
                    f"Message du client : {message}")
            raw = await self._ds.chat_completion(
                messages=[{"role": "user", "content": user}],
                temperature=0.1, max_tokens=200, system_prompt=_CLASSIFY_SYSTEM,
            )
            if not raw:
                return None
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(l for l in cleaned.splitlines()
                                    if not l.startswith("```")).strip()
            data = json.loads(cleaned)
            return data if isinstance(data, list) else None
        except Exception as e:
            logger.warning(f"classify indisponible: {e}")
            return None

    async def speak(self, brief: Dict[str, Any]) -> Optional[str]:
        try:
            persona = brief.get("persona") or {}
            persona_line = ""
            if persona.get("bot_catchphrase"):
                persona_line = f"Phrase signature à placer si naturel : {persona['bot_catchphrase']}\n"
            memory_line = f"Contexte client : {brief['memory']}\n" if brief.get("memory") else ""
            user = (
                f"Produit : {brief.get('product_name')} à {brief.get('listed_price')} F\n"
                f"Le client vient de dire : {brief.get('client_message')}\n"
                f"{memory_line}{persona_line}"
                f"PLAN À EXPRIMER (dans cet ordre) : {json.dumps(brief.get('actions', []), ensure_ascii=False)}\n"
                f"INTERDITS : {' ; '.join(brief.get('forbidden', []))}\n"
                f"Rédige le message."
            )
            raw = await self._ds.chat_completion(
                messages=[{"role": "user", "content": user}],
                temperature=0.7, max_tokens=300, system_prompt=_SPEAK_SYSTEM,
            )
            return raw.strip() if raw else None
        except Exception as e:
            logger.warning(f"speak indisponible: {e}")
            return None
```

- [ ] **Step 4:** Run `python -m pytest tests/test_dialogue_adapter.py -q` → PASS (6)
- [ ] **Step 5:** Commit `feat(dialogue): drapeau DIALOGUE_ENGINE + adaptateur DeepSeek (classify/speak)`

---

## Task 2: Orchestrateur ①→⑤

- [ ] **Step 1: Tests (rouge)** — `kalga-api/tests/test_dialogue_orchestrator.py`

```python
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
```

- [ ] **Step 2: Implémentation** — `kalga-api/app/services/dialogue/orchestrator.py`

```python
"""
Chef d'orchestre du pipeline (spec §4) — mince, zéro logique métier :
① assainir (dans extract_intents) → ② comprendre (+ classifieur LLM si UNCLEAR)
→ ③ décider → ④ parler → ⑤ filtrer (dans render).

Retourne None quand le message ne porte aucune intention client (messages
système purs) : l'appelant garde alors son chemin historique.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

from .actions import ActionPlan
from .intents import Intent, IntentType
from .llm_classifier import classify_with_llm
from .llm_protocol import LLMClient
from .policy import PolicyContext, decide_plan
from .sale_state import DB_STATUS, from_db_status
from .speech import SpeechContext, render
from .understanding import extract_intents, extract_price_amount


@dataclass
class DialogueResult:
    text: str
    plan: ActionPlan
    db_status: str
    new_offer: Optional[float]


def _last_bot_message(history: List[Dict]) -> Optional[str]:
    for msg in reversed(history or []):
        if not msg.get("is_from_client"):
            return msg.get("content")
    return None


async def run_pipeline(
    client_message: str,
    db_status: str,
    history: List[Dict],
    product: Dict,
    current_offer: Optional[float],
    llm: Optional[LLMClient],
    persona: Optional[dict] = None,
    memory_block: Optional[str] = None,
) -> Optional[DialogueResult]:
    last_bot = _last_bot_message(history)

    # ①② Comprendre (multi-intentions, métadonnées assainies)
    intents = extract_intents(client_message, last_bot_message=last_bot)
    if not intents:
        return None  # message 100 % système → chemin v1

    # ②bis Classifieur LLM pour l'ambigu
    if intents == [Intent(IntentType.UNCLEAR)]:
        intents = await classify_with_llm(client_message, llm,
                                          {"last_bot_message": last_bot})

    # ③ Décider
    ctx = PolicyContext(
        state=from_db_status(db_status, message_count=len(history)),
        listed_price=float(product["price"]),
        floor_price=float(product.get("effective_min_price") or product["min_price"]),
        current_offer=current_offer,
        has_variants=bool(product.get("group_id")),
        has_photo=bool(product.get("image_path")),
        last_bot_price=extract_price_amount(last_bot) if last_bot else None,
    )
    plan = decide_plan(intents, ctx)

    # ④⑤ Parler (filtré)
    sctx = SpeechContext(
        product_name=product["name"],
        listed_price=float(product["price"]),
        floor_price=ctx.floor_price,
        round_seed=len(history),
        persona=persona,
        memory_block=memory_block,
        client_message=client_message,
    )
    text = await render(plan, sctx, llm)

    return DialogueResult(
        text=text,
        plan=plan,
        db_status=DB_STATUS[plan.new_state],
        new_offer=plan.new_offer,
    )
```

- [ ] **Step 3:** Run → PASS (4) · **Step 4:** Commit `feat(dialogue): orchestrateur ①→⑤ (DialogueResult)`

---

## Task 3: Façade d'intégration engine.py

- [ ] **Step 1: Tests (rouge)** — `kalga-api/tests/test_dialogue_engine_v2.py` (première partie)

```python
"""Tests de la façade v2 puis du branchement chat_service bout-en-bout."""
from app.database.connection import get_connection
from app.database.repositories.product_repo import ProductRepository
from app.services.dialogue.engine import respond


async def _seed(group=False):
    repo = ProductRepository()
    async with get_connection() as db:
        cur = await db.execute(
            "INSERT INTO merchants (name, phone, address, latitude, longitude) "
            "VALUES (?, ?, ?, ?, ?)",
            ("Jolie Bien", "2250100000001", "Bassam", 5.2, -3.7),
        )
        await db.commit()
        merchant_id = cur.lastrowid
    base = await repo.create(merchant_id=merchant_id, name="Chemise", price=10000,
                             min_price=8000, image_path="chemise.jpg",
                             group_id="GRP-V2" if group else None)
    variant = None
    if group:
        variant = await repo.create(merchant_id=merchant_id, name="Chemise - Bleu",
                                    price=10000, min_price=8000, image_path="bleu.jpg",
                                    group_id="GRP-V2", variant_name="Bleu")
    merchant = {"id": merchant_id, "phone": "2250100000001", "name": "Jolie Bien",
                "business_name": "Jolie Bien"}
    return merchant, base, variant


async def test_engine_photo_request_returns_image(temp_db):
    merchant, product, _ = await _seed()
    conv = {"id": 1, "status": "negotiating", "current_offer": None,
            "selected_variant_id": None}
    out = await respond("envoie la photo", conv, product, merchant,
                        history=[{"content": "hello", "is_from_client": True},
                                 {"content": "Salut !", "is_from_client": False}],
                        llm=None)
    assert out is not None
    assert out.images_to_send and out.images_to_send[0]["image_path"] == "chemise.jpg"
    assert out.new_status == "negotiating"


async def test_engine_variants_request_returns_variant_images(temp_db):
    merchant, product, variant = await _seed(group=True)
    conv = {"id": 1, "status": "negotiating", "current_offer": None,
            "selected_variant_id": None}
    out = await respond("je veux d'autres photos", conv, product, merchant,
                        history=[], llm=None)
    assert out.images_to_send and out.images_to_send[0]["image_path"] == "bleu.jpg"
    assert "banco" not in out.message.lower()


async def test_engine_location_request_sets_flag(temp_db):
    merchant, product, _ = await _seed()
    conv = {"id": 1, "status": "agreed", "current_offer": 9000.0,
            "selected_variant_id": None}
    out = await respond("c'est où le magasin ?", conv, product, merchant,
                        history=[], llm=None)
    assert out.send_location is True
    assert out.new_status == "agreed"      # la localisation ne conclut rien


async def test_engine_system_message_returns_none(temp_db):
    merchant, product, _ = await _seed()
    conv = {"id": 1, "status": "active", "current_offer": None,
            "selected_variant_id": None}
    out = await respond("[📸 Le client a envoyé une photo.]", conv, product,
                        merchant, history=[], llm=None)
    assert out is None


async def test_engine_is_defensive_on_bad_input(temp_db):
    merchant, product, _ = await _seed()
    out = await respond("photo svp", {"status": "???"}, {"name": "X"},  # produit invalide
                        merchant, history=[], llm=None)
    assert out is None                      # jamais d'exception → v1 garde la main
```

- [ ] **Step 2: Implémentation** — `kalga-api/app/services/dialogue/engine.py`

```python
"""
Façade d'intégration du moteur v2 (spec §12, P4).

Traduit le DialogueResult (plan d'actions) vers les champs que le chemin
chat_service sait déjà exécuter (images_to_send, send_location, statut DB…).
DÉFENSIVE PAR CONTRAT : toute erreur ou message non-géré → None, et le
chemin v1 reprend la main. Activer v2 ne peut donc rien casser.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ...database.repositories.product_repo import ProductRepository
from .actions import ActionType
from .deepseek_adapter import DeepSeekAdapter
from .llm_protocol import LLMClient
from .orchestrator import run_pipeline

logger = logging.getLogger("kalga.dialogue.engine")

_UNSET = object()


@dataclass
class EngineResponse:
    message: str
    new_status: str
    new_offer: Optional[float]
    send_location: bool = False
    images_to_send: Optional[List[dict]] = None
    human_takeover: bool = False
    notify_reason: Optional[str] = None
    facts: List[str] = field(default_factory=list)


def _default_llm() -> Optional[LLMClient]:
    # Imports paresseux : éviter de charger le paquet ai/ au chargement du module
    from ...core.config import settings
    if not settings.deepseek_api_key:
        return None
    from ..ai.deepseek_client import get_deepseek_client
    return DeepSeekAdapter(get_deepseek_client())


def _format_history_block(history: List[Dict], window: int = 8) -> Optional[str]:
    recent = (history or [])[-window:]
    if not recent:
        return None
    lines = []
    for m in recent:
        who = "Client" if m.get("is_from_client") else "Vendeur"
        lines.append(f"{who}: {m.get('content', '')[:120]}")
    return "\n".join(lines)


async def _resolve_images(plan, conversation, product) -> Optional[List[dict]]:
    repo = ProductRepository()
    images: List[dict] = []
    for action in plan.actions:
        if action.type == ActionType.SEND_PHOTO:
            target = None
            if conversation.get("selected_variant_id"):
                target = await repo.get_by_id(conversation["selected_variant_id"])
            if target and target.get("image_path"):
                images.append({"image_path": target["image_path"],
                               "caption": f"Modèle {target.get('variant_name') or target['name']}"})
            elif product.get("image_path"):
                images.append({"image_path": product["image_path"],
                               "caption": product["name"]})
        elif action.type == ActionType.SEND_VARIANTS and product.get("group_id"):
            variants = await repo.get_other_variants(product["id"], product["group_id"])
            for v in variants:
                if v.get("image_path"):
                    images.append({"image_path": v["image_path"],
                                   "caption": f"Modèle {v.get('variant_name') or v['name']}"})
    return images or None


async def respond(
    client_message: str,
    conversation: Dict,
    product: Dict,
    merchant: Dict,
    history: List[Dict],
    llm=_UNSET,
) -> Optional[EngineResponse]:
    try:
        llm_client = _default_llm() if llm is _UNSET else llm

        persona = None
        if any(merchant.get(k) for k in ("bot_tone", "bot_style", "bot_catchphrase")):
            persona = {k: merchant.get(k) for k in ("bot_tone", "bot_style", "bot_catchphrase")}

        result = await run_pipeline(
            client_message=client_message,
            db_status=conversation.get("status", "active"),
            history=history or [],
            product=product,
            current_offer=conversation.get("current_offer"),
            llm=llm_client,
            persona=persona,
            memory_block=_format_history_block(history),
        )
        if result is None:
            return None

        plan = result.plan
        types = {a.type for a in plan.actions}
        message = result.text

        # Infos de paiement : ajoutées au texte (donnée marchand, pas LLM)
        if ActionType.SEND_PAYMENT_INFO in types:
            payment = merchant.get("payment_info") or merchant.get("payment_methods")
            if payment:
                message = f"{message}\n{payment}"

        notify = next((a.reason for a in plan.actions
                       if a.type == ActionType.NOTIFY_MERCHANT), None)

        return EngineResponse(
            message=message,
            new_status=result.db_status,
            new_offer=result.new_offer,
            send_location=ActionType.SEND_LOCATION in types,
            images_to_send=await _resolve_images(plan, conversation, product),
            human_takeover=ActionType.HANDOVER_HUMAN in types,
            notify_reason=notify,
            facts=[f for a in plan.actions for f in a.facts],
        )
    except Exception as e:
        logger.error(f"Moteur v2 indisponible — repli v1: {e}")
        return None
```

- [ ] **Step 3:** Run → PASS (5) · **Step 4:** Commit `feat(dialogue): façade engine v2 (plan → champs BotResponse, défensive)`

---

## Task 4: Branchement chat_service + bout-en-bout

- [ ] **Step 1: Tests bout-en-bout (rouge)** — ajout à `test_dialogue_engine_v2.py`

```python
# === Bout-en-bout : handle_incoming_message avec DIALOGUE_ENGINE=v2 ===
# ⚠️ deepseek_api_key est neutralisée (None) dans CHAQUE test e2e : la vraie clé
# est dans .env et _default_llm() construirait sinon un adaptateur RÉSEAU.
# Sans clé → gabarits déterministes, zéro réseau, tests stables.
from app.core.config import settings as app_settings
from app.models.schemas import IncomingMessage
from app.services.chat_service import ChatService


async def _conversation_for(merchant, product, status, history_msgs):
    async with get_connection() as db:
        cur = await db.execute(
            "INSERT INTO conversations (merchant_id, product_id, client_phone, status) "
            "VALUES (?, ?, ?, ?)",
            (merchant["id"], product["id"], "2250700000077", status),
        )
        conv_id = cur.lastrowid
        for content, from_client in history_msgs:
            await db.execute(
                "INSERT INTO messages (conversation_id, content, is_from_client) "
                "VALUES (?, ?, ?)", (conv_id, content, int(from_client)),
            )
        await db.commit()
    return conv_id


async def test_e2e_v2_photo_request_sends_photo_no_goodbye(temp_db, monkeypatch):
    """LE bug des captures, rejoué à travers TOUT le service en v2."""
    monkeypatch.setattr(app_settings, "dialogue_engine", "v2")
    monkeypatch.setattr(app_settings, "deepseek_api_key", None)
    merchant, product, _ = await _seed()
    await _conversation_for(merchant, product, "negotiating",
                            [("je veux ça à 9000", True),
                             ("Je peux te faire 9 500 F !", False)])
    svc = ChatService()
    resp = await svc.handle_incoming_message(IncomingMessage(
        merchant_phone=merchant["phone"], client_phone="2250700000077",
        message="je veux des photos"))
    assert resp.images_to_send, "la photo doit partir"
    assert resp.goodbye_message is None
    assert "banco" not in (resp.message or "").lower()


async def test_e2e_v2_bare_ok_after_priced_bot_concludes(temp_db, monkeypatch):
    monkeypatch.setattr(app_settings, "dialogue_engine", "v2")
    monkeypatch.setattr(app_settings, "deepseek_api_key", None)
    merchant, product, _ = await _seed()
    await _conversation_for(merchant, product, "negotiating",
                            [("9000 ?", True),
                             ("Je peux te faire 9 500 F !", False)])
    svc = ChatService()
    resp = await svc.handle_incoming_message(IncomingMessage(
        merchant_phone=merchant["phone"], client_phone="2250700000077",
        message="ok je prends"))
    assert "9 500" in resp.message
    assert "livraison" in resp.message.lower()


async def test_e2e_v1_path_untouched_when_flag_off(temp_db, monkeypatch):
    monkeypatch.setattr(app_settings, "dialogue_engine", "v1")
    monkeypatch.setattr(app_settings, "deepseek_api_key", None)
    merchant, product, _ = await _seed()
    await _conversation_for(merchant, product, "negotiating",
                            [("hello", True), ("Salut !", False)])
    svc = ChatService()
    resp = await svc.handle_incoming_message(IncomingMessage(
        merchant_phone=merchant["phone"], client_phone="2250700000077",
        message="envoie la photo"))
    # v1 : l'interception déterministe existante sert déjà la photo
    assert resp.images_to_send
```

- [ ] **Step 2: Branchement** — dans `chat_service.py`, juste APRÈS le bloc `negotiation_context` (section « 6. Générer la réponse IA ») et AVANT l'appel `generate_response`, insérer :

```python
        # === MOTEUR V2 (drapeau DIALOGUE_ENGINE) — spec refonte 2026-06-11 ===
        # v2 remplace UNIQUEMENT le cerveau+voix ; tout l'aval (persistance,
        # notifications, localisation, goodbye, relances) reste le chemin commun.
        # Défensif : v2 → None ⇒ v1 reprend la main, rien ne casse.
        engine_v2 = None
        from ..core.config import settings as _settings
        if _settings.dialogue_engine == "v2":
            from .dialogue.engine import respond as dialogue_respond
            engine_v2 = await dialogue_respond(
                client_message=message.message,
                conversation=conversation,
                product=product,
                merchant=merchant,
                history=history,
            )
            if tracer:
                tracer.event("CHAT", "dialogue_v2",
                             used=engine_v2 is not None,
                             facts=engine_v2.facts if engine_v2 else None)

        images_v2 = None
        human_takeover_v2 = False
        if engine_v2 is not None:
            bot_response = engine_v2.message
            price_offer = engine_v2.new_offer
            new_status = engine_v2.new_status
            send_location = engine_v2.send_location
            use_voice = False
            deal_accepted = new_status in ("agreed", "pending_delivery", "pending_pickup")
            images_v2 = engine_v2.images_to_send
            human_takeover_v2 = engine_v2.human_takeover
        else:
            bot_response, price_offer, deal_accepted, new_status, send_location, use_voice = await generate_response(
```

  puis fermer le `else:` en indentant l'appel `generate_response(...)` existant dedans, et :
  - dans la section « 6.1 Dispatcher le tool_call », garder le bloc sous `if engine_v2 is None and bot_response and is_tool_call(bot_response):` (v2 ne produit jamais de tool encodé) ;
  - à l'initialisation `images_to_send = None` (section 6.1), remplacer par `images_to_send = images_v2` ;
  - à la section 7.5, après `human_takeover = False`, ajouter `human_takeover = human_takeover or human_takeover_v2`.

- [ ] **Step 3:** Run `python -m pytest tests/test_dialogue_engine_v2.py -q` → PASS (8)
- [ ] **Step 4:** Suite complète + import app → ≈ 245 verts, OK
- [ ] **Step 5:** Spec §12 : P4 → « — ✅ fait » · Commit + push

```bash
git add kalga-api/app/core/config.py kalga-api/app/services/dialogue/ kalga-api/app/services/chat_service.py kalga-api/tests/
git add -f docs/superpowers/specs/2026-06-11-refonte-moteur-dialogue-design.md
git commit -m "feat(dialogue): branchement v2 derrière DIALOGUE_ENGINE (v1 défaut, repli sûr)"
git push
```

---

## Test réel WhatsApp (après exécution — manuel, par le marchand)

1. Dans `kalga-api/.env` ajouter : `DIALOGUE_ENGINE=v2`
2. Redémarrer l'API (`Ctrl+C` puis `uvicorn app.main:app --port 8001 --reload`)
3. Rejouer les scénarios des captures : « hello » sur Statut · « je veux ça à 9000 et envoie moi plus de photo » · « je veux d'autres photos » · « ok » · « je veux me faire livrer »
4. Pour revenir à l'ancien moteur : retirer la ligne ou `DIALOGUE_ENGINE=v1` + redémarrage.

## Dette tracée / notes pour P5

- Geste fidélité (plancher ajusté client connu) : pas encore branché en v2 — v1 le garde ; à porter en P5 via `negotiation_context` → `floor_price`.
- Mémoire long-terme (LTM/épisodique) : v2 utilise la fenêtre d'historique récente ; l'injection LTM complète + extraction fin de conversation à porter en P5.
- `JOIN_WAITLIST`/rupture : court-circuit existant en amont (section 4 chat_service) conservé — la branche policy stock_out reste dormante en P4.
- TTS (`use_voice`) : désactivé en v2 pour P4 ; à porter en P5 si souhaité.
