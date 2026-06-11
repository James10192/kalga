"""
Étage ② — Extraction multi-intentions par règles déterministes.

Chaque fonction `detect_*` est pure : (texte normalisé, contexte minimal) →
liste d'Intent. La composition (extract_intents) assainit le message,
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
