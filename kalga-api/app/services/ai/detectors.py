"""
Détecteurs d'intentions et extracteurs de données
Fonctions pures pour analyser les messages clients
"""
import re
from typing import Optional, List, Dict


def extract_product_code(message: str) -> Optional[str]:
    """Extrait le code produit (#K001) d'un message"""
    match = re.search(r'#K\d{3}', message.upper())
    return match.group(0) if match else None


def extract_price_offer(message: str) -> Optional[float]:
    """
    Extrait une offre de prix d'un message.
    Supporte les formats: 15k, 15K, 15 000, 15000, 15000 fcfa
    """
    msg = message.lower()

    # Pattern pour "15k" ou "15K" (milliers)
    k_match = re.search(r'(\d+)\s*k\b', msg)
    if k_match:
        return float(k_match.group(1)) * 1000

    # Pattern pour nombres avec espaces: "15 000" ou "15000"
    space_match = re.search(r'(\d{1,3}(?:\s\d{3})+)', msg)
    if space_match:
        value = space_match.group(1).replace(' ', '')
        return float(value)

    # Pattern pour nombres simples: "15000", "13000 fcfa"
    simple_match = re.search(r'(\d{4,})\s*(?:fcfa|f|francs)?', msg)
    if simple_match:
        return float(simple_match.group(1))

    return None


def detect_delivery_request(message: str) -> bool:
    """
    Détecte si le client veut la livraison.
    IMPORTANT: Exclut les contextes négatifs (plaintes, questions)
    """
    msg = message.lower()

    # Contextes négatifs - si présents, ce n'est PAS une demande de livraison
    negative_contexts = [
        'pas de livraison', 'sans livraison', 'livraison?', 'livraison ?',
        'c\'est combien la livraison', 'combien la livraison', 'combien livraison',
        'prix de la livraison', 'frais de livraison', 'coût de livraison',
        'cout de livraison', 'prix livraison', 'coute la livraison',
        'voleur', 'arnaque', 'arnaquer', 'cher', 'trop cher', 'exagér',
        'abusé', 'abuse', 'fou', 'folle', 'dingue', 'n\'importe quoi',
        'nimporte quoi', 'sérieux', 'serieux', 'tu rigoles', 'tu plaisantes',
        'tu te moques', 'moque de moi', 'pas sérieux'
    ]
    if any(ctx in msg for ctx in negative_contexts):
        return False

    # Phrases interrogatives sur la livraison (pas une demande)
    if '?' in msg and 'livr' in msg:
        return False

    # Phrases affirmatives de demande de livraison
    delivery_requests = [
        'je veux la livraison', 'livraison svp', 'livraison stp',
        'livre-moi', 'livrez-moi', 'livrer chez moi', 'livraison chez moi',
        'je préfère la livraison', 'je prefere la livraison',
        'oui livraison', 'ok livraison', 'avec livraison',
        'fais-moi la livraison', 'fais moi la livraison',
        'pour la livraison', 'en livraison'
    ]
    if any(req in msg for req in delivery_requests):
        return True

    # Ancienne logique mais uniquement si pas de contexte négatif
    delivery_keywords = ['livre-moi', 'livrez-moi', 'livrer chez']
    return any(kw in msg for kw in delivery_keywords)


def detect_pickup_request(message: str) -> bool:
    """Détecte si le client veut venir chercher au magasin"""
    msg = message.lower()
    pickup_keywords = [
        'viens chercher', 'je viens', 'passe chercher', 'récupérer',
        'magasin', 'boutique', 'sur place', 'en personne', 'moi-même', 'moi même'
    ]
    return any(kw in msg for kw in pickup_keywords)


def detect_end_conversation(message: str) -> bool:
    """
    Détecte si le client veut VRAIMENT terminer la conversation.
    ATTENTION: Fonction très restrictive pour éviter de perdre des clients intéressés.
    """
    msg = message.lower().strip()

    # Ne JAMAIS considérer comme fin si le message contient des indices d'intérêt
    interest_keywords = [
        'prix', 'combien', 'livr', 'acheter', 'prend', 'veux', 'veut',
        'dispo', 'couleur', 'taille', 'photo', 'image', 'ok', 'oui',
        'd\'accord', 'deal', 'marché', 'ça marche', 'c\'est bon',
        'intéress', 'comment', 'où', 'quand', 'payer', 'cash', 'momo',
        'magasin', 'boutique', 'adresse', 'place'
    ]
    if any(kw in msg for kw in interest_keywords):
        return False

    # Ne pas considérer comme fin si le message contient un nombre (possible offre)
    if any(char.isdigit() for char in msg):
        return False

    # Messages EXACTS de fin SEULEMENT (très restrictif)
    exact_end = [
        'bye', 'ciao', 'au revoir', 'non merci', 'pas intéressé', 'pas interesse'
    ]
    return msg in exact_end


