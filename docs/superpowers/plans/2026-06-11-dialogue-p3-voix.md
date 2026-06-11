# Refonte dialogue — Phase 3 : La voix — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire les étages ④ (parole) et ⑤ (filet de sortie) + le classifieur LLM de secours : le LLM habille le plan décidé, ne peut pas le contourner, et des gabarits garantissent une réponse correcte même sans LLM.

**Architecture:** `llm_protocol` (interface + faux client de test), `output_guard` (filet : langage de clôture/prix interdits), `speech` (brief verrouillé → LLM, gabarits de secours, variété anti-boucle déterministe), `llm_classifier` (intentions JSON validées contre le catalogue). Tout testable sans réseau via `FakeLLMClient`.

**Tech Stack:** Python 3.12, Protocol (typing), pytest + pytest-asyncio (asyncio_mode=auto).

**Spec :** `docs/superpowers/specs/2026-06-11-refonte-moteur-dialogue-design.md` §9.

**Notes :** pytest depuis `kalga-api/`, git racine, branche `refonte/moteur-dialogue` vérifiée avant commit. L'adaptateur DeepSeek réel arrive en P4 (branchement) — P3 définit le contrat et tout le comportement, prouvé au faux client.

---

## Structure des fichiers

| Fichier | Action | Responsabilité |
|---|---|---|
| `kalga-api/app/services/dialogue/llm_protocol.py` | Créer | Protocol `LLMClient` + `FakeLLMClient` (tests) |
| `kalga-api/app/services/dialogue/output_guard.py` | Créer | ⑤ Filet de sortie |
| `kalga-api/app/services/dialogue/speech.py` | Créer | ④ Brief verrouillé → LLM ; gabarits de secours |
| `kalga-api/app/services/dialogue/llm_classifier.py` | Créer | ② (secours) intentions LLM validées |
| `kalga-api/tests/test_dialogue_llm_protocol.py` | Créer | Tests protocole/faux client |
| `kalga-api/tests/test_dialogue_output_guard.py` | Créer | Tests filet |
| `kalga-api/tests/test_dialogue_speech.py` | Créer | Tests gabarits + rendu LLM |
| `kalga-api/tests/test_dialogue_classifier.py` | Créer | Tests classifieur |
| `kalga-api/tests/test_dialogue_voice_scenarios.py` | Créer | Scénarios niveau voix (Banco bloqué…) |

---

## Task 1: llm_protocol.py

- [ ] **Tests (rouge)** — `kalga-api/tests/test_dialogue_llm_protocol.py`

```python
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
```

- [ ] **Implémentation** — `kalga-api/app/services/dialogue/llm_protocol.py`

```python
"""
Contrat LLM du moteur de dialogue (spec §9).

Le LLM n'a que DEUX rôles, derrière cette interface :
- classify : message ambigu → intentions du CATALOGUE (JSON, jamais d'action) ;
- speak    : brief verrouillé → texte naturel (jamais de décision).

Toute implémentation peut échouer → retourne None, jamais d'exception :
le moteur continue (règles seules / gabarits). L'adaptateur DeepSeek réel
arrive au branchement (P4) ; FakeLLMClient sert tous les tests.
"""
from typing import Any, Dict, List, Optional, Protocol


class LLMClient(Protocol):
    async def classify(self, message: str, context: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Intentions candidates [{type, amount?, text?}] ou None si indisponible."""
        ...

    async def speak(self, brief: Dict[str, Any]) -> Optional[str]:
        """Texte de réponse à partir du brief, ou None si indisponible."""
        ...


class FakeLLMClient:
    """Faux client déterministe pour les tests (enregistre les appels)."""

    def __init__(self, speak_result: Optional[str] = None,
                 speak_results: Optional[List[Optional[str]]] = None,
                 classify_result: Optional[List[Dict[str, Any]]] = None,
                 fail: bool = False):
        self._speak_results = list(speak_results) if speak_results is not None \
            else ([speak_result] if speak_result is not None else [])
        self._classify_result = classify_result
        self._fail = fail
        self.speak_briefs: List[Dict[str, Any]] = []
        self.classify_calls: List[str] = []

    async def speak(self, brief: Dict[str, Any]) -> Optional[str]:
        self.speak_briefs.append(brief)
        if self._fail:
            return None
        if self._speak_results:
            return self._speak_results.pop(0)
        return None

    async def classify(self, message: str, context: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        self.classify_calls.append(message)
        return None if self._fail else self._classify_result
```

