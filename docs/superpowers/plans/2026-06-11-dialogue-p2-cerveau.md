# Refonte dialogue — Phase 2 : Le cerveau — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire l'étage ③ (décision) : machine à états de vente, calcul de négociation et politique de dialogue — le bot « pense » entièrement, sans LLM, vérifiable au test.

**Architecture:** Quatre modules purs dans `app/services/dialogue/` : `sale_state` (FSM + mapping statuts DB), `actions` (catalogue d'actions + plan), `negotiation` (contre-offres calculées), `policy` (intentions + état + contexte → plan d'actions). Aucun appel LLM/DB. Corpus de scénarios = les 3 bugs terrain rejoués **au niveau décision**.

**Tech Stack:** Python 3.12, dataclasses/Enum, pytest (infra existante).

**Spec :** `docs/superpowers/specs/2026-06-11-refonte-moteur-dialogue-design.md` §6, §7, §8.

**Notes d'exécution :** pytest depuis `kalga-api/`, git depuis la racine, branche `refonte/moteur-dialogue` vérifiée avant chaque commit.

---

## Décisions de conception (gravées ici, testées ensuite)

1. **Verrou de CONCLUSION** (spec §6) : `CONFIRM_DEAL` n'est émis que si (a) `ACCEPT_PRICE` avec montant ≥ plancher, ou (b) `ACCEPT_PRICE` sans montant **et** `last_bot_price` posé (le bot venait de chiffrer), **et** (c) **aucune demande (`ASK_*`) dans le même message**. Sinon : on honore les demandes et on note le prix (`new_offer`) sans conclure — le client confirme au tour suivant.
2. **Négociation** (spec §8) : offre ≥ prix demandé → accepter à l'offre (plafonnée au prix affiché) ; offre ≥ plancher → accepter à l'offre ; offre < plancher → contre-offre au **milieu entre prix demandé et max(offre, plancher)**, arrondie commerçant (500 F), jamais sous le plancher ; déjà au plancher → **tenir** (`hold_floor`) sans limite de tours (décision marchand : « jusqu'à l'entente »).
3. **Une offre client annule tout pré-accord** : `PRICE_OFFER` en CONCLUSION/LOGISTIQUE → retour NÉGOCIATION.
4. **Changement livraison↔retrait accepté en LOGISTIQUE** (bug « Je veux me faire livré » ignoré).
5. **SEND_TEXT porte des `facts`** (étiquettes sémantiques : `greeting`, `info:prix`, `apaisement`, `price_ok_pending`, `reconfirm_deal`, `clarify`…) — l'étage parole (P3) les transformera en phrases ; les gabarits de secours aussi.

## Structure des fichiers

| Fichier | Action | Responsabilité |
|---|---|---|
| `kalga-api/app/services/dialogue/sale_state.py` | Créer | FSM de vente + mapping statuts DB |
| `kalga-api/app/services/dialogue/actions.py` | Créer | Catalogue d'actions + ActionPlan |
| `kalga-api/app/services/dialogue/negotiation.py` | Créer | Décision de négo (pur) |
| `kalga-api/app/services/dialogue/policy.py` | Créer | (intentions, état, contexte) → ActionPlan |
| `kalga-api/tests/test_dialogue_sale_state.py` | Créer | Tests FSM/mapping |
| `kalga-api/tests/test_dialogue_negotiation.py` | Créer | Tests négo |
| `kalga-api/tests/test_dialogue_policy.py` | Créer | Tests politique |
| `kalga-api/tests/test_dialogue_scenarios.py` | Créer | Scénarios bout-en-bout niveau cerveau |

---

## Task 1: sale_state.py

- [ ] **Step 1: Tests (rouge)** — `kalga-api/tests/test_dialogue_sale_state.py`

```python
"""Tests de la machine à états de vente."""
from app.services.dialogue.sale_state import SaleState, DB_STATUS, from_db_status


def test_all_states_map_to_existing_db_statuses():
    # Aucune migration : on retombe sur les statuts DB actuels
    assert set(DB_STATUS) == set(SaleState)
    assert set(DB_STATUS.values()) <= {
        "active", "negotiating", "agreed", "pending_delivery",
        "pending_pickup", "completed", "ended",
    }


def test_db_mapping_values():
    assert DB_STATUS[SaleState.ACCUEIL] == "active"
    assert DB_STATUS[SaleState.RENSEIGNEMENT] == "active"
    assert DB_STATUS[SaleState.NEGOCIATION] == "negotiating"
    assert DB_STATUS[SaleState.CONCLUSION] == "agreed"
    assert DB_STATUS[SaleState.LOGISTIQUE_LIVRAISON] == "pending_delivery"
    assert DB_STATUS[SaleState.LOGISTIQUE_RETRAIT] == "pending_pickup"
    assert DB_STATUS[SaleState.APRES_VENTE] == "completed"
    assert DB_STATUS[SaleState.FIN] == "ended"


def test_from_db_status_active_first_message_is_accueil():
    assert from_db_status("active", message_count=1) == SaleState.ACCUEIL


def test_from_db_status_active_later_is_renseignement():
    assert from_db_status("active", message_count=5) == SaleState.RENSEIGNEMENT


def test_from_db_status_known_statuses():
    assert from_db_status("negotiating", 9) == SaleState.NEGOCIATION
    assert from_db_status("agreed", 9) == SaleState.CONCLUSION
    assert from_db_status("pending_delivery", 9) == SaleState.LOGISTIQUE_LIVRAISON
    assert from_db_status("pending_pickup", 9) == SaleState.LOGISTIQUE_RETRAIT
    assert from_db_status("completed", 9) == SaleState.APRES_VENTE
    assert from_db_status("ended", 9) == SaleState.FIN


def test_from_db_status_unknown_defaults_to_renseignement():
    assert from_db_status("abandoned", 9) == SaleState.RENSEIGNEMENT
```