def detect_agreement(message: str) -> bool:
    """Détecte si le client accepte le prix"""
    msg = message.lower().strip()

    # Phrases exactes d'accord (très fiables)
    exact_agreements = [
        'deal', 'vendu', 'adjugé', 'je valide', 'j\'accepte', 'jaccepte',
        'marché conclu', 'affaire conclue', 'on fait comme ça'
    ]
    if msg in exact_agreements:
        return True

    # Phrases qui doivent être au début ou seules
    start_agreements = [
        'ok pour', 'd\'accord pour', 'daccord pour', 'ok je prends',
        'je prends le', 'je prends pour', 'ça marche pour', 'ca marche pour',
        'c\'est bon pour', 'ça me va pour', 'ca me va pour'
    ]
    if any(msg.startswith(kw) for kw in start_agreements):
        return True

    # Vérifier "je prends" mais pas "je prends soin", "je prends note", etc.
    if 'je prends' in msg:
        exclusions = ['soin', 'note', 'en compte', 'le temps', 'mon temps', 'connaissance']
        if not any(excl in msg for excl in exclusions):
            return True

    # Messages courts d'accord (moins de 25 caractères)
    if len(msg) < 25:
        short_agreements = [
            'ça marche', 'ca marche', 'c\'est bon', 'ça me va',
            'ca me va', 'je suis d\'accord', 'marché'
        ]
        if any(kw in msg for kw in short_agreements):
            return True

    return False


def detect_variant_request(message: str) -> bool:
    """
    Détecte si le client demande d'autres couleurs/variantes/modèles.
    IMPORTANT: Doit capturer toutes les formulations possibles, y compris:
    - Fautes d'orthographe courantes
    - Formulations génériques ("d'autre", "t'as d'autre")
    - Questions implicites
    """
    msg = message.lower()

    # === PATTERNS EXACTS ===
    variant_keywords = [
        # Couleurs
        'autre couleur', 'autres couleurs', 'd\'autres couleurs',
        'autre teinte', 'autres teintes', 'dautres couleurs',
        'quelle couleur', 'quelles couleurs', 'les couleurs',
        'coloris', 'en noir', 'en blanc', 'en rouge', 'en bleu',
        'en vert', 'en jaune', 'en rose', 'en gris', 'en marron',

        # Tailles
        'autre taille', 'autres tailles', 'taille différente',
        'en xl', 'en l', 'en m', 'en s', 'en xxl', 'en xs',
        'plus grand', 'plus petit', 'taille au dessus', 'taille en dessous',

        # Modèles/variantes
        'autre modèle', 'autres modèles', 'd\'autres modèles', 'dautres modèles',
        'autre model', 'autres models',  # sans accent
        'variante', 'variantes', 'vatiante', 'vatiantes',  # fautes courantes
        'variente', 'varientes', 'variant',
        'version', 'versions', 'autre version',

        # Photos d'autres
        'photo d\'une autre', 'image d\'une autre', 'voir une autre',
        'photo d\'autre', 'image d\'autre', 'photos d\'autres',
        'autre photo', 'autres photos', 'd\'autres photos',
        'autre image', 'autres images', 'd\'autres images',
    ]

    if any(kw in msg for kw in variant_keywords):
        return True

    # === PATTERNS GÉNÉRIQUES "D'AUTRE" ===
    # Capture: "t'as d'autre?", "y'a d'autre", "envoie d'autre", "montre d'autre"
    generic_other_patterns = [
        'd\'autre',      # "t'as d'autre", "y'a d'autre"
        'dautre',        # sans apostrophe
        't\'as d\'autre', 'tas dautre',
        'y\'a d\'autre', 'ya dautre', 'il y a d\'autre',
        'as tu d\'autre', 'as-tu d\'autre', 'avez vous d\'autre',
        'envoie d\'autre', 'envoi d\'autre', 'envoie moi d\'autre',
        'montre d\'autre', 'montre moi d\'autre',
        'vois d\'autre', 'voir d\'autre',
        'je veux d\'autre', 'je veux voir d\'autre',
        'tu as d\'autre', 'vous avez d\'autre',
    ]

    if any(pattern in msg for pattern in generic_other_patterns):
        return True

    # === QUESTIONS SUR LA DISPONIBILITÉ D'AUTRES ===
    question_patterns = [
        'c\'est tout', 'c tout', 'y\'a que ça', 'ya que ca',
        'juste celui', 'juste celle', 'que celui-là', 'que celle-là',
        'pas d\'autre', 'rien d\'autre',  # Souvent une question implicite
    ]

    # Ces patterns sont des questions si le message contient "?"
    if '?' in msg and any(pattern in msg for pattern in question_patterns):
        return True

    # === REGEX POUR PATTERNS FLEXIBLES ===
    import re

    # Normaliser les apostrophes pour simplifier les regex
    msg_normalized = msg.replace("'", "'").replace("'", "'")

    # "autre + mot" où mot peut être photo, modèle, couleur, etc.
    if re.search(r"\bautre[s]?\s+(photo|image|modele|model|couleur|teinte|taille|version|truc|chose)", msg_normalized):
        return True

    # "d'autre" avec ou sans mot après
    if re.search(r"d'autre[s]?\s*(photo|image|modele|model|couleur|variante|version)?", msg_normalized):
        return True

    # "envoie/montre + moi + d'autre/autre"
    if re.search(r"(envoie|envoi|montre|vois|voir)\s*(moi|nous)?\s*(d'autre|autre)", msg_normalized):
        return True

    return False