- [ ] Run → PASS (4) · Commit `feat(dialogue): contrat LLMClient + FakeLLMClient`

---

## Task 2: output_guard.py

- [ ] **Tests (rouge)** — `kalga-api/tests/test_dialogue_output_guard.py`

```python
"""Tests du filet de sortie — aucun langage interdit ne sort."""
from app.services.dialogue.actions import Action, ActionPlan, ActionType
from app.services.dialogue.output_guard import guard_output
from app.services.dialogue.sale_state import SaleState


def _plan(*types, state=SaleState.NEGOCIATION):
    return ActionPlan(actions=[Action(t) for t in types], new_state=state)


def test_closing_language_blocked_outside_conclusion():
    v = guard_output("Banco à 10 000 F! On fait comment pour la livraison?",
                     _plan(ActionType.SEND_VARIANTS), floor_price=8000)
    assert not v.ok and any("cloture" in x for x in v.violations)


def test_closing_language_allowed_with_confirm_deal():
    plan = ActionPlan(actions=[Action(ActionType.CONFIRM_DEAL, price=9000.0)],
                      new_state=SaleState.CONCLUSION)
    v = guard_output("Banco à 9 000 F ! Livraison ou tu passes chercher ?",
                     plan, floor_price=8000)
    assert v.ok


def test_closing_language_allowed_in_logistics_state():
    plan = _plan(ActionType.SEND_LOCATION, state=SaleState.LOGISTIQUE_RETRAIT)
    v = guard_output("On t'attend ! Tu passes chercher quand tu veux.", plan, floor_price=8000)
    assert v.ok


def test_proposing_price_below_floor_blocked():
    v = guard_output("Allez, je peux te faire 7 000 F !",
                     _plan(ActionType.COUNTER_OFFER), floor_price=8000)
    assert not v.ok and any("prix" in x for x in v.violations)


def test_quoting_client_low_price_is_allowed():
    # Citer l'offre basse du client n'est pas la proposer
    v = guard_output("5 000 F c'est un peu bas ! Je peux faire 9 000 F.",
                     _plan(ActionType.COUNTER_OFFER), floor_price=8000)
    assert v.ok


def test_revealing_min_price_concept_blocked():
    v = guard_output("Mon prix minimum c'est 8 000 F, je ne peux pas moins.",
                     _plan(ActionType.COUNTER_OFFER), floor_price=8000)
    assert not v.ok and any("secret" in x for x in v.violations)


def test_clean_text_passes():
    v = guard_output("Je peux te faire 9 000 F, c'est un bon prix !",
                     _plan(ActionType.COUNTER_OFFER), floor_price=8000)
    assert v.ok
```

- [ ] **Implémentation** — `kalga-api/app/services/dialogue/output_guard.py`