- [ ] **Step 2:** Run `python -m pytest tests/test_dialogue_sale_state.py -q` → FAIL (module absent)

- [ ] **Step 3: Implémentation** — `kalga-api/app/services/dialogue/sale_state.py`

```python
"""
Étage ③ — Machine à états de vente (spec §6).

La méthode de vente du marchand, formalisée. Les états internes se projettent
sur les statuts DB EXISTANTS (aucune migration, le dashboard reste compatible).
"""
from enum import Enum


class SaleState(str, Enum):
    ACCUEIL = "accueil"
    RENSEIGNEMENT = "renseignement"
    NEGOCIATION = "negociation"
    CONCLUSION = "conclusion"
    LOGISTIQUE_LIVRAISON = "logistique_livraison"
    LOGISTIQUE_RETRAIT = "logistique_retrait"
    APRES_VENTE = "apres_vente"
    FIN = "fin"


DB_STATUS = {
    SaleState.ACCUEIL: "active",
    SaleState.RENSEIGNEMENT: "active",
    SaleState.NEGOCIATION: "negotiating",
    SaleState.CONCLUSION: "agreed",
    SaleState.LOGISTIQUE_LIVRAISON: "pending_delivery",
    SaleState.LOGISTIQUE_RETRAIT: "pending_pickup",
    SaleState.APRES_VENTE: "completed",
    SaleState.FIN: "ended",
}

_FROM_DB = {
    "negotiating": SaleState.NEGOCIATION,
    "agreed": SaleState.CONCLUSION,
    "pending_delivery": SaleState.LOGISTIQUE_LIVRAISON,
    "pending_pickup": SaleState.LOGISTIQUE_RETRAIT,
    "completed": SaleState.APRES_VENTE,
    "ended": SaleState.FIN,
}


def from_db_status(status: str, message_count: int) -> SaleState:
    """Statut DB → état interne. « active » se raffine selon l'avancement."""
    if status == "active":
        return SaleState.ACCUEIL if message_count <= 1 else SaleState.RENSEIGNEMENT
    return _FROM_DB.get(status, SaleState.RENSEIGNEMENT)
```

- [ ] **Step 4:** Run → PASS (7) · **Step 5:** Commit `feat(dialogue): machine à états de vente + mapping statuts DB`

---

## Task 2: actions.py

- [ ] **Step 1: Tests (rouge)** — début de `kalga-api/tests/test_dialogue_policy.py`

```python
"""Tests de la politique de dialogue (et du catalogue d'actions)."""
from app.services.dialogue.actions import Action, ActionPlan, ActionType
from app.services.dialogue.sale_state import SaleState


def test_action_is_frozen_and_defaults():
    a = Action(ActionType.SEND_PHOTO)
    assert a.price is None and a.facts == ()


def test_action_plan_holds_actions_state_offer():
    plan = ActionPlan(
        actions=[Action(ActionType.COUNTER_OFFER, price=9000.0)],
        new_state=SaleState.NEGOCIATION,
        new_offer=9000.0,
    )
    assert plan.actions[0].price == 9000.0
    assert plan.new_state is SaleState.NEGOCIATION
```

- [ ] **Step 2:** Run → FAIL · **Step 3: Implémentation** — `kalga-api/app/services/dialogue/actions.py`

```python
"""
Étage ③ — Catalogue d'actions et plan (spec §7).

La politique produit un ActionPlan ORDONNÉ ; l'exécution (P4) le réalise ;
la parole (P3) habille les SEND_TEXT à partir de leurs `facts`.
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from .sale_state import SaleState


class ActionType(str, Enum):
    SEND_TEXT = "send_text"                  # facts sémantiques à formuler
    SEND_PHOTO = "send_photo"
    SEND_VARIANTS = "send_variants"
    SEND_LOCATION = "send_location"
    SEND_PAYMENT_INFO = "send_payment_info"
    COUNTER_OFFER = "counter_offer"          # price
    CONFIRM_DEAL = "confirm_deal"            # price — demande livraison/retrait
    REQUEST_ADDRESS = "request_address"
    NOTIFY_MERCHANT = "notify_merchant"      # reason
    HANDOVER_HUMAN = "handover_human"
    END_CONVERSATION = "end_conversation"
    JOIN_WAITLIST = "join_waitlist"


@dataclass(frozen=True)
class Action:
    type: ActionType
    price: Optional[float] = None
    reason: Optional[str] = None
    facts: Tuple[str, ...] = ()


@dataclass
class ActionPlan:
    actions: List[Action]
    new_state: SaleState
    new_offer: Optional[float] = None
```

- [ ] **Step 4:** Run → PASS (2) · **Step 5:** Commit `feat(dialogue): catalogue d'actions + ActionPlan`

---

## Task 3: negotiation.py

- [ ] **Step 1: Tests (rouge)** — `kalga-api/tests/test_dialogue_negotiation.py`

