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
from .sanitizer import normalize, get_replied_photo_label

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


def extract_all_amounts(text: str) -> List[float]:
    """TOUS les montants d'un texte, dans l'ordre d'apparition.

    Indispensable pour les messages du bot qui citent plusieurs prix
    (« Au lieu de 20 000 F, je te fais 19 000 F ») : prendre le premier
    revenait à conclure au prix affiché (bug terrain n°9).
    """
    low = (text or "").lower()
    found = []
    for m in _K_AMOUNT_RE.finditer(low):
        found.append((m.start(1), float(m.group(1)) * 1000))
    for m in _SPACED_AMOUNT_RE.finditer(low):
        found.append((m.start(1), float(m.group(1).replace(" ", ""))))
    for m in _PLAIN_AMOUNT_RE.finditer(low):
        found.append((m.start(1), float(m.group(1))))
    found.sort(key=lambda x: x[0])
    return [v for _, v in found]


# ─────────────────────────────────────────────────────────────
# Prix & acceptation
# ─────────────────────────────────────────────────────────────

_PRICE_OBJECTIONS = (
    "trop cher", "c'est cher", "fais un effort", "baisse", "diminue", "réduis",
    "reduis", "pas les moyens", "au-dessus de mon budget", "dernier prix",
    "moins cher", "tu peux faire mieux", "revoir le prix", "revois le prix",
    "prix élevé", "prix est élevé", "prix eleve", "négocier", "negocier",
    "on discute le prix",
    # vocabulaire courant du marchandage ivoirien (bug terrain n°10)
    "rabais", "remise", "réduction", "reduction", "un geste", "petit geste",
    "fais un prix", "fais-moi un prix", "fais moi un prix", "bon prix pour moi",
    "casse le prix", "arrange-moi", "arrange moi",
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


def detect_price_intents(text: str, last_bot_message: Optional[str],
                         has_standing_offer: bool = False) -> List[Intent]:
    """Intentions transactionnelles d'un message (déjà normalisé).

    has_standing_offer : un prix est déjà sur la table (contre-offre persistée) —
    un « ok » faible vaut alors acceptation même si le dernier texte du bot
    ne contient pas de montant.
    """
    low = text.lower().strip()
    if not low:
        return []
    amount = extract_price_amount(low)

    if _is_strong_acceptance(low):
        return [Intent(IntentType.ACCEPT_PRICE, amount=amount)]

    if low in _WEAK_AFFIRMATIONS:
        bot_priced = bool(last_bot_message) and extract_price_amount(last_bot_message) is not None
        return [Intent(IntentType.ACCEPT_PRICE)] if (bot_priced or has_standing_offer) else []

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

# « moins cher » accolé à une demande d'AUTRES choses = alternatives abordables
_CHEAPER_WORDS = ("moins cher", "moins chère", "moins chers", "moins chères",
                  "pas cher", "plus abordable", "abordable", "économique", "economique")

# Forme polie-négative : « tu n'aurais pas d'autres … ? » / « vous n'auriez pas d'autres … »
_POLITE_OTHERS_RE = re.compile(r"n'(?:aurais|auriez|avez|as)\s+pas\s+d'autres?")


def detect_visual_intents(text: str) -> List[Intent]:
    """ASK_PHOTO / ASK_OTHER_PHOTOS / ASK_VARIANTS / ASK_OTHER_PRODUCTS.

    Ordre de spécificité : catalogue > variantes > autres-photos > photo.
    Un même message peut porter variantes ET photo explicite distinctes, mais
    une formulation unique ne produit qu'une seule de ces intentions.
    """
    low = text.lower()
    intents: List[Intent] = []

    wants_cheaper = any(w in low for w in _CHEAPER_WORDS)

    if (any(p in low for p in _OTHER_PRODUCTS_PATTERNS)
            or ("d'autre" in low and wants_cheaper)):
        # « d'autres fleurs moins cher » = alternatives abordables (bug n°7),
        # même si le nom du produit n'est pas dans nos listes génériques.
        intents.append(Intent(IntentType.ASK_OTHER_PRODUCTS,
                              text="moins cher" if wants_cheaper else None))
    elif any(p in low for p in _VARIANT_PATTERNS):
        intents.append(Intent(IntentType.ASK_VARIANTS))
    elif any(p in low for p in _OTHER_PHOTOS_PATTERNS):
        intents.append(Intent(IntentType.ASK_OTHER_PHOTOS))
    elif _POLITE_OTHERS_RE.search(low):
        # « tu n'aurais pas d'autres … ? » sans précision → catalogue
        intents.append(Intent(IntentType.ASK_OTHER_PRODUCTS,
                              text="moins cher" if wants_cheaper else None))
    elif any(k in low for k in _PHOTO_KEYWORDS) and any(t in low for t in _VISUAL_TOKENS):
        # Double condition : mot-clé de demande + token visuel — exclut
        # « envoie moi la localisation » (aucun token visuel).
        intents.append(Intent(IntentType.ASK_PHOTO))

    return intents


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
    # formes passives (bug terrain : « je veux être livré » non reconnu)
    "être livré", "etre livre", "être livrée", "etre livree",
    "qu'on me livre", "vous me livrez", "tu me livres",
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
    # message ressemble à un lieu (assez de LETTRES — un numéro de téléphone
    # « oui 0544210112 » n'est pas une adresse) et ne porte rien d'autre.
    bot_asked_address = bool(last_bot_message) and "adresse" in last_bot_message.lower()
    letter_count = sum(1 for c in low if c.isalpha())
    if bot_asked_address and not intents and len(low) >= 8 and letter_count >= 6:
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


# ─────────────────────────────────────────────────────────────
# Composition
# ─────────────────────────────────────────────────────────────

_PRICE_QUESTION_PATTERNS = ("c'est combien", "combien ça coûte", "combien ca coute",
                            "quel est le prix", "le prix ?", "ça coûte combien",
                            "ca coute combien", "combien")

# Questions qualité/authenticité — souvent posées SANS « ? » (« c'est l'original »).
# Bug terrain : le FSM historique les prenait pour une acceptation de vente.
_QUALITY_PATTERNS = ("original", "authentique", "c'est du vrai", "vrai ou faux",
                     "bonne qualité", "bonne qualite", "la qualité", "la qualite",
                     "garantie", "garanti", "contrefaçon", "contrefacon")


def extract_intents(message: str, last_bot_message: Optional[str] = None,
                    has_standing_offer: bool = False) -> List[Intent]:
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
    collected += detect_price_intents(low, last_bot_message, has_standing_offer)

    # Alternatives moins chères ≠ négociation du produit en cours : quand le
    # client demande d'AUTRES produits abordables, on ne baisse PAS le prix
    # actuel (bug n°7 : le bot saignait sa marge au lieu de montrer la gamme).
    if any(i.type == IntentType.ASK_OTHER_PRODUCTS and i.text == "moins cher"
           for i in collected):
        collected = [i for i in collected
                     if not (i.type == IntentType.PRICE_OFFER and i.amount is None)]

    # Choix d'une variante : le client répond à la photo « Modèle X » (légende
    # posée par le bot). Le préfixe bridge est ici un SIGNAL : il désigne SA
    # variante — sauf s'il demande explicitement d'autres modèles/photos.
    reply_label = get_replied_photo_label(message)
    if reply_label:
        variant_match = re.match(r"Modèle\s+(.+)", reply_label, re.IGNORECASE)
        wants_others = any(i.type in (IntentType.ASK_VARIANTS,
                                      IntentType.ASK_OTHER_PHOTOS,
                                      IntentType.ASK_OTHER_PRODUCTS)
                           for i in collected)
        if variant_match and not wants_others:
            collected.append(Intent(IntentType.CHOOSE_VARIANT,
                                    text=variant_match.group(1).strip()))

    # Question prix explicite → ASK_INFO(prix) — sauf si déjà transactionnel
    # ou si le « combien » porte sur la livraison (ASK_DELIVERY_INFO).
    if (any(p in low for p in _PRICE_QUESTION_PATTERNS)
            and not any(i.type in (IntentType.PRICE_OFFER, IntentType.ACCEPT_PRICE,
                                   IntentType.ASK_DELIVERY_INFO)
                        for i in collected)):
        collected.append(Intent(IntentType.ASK_INFO, text="prix"))

    # Question qualité/authenticité (avec ou sans « ? ») → ASK_INFO(qualité)
    if (any(p in low for p in _QUALITY_PATTERNS)
            and not any(i.type == IntentType.ASK_INFO for i in collected)):
        collected.append(Intent(IntentType.ASK_INFO, text="qualité"))

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