```python
"""
Étage ⑤ — Filet de sortie (spec §9).

Scanne le texte AVANT envoi. Trois familles d'interdits :
1. Langage de clôture hors CONCLUSION/LOGISTIQUE (le « Banco ! » en texte libre
   de la capture 2 — désormais structurellement bloqué) ;
2. PROPOSITION d'un prix sous le plancher (citer l'offre basse du client reste
   permis : seul « je peux faire X » avec X < plancher est une violation) ;
3. Révélation du concept de prix minimum (le plancher reste secret).
"""
import re
from dataclasses import dataclass
from typing import List

from .actions import ActionPlan, ActionType
from .sale_state import SaleState

_DEAL_STATES = {SaleState.CONCLUSION, SaleState.LOGISTIQUE_LIVRAISON,
                SaleState.LOGISTIQUE_RETRAIT, SaleState.APRES_VENTE}

_CLOSING_PATTERNS = (
    "banco", "marché conclu", "marche conclu", "affaire conclue", "c'est vendu",
    "on s'entend pour", "on s'est entendu", "livraison ou", "tu passes chercher",
    "tu viens chercher ou", "on fait comment pour la livraison",
    "tu préfères la livraison", "tu preferes la livraison",
)
_SECRET_PATTERNS = ("prix minimum", "prix plancher", "mon minimum", "en dessous de mon prix")

# « je peux (te) faire 7 000 », « je descends à 7000 », « d'accord pour 7 000 »…
_PROPOSAL_RE = re.compile(
    r"(?:je peux (?:te |vous )?faire|je te fais|je descends? à|je te laisse à"
    r"|d'accord pour|ok pour|je propose)\s*([\d][\d\s.]{2,9})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GuardVerdict:
    ok: bool
    violations: List[str]


def guard_output(text: str, plan: ActionPlan, floor_price: float) -> GuardVerdict:
    low = (text or "").lower()
    violations: List[str] = []

    allows_close = (plan.new_state in _DEAL_STATES
                    or any(a.type == ActionType.CONFIRM_DEAL for a in plan.actions))
    if not allows_close and any(p in low for p in _CLOSING_PATTERNS):
        violations.append("cloture interdite hors conclusion")

    if any(p in low for p in _SECRET_PATTERNS):
        violations.append("secret du prix plancher révélé")

    for m in _PROPOSAL_RE.finditer(low):
        digits = re.sub(r"[\s.]", "", m.group(1))
        if digits.isdigit() and float(digits) < floor_price:
            violations.append(f"prix proposé {digits} sous le plancher")

    return GuardVerdict(ok=not violations, violations=violations)
```

- [ ] Run → PASS (7) · Commit `feat(dialogue): filet de sortie (clôture/prix/secret)`

---

## Task 3: speech.py — gabarits de secours

- [ ] **Tests (rouge)** — `kalga-api/tests/test_dialogue_speech.py`

```python
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
```

- [ ] **Implémentation** — `kalga-api/app/services/dialogue/speech.py` (première moitié)