```python
"""Tests du calcul de négociation (pur, déterministe)."""
from app.services.dialogue.negotiation import decide, NegotiationDecision


def test_offer_at_or_above_ask_accepts_at_offer_capped_to_listed():
    d = decide(client_offer=10000, listed_price=10000, floor_price=8000, last_bot_price=None)
    assert d.kind == "accept" and d.price == 10000


def test_offer_above_listed_is_capped():
    d = decide(client_offer=12000, listed_price=10000, floor_price=8000, last_bot_price=None)
    assert d.kind == "accept" and d.price == 10000


def test_offer_between_floor_and_ask_accepts_at_offer():
    # Décision marchand : un prix ≥ plancher est un deal — on ne le risque pas
    d = decide(client_offer=9000, listed_price=10000, floor_price=8000, last_bot_price=None)
    assert d.kind == "accept" and d.price == 9000


def test_low_offer_counters_midway_rounded_500():
    # ask=10000, max(offre,plancher)=8000 → milieu 9000
    d = decide(client_offer=5000, listed_price=10000, floor_price=8000, last_bot_price=None)
    assert d.kind == "counter" and d.price == 9000


def test_counter_decreases_across_rounds_until_floor():
    # Tour 2 : ask=9000 → milieu (9000+8000)/2 = 8500
    d = decide(client_offer=5000, listed_price=10000, floor_price=8000, last_bot_price=9000)
    assert d.kind == "counter" and d.price == 8500
    # Tour 3 : ask=8500 → milieu 8250 → arrondi 500 = 8000 (plancher, pas en dessous)
    d = decide(client_offer=5000, listed_price=10000, floor_price=8000, last_bot_price=8500)
    assert d.kind == "counter" and d.price == 8000


def test_at_floor_holds_forever():
    # Déjà au plancher → on TIENT, sans limite de tours (décision marchand)
    d = decide(client_offer=5000, listed_price=10000, floor_price=8000, last_bot_price=8000)
    assert d.kind == "hold_floor" and d.price == 8000


def test_objection_without_amount_concedes_midway_to_floor():
    d = decide(client_offer=None, listed_price=10000, floor_price=8000, last_bot_price=None)
    assert d.kind == "counter" and d.price == 9000


def test_objection_at_floor_holds():
    d = decide(client_offer=None, listed_price=10000, floor_price=8000, last_bot_price=8000)
    assert d.kind == "hold_floor" and d.price == 8000


def test_counter_never_below_floor():
    d = decide(client_offer=7900, listed_price=8200, floor_price=8000, last_bot_price=None)
    assert d.price >= 8000
```

- [ ] **Step 2:** Run → FAIL · **Step 3: Implémentation** — `kalga-api/app/services/dialogue/negotiation.py`

```python
"""
Étage ③ — Décision de négociation (spec §8). 100 % code, 0 % LLM.

Règles (validées par le marchand) :
- offre ≥ prix demandé → accepter (plafonné au prix affiché : jamais surfacturer) ;
- offre ≥ plancher → accepter à l'offre (un deal au-dessus du plancher ne se risque pas) ;
- offre < plancher → contre-offre au milieu entre le prix demandé et
  max(offre, plancher), arrondie commerçant (500 F), jamais sous le plancher —
  concessions naturellement décroissantes, convergence vers le plancher ;
- déjà au plancher → TENIR, sans limite de tours (« jusqu'à l'entente ») ;
  la variation des formulations est l'affaire de la parole (P3).
"""
from dataclasses import dataclass
from typing import Optional

_ROUND_STEP = 500


@dataclass(frozen=True)
class NegotiationDecision:
    kind: str          # "accept" | "counter" | "hold_floor"
    price: float


def _round_commercant(price: float) -> float:
    return round(price / _ROUND_STEP) * _ROUND_STEP


def decide(
    client_offer: Optional[float],
    listed_price: float,
    floor_price: float,
    last_bot_price: Optional[float],
) -> NegotiationDecision:
    ask = last_bot_price if last_bot_price is not None else listed_price

    if client_offer is not None:
        if client_offer >= ask:
            return NegotiationDecision("accept", min(client_offer, listed_price))
        if client_offer >= floor_price:
            return NegotiationDecision("accept", float(client_offer))

    # Offre basse ou objection sans chiffre → concession vers le plancher
    if ask <= floor_price:
        return NegotiationDecision("hold_floor", float(floor_price))

    anchor = max(client_offer or floor_price, floor_price)
    target = max(floor_price, _round_commercant((ask + anchor) / 2))
    if target >= ask:  # l'arrondi ne doit jamais remonter le prix
        target = max(floor_price, ask - _ROUND_STEP)
    return NegotiationDecision("counter", float(target))
```

- [ ] **Step 4:** Run → PASS (9) · **Step 5:** Commit `feat(dialogue): calcul de négociation (accept/counter/hold_floor)`

---

## Task 4: policy.py — demandes du client

- [ ] **Step 1: Tests (rouge)** — ajout à `test_dialogue_policy.py`

```python
from app.services.dialogue.intents import Intent, IntentType
from app.services.dialogue.policy import PolicyContext, decide_plan


def _ctx(state=SaleState.RENSEIGNEMENT, **kw):
    defaults = dict(listed_price=10000.0, floor_price=8000.0, current_offer=None,
                    has_variants=False, has_photo=True, stock_out=False,
                    last_bot_price=None)
    defaults.update(kw)
    return PolicyContext(state=state, **defaults)


def test_ask_photo_yields_send_photo():
    plan = decide_plan([Intent(IntentType.ASK_PHOTO)], _ctx())
    assert plan.actions[0].type == ActionType.SEND_PHOTO
    assert plan.new_state == SaleState.RENSEIGNEMENT


def test_ask_other_photos_routes_by_variants():
    p1 = decide_plan([Intent(IntentType.ASK_OTHER_PHOTOS)], _ctx(has_variants=True))
    assert p1.actions[0].type == ActionType.SEND_VARIANTS
    p2 = decide_plan([Intent(IntentType.ASK_OTHER_PHOTOS)], _ctx(has_variants=False))
    assert p2.actions[0].type == ActionType.SEND_PHOTO


def test_ask_location_never_concludes():
    plan = decide_plan([Intent(IntentType.ASK_LOCATION)], _ctx(state=SaleState.NEGOCIATION))
    assert plan.actions[0].type == ActionType.SEND_LOCATION
    assert plan.new_state == SaleState.NEGOCIATION


def test_ask_payment_and_info_and_delivery_info():
    assert decide_plan([Intent(IntentType.ASK_PAYMENT)], _ctx()).actions[0].type == ActionType.SEND_PAYMENT_INFO
    info = decide_plan([Intent(IntentType.ASK_INFO, text="prix")], _ctx()).actions[0]
    assert info.type == ActionType.SEND_TEXT and "info:prix" in info.facts
    dlv = decide_plan([Intent(IntentType.ASK_DELIVERY_INFO)], _ctx()).actions[0]
    assert dlv.type == ActionType.SEND_TEXT and "delivery_info" in dlv.facts


def test_photo_request_honored_even_in_conclusion():
    # Règle transverse marchand : photo demandée → photo, TOUJOURS
    plan = decide_plan([Intent(IntentType.ASK_PHOTO)], _ctx(state=SaleState.CONCLUSION))
    assert plan.actions[0].type == ActionType.SEND_PHOTO
    assert plan.new_state == SaleState.CONCLUSION
```

