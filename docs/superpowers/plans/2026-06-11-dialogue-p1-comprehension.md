# Refonte dialogue — Phase 1 : Compréhension — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire l'étage de compréhension du nouveau moteur de dialogue : assainissement des entrées + catalogue d'intentions fermé + extraction **multi-intentions** par règles déterministes, entièrement testé (dont les 3 bugs terrain en corpus de régression).

**Architecture:** Nouveau paquet `app/services/dialogue/` (étages ① et ② de la spec). Modules purs, sans LLM ni DB. L'ancien chemin (`detectors.py`, `conversation_ai.py`) reste intact et vivant — pattern étrangleur : les deux coexistent jusqu'à la bascule P5. Seule exception : `deal_guard.py` réutilise le sanitizer canonique (suppression d'une duplication).

**Tech Stack:** Python 3.12, dataclasses/Enum, regex, pytest + pytest-asyncio (infra de test existante dans `kalga-api/tests/`).

**Spec de référence :** `docs/superpowers/specs/2026-06-11-refonte-moteur-dialogue-design.md` (§4, §5, §10, §11)

**Notes d'exécution :**
- Toutes les commandes `pytest` se lancent depuis `kalga-api/`. Les commandes git depuis la racine du repo.
- ⚠️ Avant CHAQUE commit : vérifier `git branch --show-current` == `refonte/moteur-dialogue` (le repo a un historique de bascules de branches concurrentes).
- Duplication temporaire assumée avec `detectors.py` : ce n'est pas du code mort, les deux chemins sont vivants jusqu'à P5 (spec §12).

---

## Structure des fichiers

| Fichier | Action | Responsabilité |
|---|---|---|
| `kalga-api/app/services/dialogue/__init__.py` | Créer | Paquet (exports publics) |
| `kalga-api/app/services/dialogue/sanitizer.py` | Créer | ① Nettoyage métadonnées bridge/système, normalisation |
| `kalga-api/app/services/dialogue/intents.py` | Créer | ② Catalogue fermé `IntentType` + dataclass `Intent` + priorité |
| `kalga-api/app/services/dialogue/understanding.py` | Créer | ② Extraction multi-intentions par règles |
| `kalga-api/app/services/ai/deal_guard.py` | Modifier | Importe `strip_context_prefix` depuis sanitizer (supprime sa copie) |
| `kalga-api/tests/test_dialogue_sanitizer.py` | Créer | Tests sanitizer |
| `kalga-api/tests/test_dialogue_intents.py` | Créer | Tests catalogue |
| `kalga-api/tests/test_dialogue_understanding.py` | Créer | Tests règles d'extraction |
| `kalga-api/tests/test_dialogue_corpus.py` | Créer | Corpus doré (3 bugs terrain + ~22 cas) |

---

## Task 0: Branche dédiée

- [ ] **Step 1: Créer la branche depuis l'état courant**

```bash
git checkout -b refonte/moteur-dialogue
git push -u origin refonte/moteur-dialogue
```

Expected: `Switched to a new branch 'refonte/moteur-dialogue'`, push OK. Tout le chantier P1→P5 vivra ici.

---

## Task 1: Sanitizer (étage ①)

**Files:**
- Create: `kalga-api/app/services/dialogue/__init__.py`
- Create: `kalga-api/app/services/dialogue/sanitizer.py`
- Modify: `kalga-api/app/services/ai/deal_guard.py` (~lignes 23-50 : `_CONTEXT_PREFIX_RE` + `strip_context_prefix` → import)
- Test: `kalga-api/tests/test_dialogue_sanitizer.py`

- [ ] **Step 1: Écrire les tests qui échouent**

```python
"""Tests du sanitizer — étage ① du pipeline de dialogue.

Les messages arrivent du bridge avec des préfixes de contexte qui contiennent
des mots déclencheurs (« photo »…) n'appartenant PAS au client. Bug terrain :
« hello » sur un Statut arrivait comme [Répond à la photo: "#K053"] Hello.
"""
from app.services.dialogue.sanitizer import strip_context_prefix, normalize


def test_strip_bridge_reply_prefix():
    assert strip_context_prefix('[Répond à la photo: "#K053"] Hello') == "Hello"


def test_strip_voice_prefix_with_colon():
    assert strip_context_prefix("[🎤 Vocal transcrit (fr)]: je veux la photo") == "je veux la photo"


def test_strip_multiple_prefixes():
    assert strip_context_prefix('[Répond à: "ok"] [🎤 Vocal transcrit (fr)]: oui') == "oui"


def test_bracket_only_system_message_becomes_empty():
    # Message 100 % système (ex. instruction de recherche visuelle) → ""
    assert strip_context_prefix("[📸 Le client a envoyé une photo. Présente-lui les produits.]") == ""


def test_plain_message_untouched():
    assert strip_context_prefix("je veux la photo") == "je veux la photo"


def test_none_and_empty_are_safe():
    assert strip_context_prefix(None) == ""
    assert strip_context_prefix("") == ""


def test_normalize_mobile_apostrophes():
    # iOS/Android génèrent ’ au lieu de '
    assert normalize("d’autres couleurs") == "d'autres couleurs"


def test_normalize_collapses_whitespace_and_strips():
    assert normalize("  je   veux\n ça  ") == "je veux ça"


def test_normalize_strips_context_prefix_first():
    assert normalize('[Répond à la photo: "#K053"]   Hello  ') == "Hello"
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python -m pytest tests/test_dialogue_sanitizer.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.dialogue'`

- [ ] **Step 3: Créer le paquet et le module**

`kalga-api/app/services/dialogue/__init__.py` :

```python
"""
Moteur de dialogue v2 — pipeline à 5 étages (spec 2026-06-11).

Phase 1 : étages ① (sanitizer) et ② (intents, understanding).
Le code décide QUOI faire ; le LLM décidera COMMENT le dire (phases suivantes).
"""
```

`kalga-api/app/services/dialogue/sanitizer.py` :

```python
"""
Étage ① — Sas d'entrée.

Les messages bruts portent des préfixes de contexte ajoutés par le bridge ou le
système, qui contiennent des mots déclencheurs n'appartenant pas au client :
    [Répond à la photo: "#K053"] Hello        (réponse à un Statut/image)
    [Répond à: "..."] texte                    (réponse à un message)
    [🎤 Vocal transcrit (fr)]: texte           (note vocale transcrite)
    [📸 Recherche visuelle — ...]              (instruction système, sans texte client)

Aucun détecteur en aval ne doit jamais voir ces blocs : seuls les mots
réellement tapés (ou dits) par le client comptent.
"""
import re

_CONTEXT_PREFIX_RE = re.compile(r"^\s*\[[^\]]*\]:?\s*")
_MOBILE_APOSTROPHES = {"’": "'", "‘": "'"}
_WHITESPACE_RE = re.compile(r"\s+")


def strip_context_prefix(message) -> str:
    """Retire tous les blocs [contexte] en tête de message.

    Un message 100 % système (uniquement des blocs) devient "" — les règles ne
    s'appliquent alors pas et l'appelant garde la main (LLM ou flux normal).
    """
    msg = message or ""
    while True:
        stripped = _CONTEXT_PREFIX_RE.sub("", msg, count=1)
        if stripped == msg:
            return msg
        msg = stripped


def normalize(message) -> str:
    """Texte client canonique : sans préfixes, apostrophes droites, espaces propres."""
    msg = strip_context_prefix(message)
    for bad, good in _MOBILE_APOSTROPHES.items():
        msg = msg.replace(bad, good)
    return _WHITESPACE_RE.sub(" ", msg).strip()
```

- [ ] **Step 4: Vérifier le succès**

Run: `python -m pytest tests/test_dialogue_sanitizer.py -q`
Expected: PASS (9 tests)

- [ ] **Step 5: Dé-dupliquer deal_guard**

Dans `kalga-api/app/services/ai/deal_guard.py` :
1. Supprimer le bloc local `_CONTEXT_PREFIX_RE = re.compile(...)` **et** la fonction `strip_context_prefix(...)` (commentaire d'en-tête du bloc inclus).
2. Supprimer `import re` s'il ne sert plus à rien d'autre dans le fichier (vérifier avec une recherche `re.` avant de retirer).
3. Ajouter l'import :

```python
from ..dialogue.sanitizer import strip_context_prefix
```

(`deal_guard` est dans `app/services/ai/`, le sanitizer dans `app/services/dialogue/` → remonter d'un cran avec `..`.)

- [ ] **Step 6: Vérifier que rien n'est cassé**

Run: `python -m pytest tests/ -q`
Expected: PASS — les 61 tests existants + les 9 nouveaux = 70. (Les tests `test_deal_guard.py` importent `strip_context_prefix` depuis `deal_guard`, qui le ré-exporte désormais via l'import — ils restent verts.)

- [ ] **Step 7: Commit**

```bash
git add kalga-api/app/services/dialogue/ kalga-api/app/services/ai/deal_guard.py kalga-api/tests/test_dialogue_sanitizer.py
git commit -m "feat(dialogue): étage ① sanitizer — foyer canonique du nettoyage d'entrée"
```

---

## Task 2: Catalogue d'intentions (intents.py)

**Files:**
- Create: `kalga-api/app/services/dialogue/intents.py`
- Test: `kalga-api/tests/test_dialogue_intents.py`

- [ ] **Step 1: Écrire les tests qui échouent**

```python
"""Tests du catalogue d'intentions fermé."""
from app.services.dialogue.intents import Intent, IntentType, PRIORITY


def test_catalog_is_closed_and_complete():
    expected = {
        "GREETING", "ASK_INFO", "ASK_PHOTO", "ASK_OTHER_PHOTOS", "ASK_VARIANTS",
        "ASK_OTHER_PRODUCTS", "ASK_LOCATION", "ASK_PAYMENT", "ASK_DELIVERY_INFO",
        "PRICE_OFFER", "ACCEPT_PRICE", "CHOOSE_DELIVERY", "CHOOSE_PICKUP",
        "GIVE_ADDRESS", "GOODBYE", "FRUSTRATION", "CORRECTION", "HUMAN_REQUEST",
        "UNCLEAR",
    }
    assert {t.name for t in IntentType} == expected


def test_every_intent_type_has_a_priority():
    assert set(PRIORITY) == set(IntentType)


def test_requests_rank_before_transactions():
    # Les demandes client passent avant la mécanique de vente (spec §7)
    assert PRIORITY[IntentType.ASK_PHOTO] < PRIORITY[IntentType.PRICE_OFFER]
    assert PRIORITY[IntentType.ASK_VARIANTS] < PRIORITY[IntentType.ACCEPT_PRICE]
    assert PRIORITY[IntentType.CORRECTION] < PRIORITY[IntentType.ASK_PHOTO]


def test_intent_is_frozen_and_hashable():
    a = Intent(IntentType.PRICE_OFFER, amount=9000)
    b = Intent(IntentType.PRICE_OFFER, amount=9000)
    assert a == b
    assert len({a, b}) == 1


def test_intent_optional_fields_default_none():
    i = Intent(IntentType.GREETING)
    assert i.amount is None and i.text is None
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python -m pytest tests/test_dialogue_intents.py -q`
Expected: FAIL — `ModuleNotFoundError` (intents inexistant)

- [ ] **Step 3: Implémenter**

`kalga-api/app/services/dialogue/intents.py` :

```python
"""
Étage ② — Catalogue d'intentions FERMÉ (spec §5).

Un message client porte une ou PLUSIEURS intentions. L'extraction les retourne
toutes ; la politique (P2) les transforme en plan d'actions. Le LLM classifieur
(P3) ne pourra émettre QUE des types de ce catalogue — jamais d'action.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IntentType(str, Enum):
    # — signaux à traiter en premier —
    CORRECTION = "correction"            # « c'est pas ce que j'ai demandé »
    FRUSTRATION = "frustration"          # énervement, insulte
    HUMAN_REQUEST = "human_request"      # « passe-moi le vendeur »
    # — demandes du client (toujours honorées avant la vente) —
    ASK_PHOTO = "ask_photo"              # photo du produit actuel
    ASK_OTHER_PHOTOS = "ask_other_photos"  # « d'autres photos »
    ASK_VARIANTS = "ask_variants"        # autres couleurs/tailles/modèles
    ASK_OTHER_PRODUCTS = "ask_other_products"  # catalogue du marchand
    ASK_INFO = "ask_info"                # description, qualité, dispo, prix…
    ASK_LOCATION = "ask_location"        # adresse / localisation
    ASK_PAYMENT = "ask_payment"          # moyens de paiement
    ASK_DELIVERY_INFO = "ask_delivery_info"  # frais/délais de livraison (question)
    # — logistique exprimée par le client —
    GIVE_ADDRESS = "give_address"        # adresse de livraison fournie
    CHOOSE_DELIVERY = "choose_delivery"  # « je veux être livré »
    CHOOSE_PICKUP = "choose_pickup"      # « je viens chercher »
    # — transactionnel —
    PRICE_OFFER = "price_offer"          # offre chiffrée OU objection prix (amount=None)
    ACCEPT_PRICE = "accept_price"        # acceptation (amount=None si non chiffrée)
    # — social / flux —
    GREETING = "greeting"
    GOODBYE = "goodbye"
    UNCLEAR = "unclear"                  # rien de reconnu → classifieur LLM (P3)


# Ordre canonique de tri des intentions extraites (la politique re-priorise
# ensuite pour le plan d'actions ; ici on garantit un ordre stable et testable).
PRIORITY = {t: i for i, t in enumerate(IntentType)}


@dataclass(frozen=True)
class Intent:
    type: IntentType
    amount: Optional[float] = None   # PRICE_OFFER / ACCEPT_PRICE
    text: Optional[str] = None       # GIVE_ADDRESS (adresse), ASK_INFO (sujet)
```

- [ ] **Step 4: Vérifier le succès**

Run: `python -m pytest tests/test_dialogue_intents.py -q`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add kalga-api/app/services/dialogue/intents.py kalga-api/tests/test_dialogue_intents.py
git commit -m "feat(dialogue): catalogue d'intentions fermé + priorité canonique"
```

---

## Task 3: Règles prix & acceptation (understanding.py — partie 1)

**Files:**
- Create: `kalga-api/app/services/dialogue/understanding.py`
- Test: `kalga-api/tests/test_dialogue_understanding.py`

Sémantique décidée (spec §5/§6) :
- Offre chiffrée (« je veux ça à 9000 », « 15k », « je donne 10 000 ») → `PRICE_OFFER(amount)`.
- Objection prix sans chiffre (« trop cher », « fais un effort », « baisse un peu ») → `PRICE_OFFER(amount=None)`.
- Acceptation explicite chiffrée (« ok pour 18 000 ») → `ACCEPT_PRICE(18000)` — et PAS de `PRICE_OFFER` en plus.
- Acceptation forte non chiffrée (« ok je prends », « banco », « deal », « vendu », « marché conclu ») → `ACCEPT_PRICE(None)` (la politique appliquera le verrou de CONCLUSION en P2).
- Affirmation faible (« ok », « oui », « d'accord », « ça marche ») → `ACCEPT_PRICE(None)` **seulement si** `last_bot_message` contient un prix ; sinon rien (l'étage composition rendra `UNCLEAR` si rien d'autre n'est détecté).

- [ ] **Step 1: Écrire les tests qui échouent**

```python
"""Tests des règles d'extraction — prix et acceptation."""
from app.services.dialogue.intents import Intent, IntentType
from app.services.dialogue.understanding import (
    extract_price_amount,
    detect_price_intents,
)


# --- extract_price_amount : extraction robuste d'un montant FCFA ---

def test_amount_k_suffix():
    assert extract_price_amount("je veux ça à 18K") == 18000.0


def test_amount_spaced_thousands():
    assert extract_price_amount("je te donne 15 000") == 15000.0


def test_amount_plain():
    assert extract_price_amount("9000 et on est bons") == 9000.0


def test_amount_with_currency_word():
    assert extract_price_amount("10000 fcfa dernier prix") == 10000.0


def test_no_amount_returns_none():
    assert extract_price_amount("c'est trop cher") is None


def test_product_code_is_not_an_amount():
    # #K053 ne doit jamais devenir une offre de prix
    assert extract_price_amount("je parle du K053") is None


# --- detect_price_intents : (message_normalisé, last_bot_message) -> list[Intent] ---

def test_offer_with_amount():
    intents = detect_price_intents("je veux ça à 9000", None)
    assert Intent(IntentType.PRICE_OFFER, amount=9000.0) in intents


def test_price_objection_without_amount():
    intents = detect_price_intents("c'est trop cher, fais un effort", None)
    assert Intent(IntentType.PRICE_OFFER) in intents


def test_explicit_priced_acceptance_is_accept_not_offer():
    intents = detect_price_intents("ok pour 18 000", None)
    assert Intent(IntentType.ACCEPT_PRICE, amount=18000.0) in intents
    assert all(i.type != IntentType.PRICE_OFFER for i in intents)


def test_strong_acceptance_without_amount():
    for msg in ("ok je prends", "banco", "deal", "vendu", "marché conclu"):
        intents = detect_price_intents(msg, None)
        assert Intent(IntentType.ACCEPT_PRICE) in intents, msg


def test_weak_ok_with_priced_bot_context_is_acceptance():
    intents = detect_price_intents("ok", "Je peux faire 9 500 F, ça marche ?")
    assert Intent(IntentType.ACCEPT_PRICE) in intents


def test_weak_ok_without_priced_context_is_nothing():
    # « Oui » à « ça t'intéresse ? » → AUCUNE intention transactionnelle
    assert detect_price_intents("oui", "Ça t'intéresse ?") == []


def test_je_prends_soin_is_not_acceptance():
    assert detect_price_intents("je prends soin de mes affaires", None) == []


def test_question_price_is_still_an_offer():
    # « tu peux faire 9000 ? » est bien une offre à négocier
    intents = detect_price_intents("tu peux faire 9000 ?", None)
    assert Intent(IntentType.PRICE_OFFER, amount=9000.0) in intents
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python -m pytest tests/test_dialogue_understanding.py -q`
Expected: FAIL — `ModuleNotFoundError` (understanding inexistant)

- [ ] **Step 3: Implémenter**

`kalga-api/app/services/dialogue/understanding.py` :

```python
"""
Étage ② — Extraction multi-intentions par règles déterministes.

Chaque fonction `detect_*` est pure : (texte normalisé, contexte minimal) →
liste d'Intent. La composition (extract_intents, Task 6) assainit le message,
appelle toutes les règles, déduplique et trie.

Hérite des détecteurs historiques (app/services/ai/detectors.py) en les
consolidant : multi-intentions, montants extraits, contexte du dernier message
bot. L'ancien fichier reste vivant jusqu'à la bascule P5 (spec §12).
"""
import re
from typing import List, Optional

from .intents import Intent, IntentType
from .sanitizer import normalize

# ─────────────────────────────────────────────────────────────
# Montants FCFA
# ─────────────────────────────────────────────────────────────

# « 18k » / « 18 K » — précédé de début/espace pour exclure les codes (#K053)
_K_AMOUNT_RE = re.compile(r"(?:^|[\s@à])(\d{1,4})\s*k\b", re.IGNORECASE)
# « 15 000 » (milliers espacés)
_SPACED_AMOUNT_RE = re.compile(r"\b(\d{1,3}(?:\s\d{3})+)\b")
# « 9000 », « 10000 fcfa » — 4 chiffres et plus, pas précédé d'une lettre (codes)
_PLAIN_AMOUNT_RE = re.compile(r"(?<![a-zA-Z\d])(\d{4,7})(?!\d)")


def extract_price_amount(text: str) -> Optional[float]:
    """Extrait un montant FCFA d'un texte client. None si aucun montant fiable."""
    low = text.lower()
    m = _K_AMOUNT_RE.search(low)
    if m:
        return float(m.group(1)) * 1000
    m = _SPACED_AMOUNT_RE.search(low)
    if m:
        return float(m.group(1).replace(" ", ""))
    m = _PLAIN_AMOUNT_RE.search(low)
    if m:
        return float(m.group(1))
    return None


# ─────────────────────────────────────────────────────────────
# Prix & acceptation
# ─────────────────────────────────────────────────────────────

_PRICE_OBJECTIONS = (
    "trop cher", "c'est cher", "fais un effort", "baisse", "diminue", "réduis",
    "reduis", "pas les moyens", "au-dessus de mon budget", "dernier prix",
    "moins cher", "tu peux faire mieux",
)

# Acceptations fortes : concluent même sans chiffre (le verrou P2 tranchera)
_STRONG_ACCEPT_EXACT = (
    "deal", "banco", "vendu", "adjugé", "adjuge", "je valide", "j'accepte",
    "marché conclu", "marche conclu", "affaire conclue", "on fait comme ça",
    "on fait comme ca",
)
_STRONG_ACCEPT_STARTS = (
    "ok je prends", "ok je prend", "d'accord pour", "ok pour", "ça marche pour",
    "ca marche pour", "c'est bon pour", "ça me va pour", "ca me va pour",
)
_JE_PRENDS_EXCLUSIONS = (
    "soin", "note", "en compte", "le temps", "mon temps", "connaissance",
    "rendez-vous", "en charge", "en main", "en photo",
)

# Affirmations faibles : acceptation SEULEMENT si le bot venait de chiffrer
_WEAK_AFFIRMATIONS = (
    "ok", "oui", "ouais", "oki", "dac", "d'accord", "daccord", "ça marche",
    "ca marche", "c'est bon", "cest bon", "ça me va", "ca me va", "parfait",
)


def _is_strong_acceptance(low: str) -> bool:
    if low in _STRONG_ACCEPT_EXACT:
        return True
    if any(low.startswith(s) for s in _STRONG_ACCEPT_STARTS):
        return True
    if "je prends" in low or "je prend" in low:
        if not any(excl in low for excl in _JE_PRENDS_EXCLUSIONS):
            return True
    return False


def detect_price_intents(text: str, last_bot_message: Optional[str]) -> List[Intent]:
    """Intentions transactionnelles d'un message (déjà normalisé)."""
    low = text.lower().strip()
    if not low:
        return []
    amount = extract_price_amount(low)

    if _is_strong_acceptance(low):
        return [Intent(IntentType.ACCEPT_PRICE, amount=amount)]

    if low in _WEAK_AFFIRMATIONS:
        bot_priced = bool(last_bot_message) and extract_price_amount(last_bot_message) is not None
        return [Intent(IntentType.ACCEPT_PRICE)] if bot_priced else []

    if amount is not None:
        return [Intent(IntentType.PRICE_OFFER, amount=amount)]

    if any(obj in low for obj in _PRICE_OBJECTIONS):
        return [Intent(IntentType.PRICE_OFFER)]

    return []
```

- [ ] **Step 4: Vérifier le succès**

Run: `python -m pytest tests/test_dialogue_understanding.py -q`
Expected: PASS (14 tests)

- [ ] **Step 5: Commit**

```bash
git add kalga-api/app/services/dialogue/understanding.py kalga-api/tests/test_dialogue_understanding.py
git commit -m "feat(dialogue): règles prix & acceptation (offres, objections, verrou faible/fort)"
```

---

## Task 4: Règles demandes visuelles & produits (understanding.py — partie 2)

**Files:**
- Modify: `kalga-api/app/services/dialogue/understanding.py` (ajout en fin de fichier)
- Test: `kalga-api/tests/test_dialogue_understanding.py` (ajout)

- [ ] **Step 1: Ajouter les tests qui échouent**

```python
# === Demandes visuelles & produits ===
from app.services.dialogue.understanding import detect_visual_intents


def test_photo_request():
    for msg in ("envoie la photo", "tu as une image ?", "montre-moi",
                "je peux voir le produit ?", "à quoi ça ressemble"):
        intents = detect_visual_intents(msg.lower())
        assert Intent(IntentType.ASK_PHOTO) in intents, msg


def test_other_photos_request():
    for msg in ("je veux d'autres photos", "je peux avoir d'autre photo",
                "envoie moi plus de photos"):
        intents = detect_visual_intents(msg.lower())
        assert Intent(IntentType.ASK_OTHER_PHOTOS) in intents, msg


def test_variants_request():
    for msg in ("tu as d'autres couleurs ?", "il existe en rouge ?",
                "autre taille ?", "autre modèle ?"):
        intents = detect_visual_intents(msg.lower())
        assert Intent(IntentType.ASK_VARIANTS) in intents, msg


def test_other_products_request():
    for msg in ("tu vends quoi d'autre ?", "vous avez autre chose ?",
                "montre ton catalogue"):
        intents = detect_visual_intents(msg.lower())
        assert Intent(IntentType.ASK_OTHER_PRODUCTS) in intents, msg


def test_location_send_is_not_a_photo():
    assert detect_visual_intents("envoie moi la localisation") == []


def test_variant_beats_photo_for_same_phrase():
    # « d'autres couleurs » ne doit pas déclencher ASK_PHOTO en plus
    intents = detect_visual_intents("tu as d'autres couleurs ?")
    assert Intent(IntentType.ASK_PHOTO) not in intents
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python -m pytest tests/test_dialogue_understanding.py -q`
Expected: FAIL — `ImportError: cannot import name 'detect_visual_intents'`

- [ ] **Step 3: Implémenter (ajout en fin d'understanding.py)**

```python
# ─────────────────────────────────────────────────────────────
# Demandes visuelles & produits
# ─────────────────────────────────────────────────────────────

_PHOTO_KEYWORDS = (
    "photo", "image", "montre moi", "montre-moi", "montre",
    "a quoi ca ressemble", "à quoi ça ressemble", "je peux voir",
    "fais voir", "fait voir",
)
_VISUAL_TOKENS = ("photo", "image", "montre", "voir", "ressemble", "aperçu", "apercu")

_OTHER_PHOTOS_PATTERNS = (
    "d'autres photos", "d'autre photo", "autres photos", "autre photo",
    "d'autres images", "d'autre image", "plus de photo", "plus de photos",
    "plus d'image", "plus d'images", "encore des photos", "encore une photo",
)

_VARIANT_PATTERNS = (
    "autre couleur", "autres couleurs", "d'autres couleurs", "quelle couleur",
    "quelles couleurs", "coloris", "en noir", "en blanc", "en rouge", "en bleu",
    "en vert", "en jaune", "en rose", "en gris", "en marron",
    "autre taille", "autres tailles", "taille différente", "plus grand",
    "plus petit", "en xl", "en xxl", "du xl", "du l ", "du m ", "du s ",
    "autre modèle", "autres modèles", "d'autres modèles", "autre model",
    "variante", "variantes", "autre version",
    "il existe en", "tu as la même en", "tu as la meme en",
)

_OTHER_PRODUCTS_PATTERNS = (
    "quoi d'autre", "tu as quoi", "vous avez quoi", "tu vends quoi",
    "vous vendez quoi", "autre chose", "autres articles", "autres produits",
    "d'autres articles", "d'autres produits", "catalogue", "tous tes produits",
    "tous vos produits", "liste de produits",
)


def detect_visual_intents(text: str) -> List[Intent]:
    """ASK_PHOTO / ASK_OTHER_PHOTOS / ASK_VARIANTS / ASK_OTHER_PRODUCTS.

    Ordre de spécificité : catalogue > variantes > autres-photos > photo.
    Un même message peut porter variantes ET photo explicite distinctes, mais
    une formulation unique ne produit qu'une seule de ces intentions.
    """
    low = text.lower()
    intents: List[Intent] = []

    if any(p in low for p in _OTHER_PRODUCTS_PATTERNS):
        intents.append(Intent(IntentType.ASK_OTHER_PRODUCTS))
    elif any(p in low for p in _VARIANT_PATTERNS):
        intents.append(Intent(IntentType.ASK_VARIANTS))
    elif any(p in low for p in _OTHER_PHOTOS_PATTERNS):
        intents.append(Intent(IntentType.ASK_OTHER_PHOTOS))
    elif any(k in low for k in _PHOTO_KEYWORDS) and any(t in low for t in _VISUAL_TOKENS):
        # Double condition : mot-clé de demande + token visuel — exclut
        # « envoie moi la localisation » (aucun token visuel).
        intents.append(Intent(IntentType.ASK_PHOTO))

    return intents
```

- [ ] **Step 4: Vérifier le succès**

Run: `python -m pytest tests/test_dialogue_understanding.py -q`
Expected: PASS (20 tests)

- [ ] **Step 5: Commit**

```bash
git add kalga-api/app/services/dialogue/understanding.py kalga-api/tests/test_dialogue_understanding.py
git commit -m "feat(dialogue): règles demandes visuelles (photo/autres-photos/variantes/catalogue)"
```

---

## Task 5: Règles logistique, social & signaux (understanding.py — partie 3)

**Files:**
- Modify: `kalga-api/app/services/dialogue/understanding.py` (ajout en fin de fichier)
- Test: `kalga-api/tests/test_dialogue_understanding.py` (ajout)

- [ ] **Step 1: Ajouter les tests qui échouent**

```python
# === Logistique, social & signaux ===
from app.services.dialogue.understanding import detect_logistics_intents, detect_signal_intents


def test_location_request():
    for msg in ("où vous êtes ?", "l'adresse ?", "envoie la localisation",
                "c'est où le magasin ?"):
        assert Intent(IntentType.ASK_LOCATION) in detect_logistics_intents(msg.lower(), None), msg


def test_payment_request():
    for msg in ("comment payer ?", "orange money ?", "wave ?", "numéro de paiement"):
        assert Intent(IntentType.ASK_PAYMENT) in detect_logistics_intents(msg.lower(), None), msg


def test_delivery_info_question_vs_choice():
    # Question sur la livraison ≠ choix de la livraison
    q = detect_logistics_intents("c'est combien la livraison ?", None)
    assert Intent(IntentType.ASK_DELIVERY_INFO) in q
    assert Intent(IntentType.CHOOSE_DELIVERY) not in q

    c = detect_logistics_intents("je veux me faire livrer", None)
    assert Intent(IntentType.CHOOSE_DELIVERY) in c


def test_pickup_choice():
    for msg in ("je viens chercher", "je passe au magasin", "je vais venir sur place"):
        assert Intent(IntentType.CHOOSE_PICKUP) in detect_logistics_intents(msg.lower(), None), msg


def test_give_address_when_bot_asked():
    intents = detect_logistics_intents(
        "cocody angré 7e tranche, près de la pharmacie",
        "Parfait ! Donne-moi ton adresse de livraison ?",
    )
    assert any(i.type == IntentType.GIVE_ADDRESS and "cocody" in i.text for i in intents)


def test_no_give_address_without_bot_asking():
    intents = detect_logistics_intents("cocody angré 7e tranche", None)
    assert all(i.type != IntentType.GIVE_ADDRESS for i in intents)


def test_greeting():
    for msg in ("hello", "salut", "bonjour", "bonsoir", "cc"):
        assert Intent(IntentType.GREETING) in detect_signal_intents(msg.lower()), msg


def test_goodbye_restrictive():
    assert Intent(IntentType.GOODBYE) in detect_signal_intents("bye")
    assert Intent(IntentType.GOODBYE) in detect_signal_intents("merci bye")
    assert Intent(IntentType.GOODBYE) in detect_signal_intents("laisse tomber")
    # Jamais GOODBYE si signe d'intérêt
    assert detect_signal_intents("bye, mais c'est combien ?") == []


def test_frustration():
    assert Intent(IntentType.FRUSTRATION) in detect_signal_intents("tu te moques de moi, voleur !")


def test_correction():
    assert Intent(IntentType.CORRECTION) in detect_signal_intents("c'est pas ce que j'ai demandé")


def test_human_request():
    for msg in ("je veux parler à quelqu'un", "passez-moi un responsable",
                "je veux parler au vendeur directement"):
        assert Intent(IntentType.HUMAN_REQUEST) in detect_signal_intents(msg.lower()), msg
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python -m pytest tests/test_dialogue_understanding.py -q`
Expected: FAIL — `ImportError: cannot import name 'detect_logistics_intents'`

- [ ] **Step 3: Implémenter (ajout en fin d'understanding.py)**

```python
# ─────────────────────────────────────────────────────────────
# Logistique
# ─────────────────────────────────────────────────────────────

_LOCATION_KEYWORDS = (
    "adresse", "localisation", "position", "emplacement", "où vous êtes",
    "ou vous etes", "où c'est", "ou c'est", "c'est où", "c'est ou",
    "où est le magasin", "ou est le magasin", "comment trouver",
    "situé", "situe", "le magasin", "la boutique",
)
_PAYMENT_KEYWORDS = (
    "comment payer", "je paye comment", "paiement", "orange money", "wave",
    "momo", "moov money", "mtn money", "numéro de paiement", "numero de paiement",
)
_DELIVERY_QUESTION_PATTERNS = (
    "combien la livraison", "c'est combien la livraison", "prix de la livraison",
    "frais de livraison", "vous livrez", "tu livres", "la livraison coûte",
    "la livraison coute", "livraison ?",
)
_DELIVERY_CHOICE_PATTERNS = (
    "je veux la livraison", "je veux me faire livrer", "je veux me faire livré",
    "livre-moi", "livrez-moi", "livre moi", "livrer chez moi", "en livraison",
    "ok livraison", "oui livraison", "je préfère la livraison",
    "je prefere la livraison", "pour la livraison",
)
_PICKUP_PATTERNS = (
    "je viens chercher", "je viens le chercher", "je passe chercher",
    "je passe au magasin", "je viens au magasin", "venir au magasin",
    "je passe à la boutique", "je vais venir", "sur place", "en personne",
    "moi-même", "moi même", "je viens",
)


def detect_logistics_intents(text: str, last_bot_message: Optional[str]) -> List[Intent]:
    """ASK_LOCATION / ASK_PAYMENT / ASK_DELIVERY_INFO / CHOOSE_* / GIVE_ADDRESS."""
    low = text.lower()
    intents: List[Intent] = []

    if any(k in low for k in _LOCATION_KEYWORDS):
        intents.append(Intent(IntentType.ASK_LOCATION))
    if any(k in low for k in _PAYMENT_KEYWORDS):
        intents.append(Intent(IntentType.ASK_PAYMENT))

    if any(p in low for p in _DELIVERY_QUESTION_PATTERNS):
        intents.append(Intent(IntentType.ASK_DELIVERY_INFO))
    elif any(p in low for p in _DELIVERY_CHOICE_PATTERNS):
        intents.append(Intent(IntentType.CHOOSE_DELIVERY))

    if any(p in low for p in _PICKUP_PATTERNS):
        intents.append(Intent(IntentType.CHOOSE_PICKUP))

    # GIVE_ADDRESS : uniquement si le bot vient de demander l'adresse, que le
    # message ressemble à un lieu (assez long, lettres) et ne porte rien d'autre.
    bot_asked_address = bool(last_bot_message) and "adresse" in last_bot_message.lower()
    if bot_asked_address and not intents and len(low) >= 8 and any(c.isalpha() for c in low):
        intents.append(Intent(IntentType.GIVE_ADDRESS, text=text.strip()))

    return intents


# ─────────────────────────────────────────────────────────────
# Social & signaux
# ─────────────────────────────────────────────────────────────

_GREETINGS = ("hello", "salut", "bonjour", "bonsoir", "coucou", "cc", "yo", "hey", "hi")

_INTEREST_KEYWORDS = (
    "prix", "combien", "livr", "acheter", "prend", "veux", "veut", "dispo",
    "couleur", "taille", "photo", "image", "intéress", "interess", "comment",
    "où", "ou est", "quand", "payer", "adresse",
)
_GOODBYE_EXACT = (
    "bye", "ciao", "au revoir", "non merci", "pas intéressé", "pas interesse",
    "merci bye", "na laisse", "laisse tomber", "laisse béton", "laisse beton",
    "j'ai trouvé ailleurs", "jai trouve ailleurs", "je reviendrai",
    "je reviens plus tard", "pas pour l'instant", "pas maintenant merci",
    "à une prochaine", "a une prochaine", "en tout cas merci",
)
_GOODBYE_STARTS = ("laisse tomber", "j'ai trouvé ailleurs", "jai trouve ailleurs")

_FRUSTRATION_PATTERNS = (
    "voleur", "arnaque", "arnaqueur", "escroc", "menteur", "tu te moques",
    "moque de moi", "tu te fous de moi", "fous de ma gueule", "n'importe quoi",
    "nimporte quoi", "tu rigoles", "tu plaisantes", "tu abuses", "tu exagères",
    "tu exageres", "c'est du vol", "pas sérieux", "pas serieux",
)
_CORRECTION_PATTERNS = (
    "c'est pas ce que j'ai demandé", "pas ce que j'ai demandé",
    "pas ce que je t'ai demandé", "tu n'as pas répondu", "tu nas pas repondu",
    "tu réponds pas à", "tu reponds pas a", "ma question c'était",
    "ma question cetait", "j'avais demandé", "javais demande",
    "ce n'est pas ma question", "c'est pas ma question", "tu comprends pas",
    "tu comprend pas", "je t'ai pas demandé ça", "j'ai pas demandé ça",
    "jai pas demande ca", "c'est pas ça que je voulais",
    "c'est pas ce que je voulais", "non ce que je",
)
_HUMAN_PATTERNS = (
    "parler à quelqu'un", "parler a quelqu'un", "un responsable",
    "passe-moi", "passez-moi", "un humain", "une vraie personne",
    "parler au vendeur", "le vendeur directement", "litige", "réclamation",
    "reclamation",
)


def detect_signal_intents(text: str) -> List[Intent]:
    """GREETING / GOODBYE / FRUSTRATION / CORRECTION / HUMAN_REQUEST."""
    low = text.lower().strip()
    intents: List[Intent] = []

    if any(p in low for p in _CORRECTION_PATTERNS):
        intents.append(Intent(IntentType.CORRECTION))
    if any(p in low for p in _FRUSTRATION_PATTERNS):
        intents.append(Intent(IntentType.FRUSTRATION))
    if any(p in low for p in _HUMAN_PATTERNS):
        intents.append(Intent(IntentType.HUMAN_REQUEST))

    first_word = low.split(" ")[0].rstrip("!,.") if low else ""
    if first_word in _GREETINGS:
        intents.append(Intent(IntentType.GREETING))

    # GOODBYE — très restrictif (ne jamais perdre un client intéressé) :
    # aucun mot d'intérêt, aucun chiffre, et formulation de fin connue.
    has_interest = any(k in low for k in _INTEREST_KEYWORDS)
    has_digit = any(c.isdigit() for c in low)
    if not has_interest and not has_digit:
        if low in _GOODBYE_EXACT or any(low.startswith(s) for s in _GOODBYE_STARTS):
            intents.append(Intent(IntentType.GOODBYE))

    return intents
```

- [ ] **Step 4: Vérifier le succès**

Run: `python -m pytest tests/test_dialogue_understanding.py -q`
Expected: PASS (31 tests)

- [ ] **Step 5: Commit**

```bash
git add kalga-api/app/services/dialogue/understanding.py kalga-api/tests/test_dialogue_understanding.py
git commit -m "feat(dialogue): règles logistique (lieu/paiement/livraison/retrait/adresse) et signaux"
```

---

## Task 6: Composition extract_intents (understanding.py — partie 4)

**Files:**
- Modify: `kalga-api/app/services/dialogue/understanding.py` (ajout en fin de fichier)
- Test: `kalga-api/tests/test_dialogue_understanding.py` (ajout)

- [ ] **Step 1: Ajouter les tests qui échouent**

```python
# === Composition : extract_intents ===
from app.services.dialogue.understanding import extract_intents


def test_multi_intent_offer_plus_photo():
    """LE bug terrain n°1 : contre-offre + photo dans le même message."""
    intents = extract_intents("Je veux ça à 9000 et envoie moi plus de photo")
    types = [i.type for i in intents]
    assert IntentType.ASK_OTHER_PHOTOS in types or IntentType.ASK_PHOTO in types
    assert Intent(IntentType.PRICE_OFFER, amount=9000.0) in intents
    # La demande visuelle passe AVANT le transactionnel (ordre canonique)
    visual_idx = min(types.index(t) for t in types
                     if t in (IntentType.ASK_PHOTO, IntentType.ASK_OTHER_PHOTOS))
    assert visual_idx < types.index(IntentType.PRICE_OFFER)


def test_bridge_prefix_sanitized():
    """LE bug terrain n°3 : « hello » sur un Statut → GREETING, pas photo."""
    intents = extract_intents('[Répond à la photo: "#K053"] Hello')
    assert intents == [Intent(IntentType.GREETING)]


def test_system_only_message_returns_empty():
    assert extract_intents("[📸 Le client a envoyé une photo. Présente les produits.]") == []


def test_unrecognized_returns_unclear():
    intents = extract_intents("euh hum alors voilà quoi")
    assert intents == [Intent(IntentType.UNCLEAR)]


def test_dedup_same_intent():
    intents = extract_intents("photo photo envoie la photo stp")
    assert intents.count(Intent(IntentType.ASK_PHOTO)) == 1


def test_question_without_match_is_ask_info():
    intents = extract_intents("c'est du cuir véritable ?")
    assert any(i.type == IntentType.ASK_INFO for i in intents)


def test_price_question_is_ask_info_with_subject():
    intents = extract_intents("c'est combien ?")
    assert Intent(IntentType.ASK_INFO, text="prix") in intents


def test_sorted_by_canonical_priority():
    intents = extract_intents("c'est pas ce que j'ai demandé, je veux la photo")
    assert intents[0].type == IntentType.CORRECTION
```

- [ ] **Step 2: Vérifier l'échec**

Run: `python -m pytest tests/test_dialogue_understanding.py -q`
Expected: FAIL — `ImportError: cannot import name 'extract_intents'`

- [ ] **Step 3: Implémenter (ajout en fin d'understanding.py)**

```python
# ─────────────────────────────────────────────────────────────
# Composition
# ─────────────────────────────────────────────────────────────

_PRICE_QUESTION_PATTERNS = ("c'est combien", "combien ça coûte", "combien ca coute",
                            "quel est le prix", "le prix ?", "ça coûte combien",
                            "ca coute combien", "combien")


def extract_intents(message: str, last_bot_message: Optional[str] = None) -> List[Intent]:
    """Point d'entrée de l'étage ② : message brut → intentions ordonnées.

    - Assainit (préfixes bridge/système) et normalise.
    - Message 100 % système → [] (aucune intention client).
    - Applique toutes les familles de règles, déduplique, trie par PRIORITY.
    - Rien de reconnu → [ASK_INFO] si question, sinon [UNCLEAR]
      (le classifieur LLM prendra le relais en P3).
    """
    from .intents import PRIORITY  # import local pour éviter tout cycle futur

    text = normalize(message)
    if not text:
        return []

    low = text.lower()
    collected: List[Intent] = []
    collected += detect_signal_intents(low)
    collected += detect_visual_intents(low)
    collected += detect_logistics_intents(low, last_bot_message)
    collected += detect_price_intents(low, last_bot_message)

    # Question prix explicite → ASK_INFO(prix) — sauf si déjà transactionnel
    # ou si le « combien » porte sur la livraison (ASK_DELIVERY_INFO).
    if (any(p in low for p in _PRICE_QUESTION_PATTERNS)
            and not any(i.type in (IntentType.PRICE_OFFER, IntentType.ACCEPT_PRICE,
                                   IntentType.ASK_DELIVERY_INFO)
                        for i in collected)):
        collected.append(Intent(IntentType.ASK_INFO, text="prix"))

    # Question générique non couverte → ASK_INFO
    substantive = [i for i in collected if i.type != IntentType.GREETING]
    if not substantive and "?" in text:
        collected.append(Intent(IntentType.ASK_INFO))

    # Dédup en préservant la première occurrence
    seen = set()
    unique: List[Intent] = []
    for intent in collected:
        if intent not in seen:
            seen.add(intent)
            unique.append(intent)

    if not unique:
        return [Intent(IntentType.UNCLEAR)]

    unique.sort(key=lambda i: PRIORITY[i.type])
    return unique
```

- [ ] **Step 4: Vérifier le succès**

Run: `python -m pytest tests/test_dialogue_understanding.py -q`
Expected: PASS (39 tests)

- [ ] **Step 5: Commit**

```bash
git add kalga-api/app/services/dialogue/understanding.py kalga-api/tests/test_dialogue_understanding.py
git commit -m "feat(dialogue): extract_intents — composition multi-intentions ordonnée"
```

---

## Task 7: Corpus doré + vérification finale

**Files:**
- Create: `kalga-api/tests/test_dialogue_corpus.py`
- Modify: `docs/superpowers/specs/2026-06-11-refonte-moteur-dialogue-design.md` (statut P1)

- [ ] **Step 1: Écrire le corpus**

```python
"""Corpus doré de l'étage compréhension.

Chaque entrée : (message brut tel que reçu du bridge, last_bot_message,
types d'intentions attendus dans l'ordre). Les 3 bugs terrain y sont gravés
en régression permanente. Toute évolution des règles DOIT garder ce corpus vert.
"""
import pytest

from app.services.dialogue.intents import IntentType as T
from app.services.dialogue.understanding import extract_intents


CORPUS = [
    # ── Les 3 bugs terrain (captures WhatsApp) ──
    ('[Répond à la photo: "#K053"] Hello', None, [T.GREETING]),
    ("Je veux ça à 9000 et envoie moi plus de photo", None, [T.ASK_OTHER_PHOTOS, T.PRICE_OFFER]),
    ("Je veux d'autres photos", None, [T.ASK_OTHER_PHOTOS]),
    ("Je peux avoir d'autre photo", None, [T.ASK_OTHER_PHOTOS]),
    ("Je veux me faire livré", None, [T.CHOOSE_DELIVERY]),
    # ── Accueil / social ──
    ("hello", None, [T.GREETING]),
    ("Bonjour, c'est disponible ?", None, [T.ASK_INFO, T.GREETING]),  # tri canonique : demandes avant social
    ("merci bye", None, [T.GOODBYE]),
    # ── Renseignement ──
    ("c'est combien ?", None, [T.ASK_INFO]),
    ("envoie la photo", None, [T.ASK_PHOTO]),
    ("tu as d'autres couleurs ?", None, [T.ASK_VARIANTS]),
    ("tu vends quoi d'autre ?", None, [T.ASK_OTHER_PRODUCTS]),
    ("c'est du cuir véritable ?", None, [T.ASK_INFO]),
    ("où vous êtes ?", None, [T.ASK_LOCATION]),
    ("comment payer ? wave ?", None, [T.ASK_PAYMENT]),
    ("c'est combien la livraison ?", None, [T.ASK_DELIVERY_INFO]),
    # ── Négociation ──
    ("je te donne 15 000", None, [T.PRICE_OFFER]),
    ("18K et on est bons", None, [T.PRICE_OFFER]),
    ("c'est trop cher, fais un effort", None, [T.PRICE_OFFER]),
    ("tu peux faire 9000 ?", None, [T.PRICE_OFFER]),
    # ── Conclusion ──
    ("ok pour 18 000", None, [T.ACCEPT_PRICE]),
    ("ok je prends", None, [T.ACCEPT_PRICE]),
    ("banco", None, [T.ACCEPT_PRICE]),
    ("ok", "Je peux faire 9 500 F, ça marche ?", [T.ACCEPT_PRICE]),
    ("oui", "Ça t'intéresse ?", [T.UNCLEAR]),  # le « oui » d'intérêt ne conclut RIEN
    # ── Logistique ──
    ("je viens chercher", None, [T.CHOOSE_PICKUP]),
    ("cocody angré 7e tranche, près de la pharmacie",
     "Parfait ! Donne-moi ton adresse de livraison ?", [T.GIVE_ADDRESS]),
    # ── Signaux ──
    ("tu te moques de moi, voleur !", None, [T.FRUSTRATION]),
    ("c'est pas ce que j'ai demandé", None, [T.CORRECTION]),
    ("je veux parler au vendeur directement", None, [T.HUMAN_REQUEST]),
    # ── Vocal transcrit ──
    ("[🎤 Vocal transcrit (fr)]: je veux la photo", None, [T.ASK_PHOTO]),
    # ── Système pur ──
    ("[📸 Le client a envoyé une photo. Présente les produits.]", None, []),
]


@pytest.mark.parametrize("message,last_bot,expected", CORPUS,
                         ids=[c[0][:40] for c in CORPUS])
def test_corpus(message, last_bot, expected):
    intents = extract_intents(message, last_bot_message=last_bot)
    assert [i.type for i in intents] == expected
```

- [ ] **Step 2: Lancer le corpus**

Run: `python -m pytest tests/test_dialogue_corpus.py -v`
Expected: PASS (32 cas). Si un cas échoue : corriger la **règle** dans `understanding.py` (jamais affaiblir le corpus) — chaque entrée est un comportement validé par le marchand.

- [ ] **Step 3: Suite complète + import app**

Run: `python -m pytest tests/ -q && python -c "from app.main import app; print('OK')"`
Expected: tous verts (≈ 145 tests : 61 existants + 9 sanitizer + 5 intents + 39 understanding + 32 corpus), `OK`.

- [ ] **Step 4: Marquer P1 dans la spec**

Dans `docs/superpowers/specs/2026-06-11-refonte-moteur-dialogue-design.md`, §12, ligne P1 : ajouter ` — ✅ fait` en fin de cellule « Livrable vérifiable ».

- [ ] **Step 5: Commit + push**

```bash
git add kalga-api/tests/test_dialogue_corpus.py
git add -f docs/superpowers/specs/2026-06-11-refonte-moteur-dialogue-design.md
git commit -m "test(dialogue): corpus doré de compréhension (3 bugs terrain en régression permanente)"
git push
```

---

## Dette tracée / notes pour P2

- `understanding.py` duplique temporairement des règles de `detectors.py` — voulu (étrangleur), résorbé en P5.
- `GIVE_ADDRESS` repose sur une heuristique simple (le bot a demandé l'adresse) ; la politique P2 la fiabilisera avec l'état LOGISTIQUE_LIVRAISON.
- Le verrou complet de CONCLUSION (« aucune autre intention en attente ») est l'affaire de la **politique** (P2) — l'extraction se contente de fournir toutes les intentions.
- `ASK_INFO` reste grossier (sujet « prix » seulement) ; le classifieur LLM (P3) affinera les sujets.