```python
"""
Étage ④ — La parole (spec §9).

Le plan est DÉJÀ décidé. Ici on le met en mots :
- gabarits déterministes (render_fallback) — corrects, toujours disponibles ;
- LLM en habilleur (render, Task 4) — plus naturel, vérifié par le filet,
  retombe sur les gabarits à la moindre violation ou indisponibilité.

La variété anti-boucle (hold_floor) est déterministe : round_seed (= nombre de
messages de la conversation) choisit la formulation — testable, sans hasard.
"""
from dataclasses import dataclass
from typing import Optional

from .actions import Action, ActionPlan, ActionType
from .output_guard import guard_output
from .llm_protocol import LLMClient


@dataclass
class SpeechContext:
    product_name: str
    listed_price: float
    floor_price: float
    round_seed: int = 0                 # varie les formulations (anti-boucle)
    persona: Optional[dict] = None      # bot_tone / bot_style / bot_catchphrase
    memory_block: Optional[str] = None  # contexte épisodique/LTM déjà formaté
    client_message: str = ""


def _fmt(price: Optional[float]) -> str:
    return f"{int(price):,}".replace(",", " ") if price is not None else ""


_HOLD_FLOOR_VARIANTS = (
    "Je suis déjà à {p} F, c'est vraiment mon dernier prix 🙏",
    "{p} F c'est le prix final, je ne peux pas descendre plus bas !",
    "Crois-moi, à {p} F tu fais une bonne affaire — je ne bouge plus !",
)


def _action_text(action: Action, sctx: SpeechContext) -> str:
    t, facts = action.type, set(action.facts)
    p = _fmt(action.price)

    if t == ActionType.SEND_PHOTO:
        return "C'est la seule photo que j'ai pour l'instant, la voilà ! 😊" \
            if "only_photo" in facts else "Voilà la photo ! 😊"
    if t == ActionType.SEND_VARIANTS:
        return "Je t'envoie les autres modèles disponibles 👇"
    if t == ActionType.SEND_LOCATION:
        return "Je t'envoie la localisation !"
    if t == ActionType.SEND_PAYMENT_INFO:
        return "Voici nos moyens de paiement :"
    if t == ActionType.COUNTER_OFFER:
        if "hold_floor" in facts:
            variant = _HOLD_FLOOR_VARIANTS[sctx.round_seed % len(_HOLD_FLOOR_VARIANTS)]
            return variant.format(p=p)
        return f"Je peux te faire {p} F, c'est un bon prix !"
    if t == ActionType.CONFIRM_DEAL:
        return f"C'est bon pour {p} F ! 🤝 Tu préfères la livraison ou tu passes chercher ?"
    if t == ActionType.REQUEST_ADDRESS:
        return "Parfait ! Donne-moi ton adresse de livraison ?"
    if t == ActionType.END_CONVERSATION:
        return "Pas de souci, reviens quand tu veux ! 😊"
    if t == ActionType.JOIN_WAITLIST:
        return "Réponds *OUI* pour rejoindre la liste prioritaire 🔔"
    if t == ActionType.HANDOVER_HUMAN:
        return "Je transmets au vendeur, il te répond très vite !"
    if t == ActionType.NOTIFY_MERCHANT:
        return ""  # action interne, pas de texte client

    # SEND_TEXT — selon les facts
    if "greeting" in facts:
        return (f"Salut ! 😊 Oui, le {sctx.product_name} est disponible "
                f"à {_fmt(sctx.listed_price)} F. Tu veux plus d'infos ?")
    if "price_ok_pending" in facts:
        return f"Pour {p} F c'est bon pour moi ! Dis-moi quand tu confirmes 👍"
    if "clarify_deal" in facts:
        return "On se met d'accord à combien ? Dis-moi ton prix 😊"
    if "apaisement" in facts:
        return "Désolé si je t'ai froissé, ce n'était pas le but 🙏"
    if "correction" in facts:
        return "Pardon pour la confusion ! Reformule ta question, je t'écoute."
    if "delivery_info" in facts:
        return "Pour les frais et délais de livraison, le vendeur te confirme ça vite !"
    if "catalogue" in facts:
        return "On a d'autres articles en boutique ! Dis-moi ce que tu cherches."
    if "out_of_stock" in facts:
        return f"Le {sctx.product_name} est momentanément épuisé 😕"
    if "address_confirmed" in facts:
        return "C'est noté ! On te livre très vite 🚚"
    if "delivery_noted" in facts:
        return "Noté pour la livraison ! On règle d'abord le prix 😊"
    if "only_photo" in facts:
        return "C'est la seule photo que j'ai pour l'instant !"
    if any(f.startswith("info") for f in facts):
        if "info:prix" in facts:
            return f"Le {sctx.product_name} est à {_fmt(sctx.listed_price)} F."
        return f"Bonne question ! Le {sctx.product_name} : je te confirme ça tout de suite."
    return "Je ne suis pas sûr d'avoir compris — tu peux préciser ? 😊"


def render_fallback(plan: ActionPlan, sctx: SpeechContext) -> str:
    """Gabarits déterministes : corrects, jamais indisponibles, jamais faux."""
    parts = [_action_text(a, sctx) for a in plan.actions]
    return " ".join(x for x in parts if x).strip()
```

- [ ] Run → PASS (6) · Commit `feat(dialogue): gabarits de parole déterministes (variété anti-boucle)`

---

## Task 4: speech.py — rendu LLM contraint

- [ ] **Tests (rouge)** — ajout à `test_dialogue_speech.py`

```python
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
```

- [ ] **Implémentation** — ajout en fin de `speech.py`