- [ ] **Step 2:** Run → FAIL · **Step 3: Implémentation** — `kalga-api/app/services/dialogue/policy.py`

```python
"""
Étage ③ — Politique de dialogue (spec §6, §7).

decide_plan(intents, ctx) -> ActionPlan : fonction PURE. C'est ici — et nulle
part ailleurs — que se décident les actions et les transitions d'état. Le LLM
n'y a aucun droit de regard ; il habillera le plan (P3).

Invariants gravés (décisions du marchand) :
- toute demande (ASK_*) est honorée, dans tous les états, avant la vente ;
- CONFIRM_DEAL impossible si une demande arrive dans le même message ;
- un « accord » sans prix sur la table ne conclut jamais ;
- une contre-offre client annule tout pré-accord (retour NÉGOCIATION) ;
- livraison ↔ retrait modifiable en LOGISTIQUE.
"""
from dataclasses import dataclass
from typing import List, Optional

from .actions import Action, ActionPlan, ActionType
from .intents import Intent, IntentType
from .negotiation import decide as negotiate
from .sale_state import SaleState

_REQUEST_TYPES = {
    IntentType.ASK_PHOTO, IntentType.ASK_OTHER_PHOTOS, IntentType.ASK_VARIANTS,
    IntentType.ASK_OTHER_PRODUCTS, IntentType.ASK_INFO, IntentType.ASK_LOCATION,
    IntentType.ASK_PAYMENT, IntentType.ASK_DELIVERY_INFO,
}
_DEAL_STATES = {SaleState.CONCLUSION, SaleState.LOGISTIQUE_LIVRAISON,
                SaleState.LOGISTIQUE_RETRAIT}


@dataclass
class PolicyContext:
    state: SaleState
    listed_price: float
    floor_price: float                 # plancher effectif (fidélité déjà appliquée)
    current_offer: Optional[float]     # prix sur la table (accord de principe)
    has_variants: bool
    has_photo: bool
    stock_out: bool = False
    last_bot_price: Optional[float] = None  # dernier prix chiffré par le bot


def _handle_request(intent: Intent, ctx: PolicyContext) -> Action:
    t = intent.type
    if t == IntentType.ASK_PHOTO:
        return Action(ActionType.SEND_PHOTO)
    if t == IntentType.ASK_OTHER_PHOTOS:
        return Action(ActionType.SEND_VARIANTS) if ctx.has_variants \
            else Action(ActionType.SEND_PHOTO, facts=("only_photo",))
    if t == IntentType.ASK_VARIANTS:
        return Action(ActionType.SEND_VARIANTS)
    if t == IntentType.ASK_OTHER_PRODUCTS:
        return Action(ActionType.SEND_TEXT, facts=("catalogue",))
    if t == IntentType.ASK_LOCATION:
        return Action(ActionType.SEND_LOCATION)
    if t == IntentType.ASK_PAYMENT:
        return Action(ActionType.SEND_PAYMENT_INFO)
    if t == IntentType.ASK_DELIVERY_INFO:
        return Action(ActionType.SEND_TEXT, facts=("delivery_info",))
    # ASK_INFO
    subject = f"info:{intent.text}" if intent.text else "info"
    return Action(ActionType.SEND_TEXT, facts=(subject,))
```

*(la suite de `decide_plan` arrive aux Tasks 5-6 — à ce stade, version minimale :)*

```python
def decide_plan(intents: List[Intent], ctx: PolicyContext) -> ActionPlan:
    actions: List[Action] = []
    state = ctx.state
    offer = ctx.current_offer

    for intent in intents:
        if intent.type in _REQUEST_TYPES:
            actions.append(_handle_request(intent, ctx))

    if not actions:
        actions.append(Action(ActionType.SEND_TEXT, facts=("clarify",)))
    return ActionPlan(actions=actions, new_state=state, new_offer=offer)
```

- [ ] **Step 4:** Run → PASS · **Step 5:** Commit `feat(dialogue): policy — demandes client honorées dans tous les états`

---

## Task 5: policy.py — transactionnel (le verrou)

- [ ] **Step 1: Tests (rouge)** — ajout à `test_dialogue_policy.py`