def detect_photo_request(message: str) -> bool:
    """Détecte si le client demande une photo/image du produit"""
    msg = message.lower()

    # Exclusions : le client dit qu'il ne veut PAS une image/photo
    negation_patterns = [
        'pas demande', 'pas une image', 'pas une photo', 'pas de photo',
        "pas d'image", "pas d'photo", 'pas besoin de photo', "pas besoin d'image",
    ]
    if any(neg in msg for neg in negation_patterns):
        return False

    photo_keywords = [
        'photo', 'image',
        'envoie moi', 'envoie-moi', 'envoi moi', 'envoi-moi',
        'montre moi', 'montre-moi',
        'a quoi ca ressemble', 'a quoi ça ressemble',
        'je peux voir',
    ]
    # "voir le/la/l'" seulement si PAS précédé de "a" (éviter "avoir les")
    if ' voir le ' in f' {msg} ' or ' voir la ' in f' {msg} ' or "voir l'" in msg:
        if 'avoir le' not in msg and 'avoir la' not in msg and 'avoir les' not in msg:
            return True
    return any(kw in msg for kw in photo_keywords)


def detect_location_request(message: str) -> bool:
    """Détecte si le client demande l'adresse/localisation"""
    msg = message.lower()
    location_keywords = [
        'magasin', 'boutique', 'adresse', 'où', 'ou c\'est',
        'situé', 'situer', 'situe',
        'localisation', 'position', 'lieu', 'emplacement', 'trouver',
        'renvois', 'renvoie', 'renvoyer',
    ]
    return any(kw in msg for kw in location_keywords)


def is_product_related_message(message: str, product_name: str) -> bool:
    """
    Vérifie si le message est en rapport avec le produit ou la vente.
    IMPORTANT: Fonction très permissive pour ne pas rater de ventes.
    """
    # TOUJOURS retourner True pour les messages courts/moyens
    if len(message.strip()) < 100:
        return True

    msg = message.lower()
    product_lower = product_name.lower()

    # Mots-clés liés à une transaction/vente
    sale_keywords = [
        'prix', 'combien', 'coute', 'coûte', 'cher', 'moins', 'plus',
        'livr', 'magasin', 'acheter', 'achète', 'prend', 'veux', 'veut',
        'dispo', 'disponible', 'stock', 'couleur', 'taille', 'modèle',
        'ok', 'oui', 'non', 'deal', 'marché', 'd\'accord', 'réfléchi',
        'intéress', 'produit', 'article', 'phone', 'téléphone',
        '#k', 'fcfa', 'franc', 'f', 'k', '000',
        'comment', 'avoir', 'ça', 'ca', 'celui', 'celle', 'ceux',
        'payer', 'paiement', 'cash', 'espèce', 'mobile', 'momo', 'wave', 'orange',
        'quand', 'où', 'adresse', 'localisation', 'situé',
        'neuf', 'occasion', 'état', 'garantie', 'original',
        'photo', 'image', 'voir', 'envoie', 'montre',
        'salut', 'bonjour', 'bonsoir', 'hello', 'hey', 'coucou',
        'merci', 'thanks', 'svp', 'stp', 'please',
        'bien', 'super', 'cool', 'nice', 'parfait', 'excellent',
        'c\'est', 'je', 'tu', 'il', 'elle', 'on', 'nous'
    ]

    # Vérifier si le message contient le nom du produit
    if product_lower in msg:
        return True

    # Vérifier si le message contient des mots-clés
    if any(kw in msg for kw in sale_keywords):
        return True

    # Vérifier si le message contient un nombre (potentiellement un prix)
    if any(char.isdigit() for char in msg):
        return True

    # Par défaut, considérer comme pertinent
    return True