```python
def build_brief(plan: ActionPlan, sctx: SpeechContext) -> dict:
    """Brief verrouillé envoyé au LLM : la décision, les faits, les interdits."""
    forbidden = ["mentionner le prix minimum/plancher",
                 f"proposer un prix sous {int(sctx.floor_price)} F"]
    from .output_guard import _DEAL_STATES  # même définition que le filet
    if plan.new_state not in _DEAL_STATES:
        forbidden.append("conclure la vente ou parler de livraison/retrait")

    return {
        "actions": [
            {"type": a.type.value, "price": a.price, "facts": list(a.facts)}
            for a in plan.actions
        ],
        "state": plan.new_state.value,
        "product_name": sctx.product_name,
        "listed_price": sctx.listed_price,
        "client_message": sctx.client_message,
        "persona": sctx.persona or {},
        "memory": sctx.memory_block,
        "forbidden": forbidden,
    }


async def render(plan: ActionPlan, sctx: SpeechContext,
                 llm: Optional[LLMClient]) -> str:
    """Rendu final : LLM contraint si disponible, gabarits sinon. Jamais faux."""
    if llm is None:
        return render_fallback(plan, sctx)

    brief = build_brief(plan, sctx)
    text = await llm.speak(brief)
    if text:
        verdict = guard_output(text, plan, sctx.floor_price)
        if verdict.ok:
            return text
        # Une seule reprise corrective, avec le motif
        retry_brief = dict(brief, violations=verdict.violations)
        text = await llm.speak(retry_brief)
        if text and guard_output(text, plan, sctx.floor_price).ok:
            return text

    return render_fallback(plan, sctx)
```

- [ ] Run → PASS · Commit `feat(dialogue): rendu LLM contraint (brief verrouillé + reprise + repli gabarits)`

---

## Task 5: llm_classifier.py

- [ ] **Tests (rouge)** — `kalga-api/tests/test_dialogue_classifier.py`

```python
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
```

- [ ] **Implémentation** — `kalga-api/app/services/dialogue/llm_classifier.py`

```python
"""
Étage ② (secours) — Classifieur LLM pour les messages ambigus (spec §9).

Appelé UNIQUEMENT quand les règles retournent UNCLEAR (P4). Le LLM ne peut
émettre que des types du catalogue — tout le reste est jeté. Échec, vide ou
inconnu → [UNCLEAR] : le bot demandera une clarification, jamais une action
inventée.
"""
import logging
from typing import Any, Dict, List, Optional

from .intents import Intent, IntentType
from .llm_protocol import LLMClient

logger = logging.getLogger("kalga.dialogue.classifier")

_VALID_TYPES = {t.value: t for t in IntentType}


async def classify_with_llm(message: str, llm: Optional[LLMClient],
                            context: Dict[str, Any]) -> List[Intent]:
    if llm is None:
        return [Intent(IntentType.UNCLEAR)]
    try:
        raw = await llm.classify(message, context)
    except Exception as e:  # un classifieur ne doit JAMAIS casser le flux
        logger.warning(f"Classifieur LLM en erreur: {e}")
        raw = None

    intents: List[Intent] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        intent_type = _VALID_TYPES.get(item.get("type"))
        if intent_type is None or intent_type == IntentType.UNCLEAR:
            continue
        amount = item.get("amount")
        intents.append(Intent(
            intent_type,
            amount=float(amount) if amount is not None else None,
            text=item.get("text"),
        ))

    return intents or [Intent(IntentType.UNCLEAR)]
```

- [ ] Run → PASS (5) · Commit `feat(dialogue): classifieur LLM de secours (catalogue imposé)`

---

## Task 6: Scénarios niveau voix + vérification finale

- [ ] **Tests** — `kalga-api/tests/test_dialogue_voice_scenarios.py`

```python
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
```

- [ ] Run scénarios → PASS · Suite complète `python -m pytest tests/ -q` → ≈ 225 verts + `from app.main import app` OK
- [ ] Spec §12 : P3 → « — ✅ fait »
- [ ] Commit + push

```bash
git add kalga-api/tests/test_dialogue_voice_scenarios.py
git add -f docs/superpowers/specs/2026-06-11-refonte-moteur-dialogue-design.md
git commit -m "test(dialogue): scénarios voix — un LLM qui dérape ne peut plus produire les bugs terrain"
git push
```

---

## Dette tracée / notes pour P4

- L'adaptateur DeepSeek réel (`classify`/`speak` → API) = P4, avec prompts dédiés ; tout le comportement est déjà prouvé au FakeLLM.
- `memory_block`/`persona` sont transportés dans le brief mais c'est P4 qui les alimentera (STM/LTM/épisodique existants).
- `round_seed` sera alimenté par `len(conversation_history)` au branchement.