```python
# === Transactionnel : le verrou de CONCLUSION ===

def test_offer_above_floor_alone_confirms_deal():
    plan = decide_plan([Intent(IntentType.PRICE_OFFER, amount=9000.0)],
                       _ctx(state=SaleState.NEGOCIATION))
    assert plan.actions[-1].type == ActionType.CONFIRM_DEAL
    assert plan.actions[-1].price == 9000.0
    assert plan.new_state == SaleState.CONCLUSION
    assert plan.new_offer == 9000.0


def test_bug1_offer_plus_photo_never_concludes():
    """Bug terrain n°1 au niveau cerveau : photo + 9000 → photo + prix noté, PAS de clôture."""
    intents = [Intent(IntentType.ASK_OTHER_PHOTOS), Intent(IntentType.PRICE_OFFER, amount=9000.0)]
    plan = decide_plan(intents, _ctx(state=SaleState.NEGOCIATION, has_variants=True))
    types = [a.type for a in plan.actions]
    assert ActionType.SEND_VARIANTS in types
    assert ActionType.CONFIRM_DEAL not in types
    assert any(a.type == ActionType.SEND_TEXT and "price_ok_pending" in a.facts
               for a in plan.actions)
    assert plan.new_state == SaleState.NEGOCIATION  # pas conclu
    assert plan.new_offer == 9000.0                  # mais prix noté


def test_low_offer_counters():
    plan = decide_plan([Intent(IntentType.PRICE_OFFER, amount=5000.0)],
                       _ctx(state=SaleState.NEGOCIATION))
    assert plan.actions[-1].type == ActionType.COUNTER_OFFER
    assert plan.actions[-1].price == 9000.0  # milieu(10000, 8000)
    assert plan.new_state == SaleState.NEGOCIATION


def test_accept_with_amount_confirms():
    plan = decide_plan([Intent(IntentType.ACCEPT_PRICE, amount=9000.0)],
                       _ctx(state=SaleState.NEGOCIATION))
    assert plan.actions[-1].type == ActionType.CONFIRM_DEAL
    assert plan.new_state == SaleState.CONCLUSION


def test_bare_accept_with_bot_price_confirms_at_that_price():
    plan = decide_plan([Intent(IntentType.ACCEPT_PRICE)],
                       _ctx(state=SaleState.NEGOCIATION, last_bot_price=9500.0))
    assert plan.actions[-1].type == ActionType.CONFIRM_DEAL
    assert plan.actions[-1].price == 9500.0


def test_bare_accept_without_any_price_never_concludes():
    """Le « oui » sans prix sur la table → clarification, jamais de vente."""
    plan = decide_plan([Intent(IntentType.ACCEPT_PRICE)], _ctx(state=SaleState.RENSEIGNEMENT))
    assert all(a.type != ActionType.CONFIRM_DEAL for a in plan.actions)
    assert any("clarify_deal" in a.facts for a in plan.actions if a.type == ActionType.SEND_TEXT)


def test_accept_with_pending_request_defers_conclusion():
    intents = [Intent(IntentType.ASK_PHOTO), Intent(IntentType.ACCEPT_PRICE, amount=9000.0)]
    plan = decide_plan(intents, _ctx(state=SaleState.NEGOCIATION))
    types = [a.type for a in plan.actions]
    assert ActionType.SEND_PHOTO in types and ActionType.CONFIRM_DEAL not in types
    assert plan.new_offer == 9000.0


def test_new_offer_in_conclusion_cancels_agreement():
    plan = decide_plan([Intent(IntentType.PRICE_OFFER, amount=8500.0)],
                       _ctx(state=SaleState.CONCLUSION, current_offer=9500.0))
    assert plan.actions[-1].type == ActionType.CONFIRM_DEAL or plan.new_state == SaleState.CONCLUSION
    # 8500 ≥ plancher → ré-accord direct au nouveau prix
    assert plan.new_offer == 8500.0


def test_accept_below_floor_counters():
    plan = decide_plan([Intent(IntentType.ACCEPT_PRICE, amount=5000.0)],
                       _ctx(state=SaleState.NEGOCIATION))
    assert plan.actions[-1].type == ActionType.COUNTER_OFFER
    assert plan.new_state == SaleState.NEGOCIATION
```

- [ ] **Step 2:** Run → FAIL · **Step 3:** Remplacer `decide_plan` par la version transactionnelle

```python
def decide_plan(intents: List[Intent], ctx: PolicyContext) -> ActionPlan:
    actions: List[Action] = []
    state = ctx.state
    offer = ctx.current_offer

    has_request = any(i.type in _REQUEST_TYPES for i in intents)

    # 1) Demandes du client — toujours, d'abord
    for intent in intents:
        if intent.type in _REQUEST_TYPES:
            actions.append(_handle_request(intent, ctx))

    # 2) Transactionnel
    for intent in intents:
        if intent.type == IntentType.PRICE_OFFER:
            decision = negotiate(intent.amount, ctx.listed_price,
                                 ctx.floor_price, ctx.last_bot_price)
            if decision.kind == "accept":
                offer = decision.price
                if has_request:
                    # Verrou : pas de clôture avec une demande en attente —
                    # on note le prix, le client confirmera au tour suivant.
                    actions.append(Action(ActionType.SEND_TEXT,
                                          facts=("price_ok_pending",), price=decision.price))
                    state = SaleState.NEGOCIATION
                else:
                    actions.append(Action(ActionType.CONFIRM_DEAL, price=decision.price))
                    state = SaleState.CONCLUSION
            else:
                kind = "hold_floor" if decision.kind == "hold_floor" else "counter"
                actions.append(Action(ActionType.COUNTER_OFFER, price=decision.price,
                                      facts=(kind,)))
                state = SaleState.NEGOCIATION
                offer = None  # plus d'accord sur la table

        elif intent.type == IntentType.ACCEPT_PRICE:
            amount = intent.amount if intent.amount is not None else ctx.last_bot_price
            if amount is None:
                actions.append(Action(ActionType.SEND_TEXT, facts=("clarify_deal",)))
                continue
            if amount < ctx.floor_price:
                decision = negotiate(amount, ctx.listed_price,
                                     ctx.floor_price, ctx.last_bot_price)
                actions.append(Action(ActionType.COUNTER_OFFER, price=decision.price,
                                      facts=("counter",)))
                state = SaleState.NEGOCIATION
                offer = None
            elif has_request:
                offer = float(amount)
                actions.append(Action(ActionType.SEND_TEXT,
                                      facts=("price_ok_pending",), price=float(amount)))
                state = SaleState.NEGOCIATION
            else:
                offer = float(amount)
                actions.append(Action(ActionType.CONFIRM_DEAL, price=float(amount)))
                state = SaleState.CONCLUSION

    if not actions:
        actions.append(Action(ActionType.SEND_TEXT, facts=("clarify",)))
    return ActionPlan(actions=actions, new_state=state, new_offer=offer)
```