def detect_other_products_request(message: str) -> bool:
    """
    Détecte si le client demande à voir d'autres PRODUITS du marchand
    (pas des variantes du même produit, mais de nouveaux articles).
    """
    msg = message.lower()

    explicit = [
        'quoi d\'autre', 'quoi d autre', 'tu as quoi', 'vous avez quoi',
        'tu vends quoi', 'vous vendez quoi', 'c\'est quoi d\'autre',
        'tu as autre chose', 'vous avez autre chose',
        'autres articles', 'autres produits', 'autres choses',
        'd\'autres articles', 'd\'autres produits',
        'votre catalogue', 'ton catalogue', 'ta boutique vend',
        'qu\'est ce que tu as', 'qu\'est ce que vous avez',
        'qu est ce que tu as', 'qu est ce que vous avez',
        'tu as quoi d\'autre', 'vous avez quoi d\'autre',
        'tu as autre chose à vendre', 'tu vends quoi d\'autre',
        'liste de produits', 'tous vos produits', 'tous tes produits',
    ]
    return any(p in msg for p in explicit)


def count_low_offers(conversation_history: List[Dict], min_price: float) -> int:
    """Compte le nombre d'offres en dessous du prix minimum"""
    count = 0
    for msg in conversation_history:
        if msg.get('is_from_client'):
            offer = extract_price_offer(msg.get('content', ''))
            if offer and offer < min_price:
                count += 1
    return count


def detect_frustration(message: str) -> bool:
    """
    Détecte si le client est frustré, énervé ou utilise des insultes.
    Retourne True si le message contient des signes de frustration.
    """
    msg = message.lower()

    # Insultes et mots vulgaires
    insults = [
        'voleur', 'arnaqueur', 'arnaque', 'escroc', 'menteur',
        'idiot', 'imbécile', 'imbecile', 'con', 'connard', 'connasse',
        'fou', 'folle', 'dingue', 'malade', 'taré', 'tare',
        'nul', 'nulle', 'merde', 'bordel', 'putain',
        'tu te fous de moi', 'tu te moques', 'moque de moi',
        'va te faire', 'laisse tomber', 'laisse-moi tranquille'
    ]

    # Expressions de frustration
    frustration_phrases = [
        'tu rigoles', 'tu plaisantes', 'tu délires', 'tu delires',
        'c\'est une blague', 'sérieusement', 'serieusement',
        'n\'importe quoi', 'nimporte quoi', 'ça va pas',
        'tu abuses', 'tu exagères', 'tu exageres', 'abusé', 'abuse',
        'trop cher', 'beaucoup trop', 'vraiment trop',
        'pas possible', 'impossible', 'c\'est du vol',
        'tu te fous de ma gueule', 'fous de ma gueule',
        'tu me prends pour', 'prends pour un',
        'pas sérieux', 'pas serieux', 'pas croyable'
    ]

    # Vérifier les insultes
    if any(insult in msg for insult in insults):
        return True

    # Vérifier les expressions de frustration
    if any(phrase in msg for phrase in frustration_phrases):
        return True

    # Majuscules excessives (signe de colère)
    uppercase_count = sum(1 for c in message if c.isupper())
    if len(message) > 10 and uppercase_count > len(message) * 0.5:
        return True

    # Ponctuation excessive
    if message.count('!') >= 3 or message.count('?') >= 3:
        return True

    return False


def detect_objection(message: str) -> Optional[str]:
    """
    Détecte le type d'objection du client pour mieux y répondre.
    Retourne le type d'objection ou None.
    """
    msg = message.lower()

    # Objection sur le prix
    price_objections = [
        'trop cher', 'cher', 'coute cher', 'coûte cher',
        'pas les moyens', 'budget', 'au-dessus de mon budget',
        'ailleurs moins cher', 'moins cher ailleurs',
        'concurrent', 'autre vendeur', 'vu moins cher'
    ]
    if any(obj in msg for obj in price_objections):
        return "price"

    # Objection sur la qualité
    quality_objections = [
        'qualité', 'qualite', 'original', 'faux', 'contrefaçon',
        'copie', 'authentique', 'garanti', 'garantie'
    ]
    if any(obj in msg for obj in quality_objections):
        return "quality"

    # Objection sur la confiance
    trust_objections = [
        'confiance', 'arnaque', 'peur', 'méfiant', 'mefiant',
        'sûr', 'sur', 'certain', 'fiable', 'sécurisé', 'securise'
    ]
    if any(obj in msg for obj in trust_objections):
        return "trust"

    # Objection sur le timing
    timing_objections = [
        'réfléchir', 'reflechir', 'plus tard', 'pas maintenant',
        'besoin de temps', 'demain', 'la semaine prochaine',
        'rappeler', 'reviens', 'recontacter'
    ]
    if any(obj in msg for obj in timing_objections):
        return "timing"

    return None