- [ ] **Step 4:** Run → PASS · **Step 5:** Commit `feat(dialogue): policy — verrou de CONCLUSION et négociation câblée`

---

## Task 6: policy.py — logistique, flux & signaux

- [ ] **Step 1: Tests (rouge)** — ajout à `test_dialogue_policy.py`

```python
# === Logistique, flux & signaux ===

def test_choose_delivery_after_deal_requests_address():
    plan = decide_plan([Intent(IntentType.CHOOSE_DELIVERY)], _ctx(state=SaleState.CONCLUSION))
    assert plan.actions[0].type == ActionType.REQUEST_ADDRESS
    assert plan.new_state == SaleState.LOGISTIQUE_LIVRAISON


def test_switch_pickup_to_delivery_in_logistics():
    """Bug terrain : « Je veux me faire livré » après un retrait — désormais accepté."""
    plan = decide_plan([Intent(IntentType.CHOOSE_DELIVERY)],
                       _ctx(state=SaleState.LOGISTIQUE_RETRAIT))
    assert plan.actions[0].type == ActionType.REQUEST_ADDRESS
    assert plan.new_state == SaleState.LOGISTIQUE_LIVRAISON


def test_choose_pickup_after_deal_sends_location_and_notifies():
    plan = decide_plan([Intent(IntentType.CHOOSE_PICKUP)], _ctx(state=SaleState.CONCLUSION))
    types = [a.type for a in plan.actions]
    assert ActionType.SEND_LOCATION in types and ActionType.NOTIFY_MERCHANT in types
    assert plan.new_state == SaleState.LOGISTIQUE_RETRAIT


def test_choose_pickup_without_deal_just_sends_location():
    plan = decide_plan([Intent(IntentType.CHOOSE_PICKUP)], _ctx(state=SaleState.RENSEIGNEMENT))
    assert plan.actions[0].type == ActionType.SEND_LOCATION
    assert plan.new_state == SaleState.RENSEIGNEMENT


def test_give_address_completes_logistics():
    plan = decide_plan([Intent(IntentType.GIVE_ADDRESS, text="cocody angré")],
                       _ctx(state=SaleState.LOGISTIQUE_LIVRAISON))
    types = [a.type for a in plan.actions]
    assert ActionType.NOTIFY_MERCHANT in types
    assert plan.new_state == SaleState.APRES_VENTE


def test_goodbye_ends():
    plan = decide_plan([Intent(IntentType.GOODBYE)], _ctx())
    assert plan.actions[-1].type == ActionType.END_CONVERSATION
    assert plan.new_state == SaleState.FIN


def test_greeting_opens_conversation():
    plan = decide_plan([Intent(IntentType.GREETING)], _ctx(state=SaleState.ACCUEIL))
    a = plan.actions[0]
    assert a.type == ActionType.SEND_TEXT and "greeting" in a.facts
    assert plan.new_state == SaleState.RENSEIGNEMENT


def test_frustration_prepends_apaisement():
    intents = [Intent(IntentType.FRUSTRATION), Intent(IntentType.PRICE_OFFER, amount=5000.0)]
    plan = decide_plan(intents, _ctx(state=SaleState.NEGOCIATION))
    assert plan.actions[0].type == ActionType.SEND_TEXT and "apaisement" in plan.actions[0].facts
    assert plan.actions[-1].type == ActionType.COUNTER_OFFER


def test_human_request_hands_over():
    plan = decide_plan([Intent(IntentType.HUMAN_REQUEST)], _ctx())
    types = [a.type for a in plan.actions]
    assert ActionType.HANDOVER_HUMAN in types and ActionType.NOTIFY_MERCHANT in types


def test_correction_apologizes():
    plan = decide_plan([Intent(IntentType.CORRECTION)], _ctx())
    assert any("correction" in a.facts for a in plan.actions if a.type == ActionType.SEND_TEXT)


def test_stock_out_offers_waitlist_instead_of_deal():
    plan = decide_plan([Intent(IntentType.PRICE_OFFER, amount=9000.0)],
                       _ctx(state=SaleState.RENSEIGNEMENT, stock_out=True))
    types = [a.type for a in plan.actions]
    assert ActionType.JOIN_WAITLIST in types and ActionType.CONFIRM_DEAL not in types


def test_unclear_clarifies():
    plan = decide_plan([Intent(IntentType.UNCLEAR)], _ctx())
    assert any("clarify" in a.facts for a in plan.actions)
```

- [ ] **Step 2:** Run → FAIL · **Step 3:** Compléter `decide_plan` (version finale P2)

```python
def decide_plan(intents: List[Intent], ctx: PolicyContext) -> ActionPlan:
    actions: List[Action] = []
    state = ctx.state
    offer = ctx.current_offer

    types = {i.type for i in intents}
    has_request = bool(types & _REQUEST_TYPES)

    # 0) Signaux prioritaires
    if IntentType.CORRECTION in types:
        actions.append(Action(ActionType.SEND_TEXT, facts=("correction",)))
    if IntentType.FRUSTRATION in types:
        actions.append(Action(ActionType.SEND_TEXT, facts=("apaisement",)))
    if IntentType.HUMAN_REQUEST in types:
        actions.append(Action(ActionType.HANDOVER_HUMAN))
        actions.append(Action(ActionType.NOTIFY_MERCHANT, reason="human_request"))
        return ActionPlan(actions=actions, new_state=state, new_offer=offer)

    # 1) Demandes du client — toujours honorées, d'abord
    for intent in intents:
        if intent.type in _REQUEST_TYPES:
            actions.append(_handle_request(intent, ctx))

    # 2) Rupture de stock : pas de transactionnel, proposer la liste d'attente
    if ctx.stock_out and (types & {IntentType.PRICE_OFFER, IntentType.ACCEPT_PRICE}):
        actions.append(Action(ActionType.SEND_TEXT, facts=("out_of_stock",)))
        actions.append(Action(ActionType.JOIN_WAITLIST))
        return ActionPlan(actions=actions, new_state=state, new_offer=offer)

    # 3) Transactionnel (verrou de CONCLUSION)
    for intent in intents:
        if intent.type == IntentType.PRICE_OFFER:
            decision = negotiate(intent.amount, ctx.listed_price,
                                 ctx.floor_price, ctx.last_bot_price)
            if decision.kind == "accept":
                offer = decision.price
                if has_request:
                    actions.append(Action(ActionType.SEND_TEXT,
                                          facts=("price_ok_pending",), price=decision.price))
                    state = SaleState.NEGOCIATION
                else:
                    actions.append(Action(ActionType.CONFIRM_DEAL, price=decision.price))
                    state = SaleState.CONCLUSION
            else:
                kind = "hold_floor" if decision.kind == "hold_floor" else "counter"
                actions.append(Action(ActionType.COUNTER_OFFER, price=decision.price,
                                      facts=(kind,)))
                state = SaleState.NEGOCIATION
                offer = None

        elif intent.type == IntentType.ACCEPT_PRICE:
            amount = intent.amount if intent.amount is not None else ctx.last_bot_price
            if amount is None:
                actions.append(Action(ActionType.SEND_TEXT, facts=("clarify_deal",)))
                continue
            if amount < ctx.floor_price:
                decision = negotiate(amount, ctx.listed_price,
                                     ctx.floor_price, ctx.last_bot_price)
                actions.append(Action(ActionType.COUNTER_OFFER, price=decision.price,
                                      facts=("counter",)))
                state = SaleState.NEGOCIATION
                offer = None
            elif has_request:
                offer = float(amount)
                actions.append(Action(ActionType.SEND_TEXT,
                                      facts=("price_ok_pending",), price=float(amount)))
                state = SaleState.NEGOCIATION
            else:
                offer = float(amount)
                actions.append(Action(ActionType.CONFIRM_DEAL, price=float(amount)))
                state = SaleState.CONCLUSION

    # 4) Logistique
    for intent in intents:
        if intent.type == IntentType.CHOOSE_DELIVERY:
            if state in _DEAL_STATES:
                actions.append(Action(ActionType.REQUEST_ADDRESS))
                state = SaleState.LOGISTIQUE_LIVRAISON
            else:
                actions.append(Action(ActionType.SEND_TEXT, facts=("delivery_noted",)))
        elif intent.type == IntentType.CHOOSE_PICKUP:
            if state in _DEAL_STATES:
                actions.append(Action(ActionType.SEND_LOCATION))
                actions.append(Action(ActionType.NOTIFY_MERCHANT, reason="pickup"))
                state = SaleState.LOGISTIQUE_RETRAIT
            else:
                actions.append(Action(ActionType.SEND_LOCATION))
        elif intent.type == IntentType.GIVE_ADDRESS and state == SaleState.LOGISTIQUE_LIVRAISON:
            actions.append(Action(ActionType.SEND_TEXT, facts=("address_confirmed",),
                                  reason=intent.text))
            actions.append(Action(ActionType.NOTIFY_MERCHANT, reason="delivery_address"))
            state = SaleState.APRES_VENTE

    # 5) Flux social
    if IntentType.GREETING in types and not actions:
        actions.append(Action(ActionType.SEND_TEXT, facts=("greeting",)))
        if state == SaleState.ACCUEIL:
            state = SaleState.RENSEIGNEMENT
    if IntentType.GOODBYE in types:
        actions.append(Action(ActionType.END_CONVERSATION))
        state = SaleState.FIN

    if not actions:
        actions.append(Action(ActionType.SEND_TEXT, facts=("clarify",)))
    return ActionPlan(actions=actions, new_state=state, new_offer=offer)
```

- [ ] **Step 4:** Run → PASS · **Step 5:** Commit `feat(dialogue): policy — logistique, flux social, signaux, rupture de stock`

---

## Task 7: Scénarios bout-en-bout (niveau cerveau) + vérification

- [ ] **Step 1: Tests** — `kalga-api/tests/test_dialogue_scenarios.py`

```python
"""Scénarios bout-en-bout au niveau cerveau : message brut → intentions → plan.

Rejoue les conversations réelles (captures WhatsApp) à travers
extract_intents + decide_plan, sans LLM ni DB. Le comportement attendu
est celui validé par le marchand.
"""
from app.services.dialogue.actions import ActionType
from app.services.dialogue.policy import PolicyContext, decide_plan
from app.services.dialogue.sale_state import SaleState
from app.services.dialogue.understanding import extract_intents


def think(message, state, last_bot=None, **ctx_kw):
    """Pipeline cerveau : compréhension → décision."""
    defaults = dict(listed_price=10000.0, floor_price=8000.0, current_offer=None,
                    has_variants=True, has_photo=True, stock_out=False,
                    last_bot_price=None)
    defaults.update(ctx_kw)
    intents = extract_intents(message, last_bot_message=last_bot)
    return decide_plan(intents, PolicyContext(state=state, **defaults))


def test_scenario_bug1_full():
    """Capture 1 : « Je veux ça à 9000 et envoie moi plus de photo »."""
    plan = think("Je veux ça à 9000 et envoie moi plus de photo", SaleState.NEGOCIATION)
    types = [a.type for a in plan.actions]
    assert ActionType.SEND_VARIANTS in types          # la demande visuelle d'abord
    assert ActionType.CONFIRM_DEAL not in types        # JAMAIS de clôture ici
    assert plan.new_offer == 9000.0                    # le prix est noté
    # ... puis le client confirme au tour suivant :
    plan2 = think("ok", SaleState.NEGOCIATION, last_bot="Pour 9 000 F c'est bon !",
                  last_bot_price=9000.0)
    assert plan2.actions[-1].type == ActionType.CONFIRM_DEAL
    assert plan2.actions[-1].price == 9000.0


def test_scenario_bug2_photos_then_no_banco():
    """Capture 2 : « Je veux d'autres photos » 2× — photos servies, zéro Banco."""
    for _ in range(2):
        plan = think("Je veux d'autres photos", SaleState.NEGOCIATION, has_variants=True)
        types = [a.type for a in plan.actions]
        assert types == [ActionType.SEND_VARIANTS]
        assert plan.new_state == SaleState.NEGOCIATION


def test_scenario_bug3_hello_on_status():
    """Capture 3 : « hello » sur un Statut → accueil, pas de photo."""
    plan = think('[Répond à la photo: "#K053"] Hello', SaleState.ACCUEIL)
    assert [a.type for a in plan.actions] == [ActionType.SEND_TEXT]
    assert "greeting" in plan.actions[0].facts
    assert plan.new_state == SaleState.RENSEIGNEMENT


def test_scenario_oui_interest_never_sells():
    """« Oui » à « ça t'intéresse ? » → clarification, zéro vente."""
    plan = think("Oui", SaleState.RENSEIGNEMENT, last_bot="Ça t'intéresse ?")
    assert all(a.type != ActionType.CONFIRM_DEAL for a in plan.actions)


def test_scenario_nominal_full_sale():
    """Parcours nominal : accueil → info → négo → conclusion → livraison."""
    p1 = think("bonjour, c'est disponible ?", SaleState.ACCUEIL)
    assert all(a.type != ActionType.CONFIRM_DEAL for a in p1.actions)

    p2 = think("envoie la photo", SaleState.RENSEIGNEMENT)
    assert p2.actions[0].type == ActionType.SEND_PHOTO

    p3 = think("je te donne 5000", SaleState.RENSEIGNEMENT)
    assert p3.actions[-1].type == ActionType.COUNTER_OFFER
    assert p3.actions[-1].price == 9000.0
    assert p3.new_state == SaleState.NEGOCIATION

    p4 = think("ok pour 9000", SaleState.NEGOCIATION, last_bot_price=9000.0)
    assert p4.actions[-1].type == ActionType.CONFIRM_DEAL
    assert p4.new_state == SaleState.CONCLUSION

    p5 = think("je veux me faire livrer", SaleState.CONCLUSION)
    assert p5.actions[0].type == ActionType.REQUEST_ADDRESS
    assert p5.new_state == SaleState.LOGISTIQUE_LIVRAISON

    p6 = think("cocody angré 7e tranche", SaleState.LOGISTIQUE_LIVRAISON,
               last_bot="Parfait ! Donne-moi ton adresse de livraison ?")
    assert any(a.type == ActionType.NOTIFY_MERCHANT for a in p6.actions)
    assert p6.new_state == SaleState.APRES_VENTE


def test_scenario_switch_pickup_to_delivery():
    """L'oubli de la capture 1 : changer retrait → livraison reste possible."""
    plan = think("finalement je veux me faire livrer", SaleState.LOGISTIQUE_RETRAIT)
    assert plan.actions[0].type == ActionType.REQUEST_ADDRESS
    assert plan.new_state == SaleState.LOGISTIQUE_LIVRAISON


def test_scenario_radin_holds_floor_forever():
    """Client radin : le bot tient le plancher sans jamais casser le prix."""
    plan = think("5000 dernier prix", SaleState.NEGOCIATION, last_bot_price=8000.0)
    assert plan.actions[-1].type == ActionType.COUNTER_OFFER
    assert plan.actions[-1].price == 8000.0
    assert "hold_floor" in plan.actions[-1].facts
```

- [ ] **Step 2:** Run `python -m pytest tests/test_dialogue_scenarios.py -v` → PASS (corriger la **règle**, jamais le scénario, si échec)

- [ ] **Step 3:** Suite complète : `python -m pytest tests/ -q` + `python -c "from app.main import app; print('OK')"` → ≈ 195 verts, OK.

- [ ] **Step 4:** Spec §12 : P2 → « — ✅ fait ».

- [ ] **Step 5:** Commit + push

```bash
git add kalga-api/tests/test_dialogue_scenarios.py
git add -f docs/superpowers/specs/2026-06-11-refonte-moteur-dialogue-design.md
git commit -m "test(dialogue): scénarios cerveau — les 3 bugs terrain décidés correctement sans LLM"
git push
```

---

## Dette tracée / notes pour P3

- `facts` est un vocabulaire libre pour l'instant — P3 (speech) le formalisera avec les gabarits.
- `PolicyContext.floor_price` suppose la fidélité déjà appliquée par l'appelant (P4 la branchera depuis `client_history`, logique existante).
- `JOIN_WAITLIST` délègue à la mécanique waitlist existante au branchement (P4).
- La variation anti-boucle des formulations `hold_floor` est l'affaire de P3 (parole).
