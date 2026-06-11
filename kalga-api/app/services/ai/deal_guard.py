"""
Garde-fou déterministe pour accept_deal.

Empêche la clôture prématurée d'une vente quand le message du client contient
une intention concurrente non satisfaite (demande de photo / d'autres variantes)
ou une contre-offre à la baisse. Fonction pure et testable — ne dépend ni du
LLM ni de la base de données.

Raison d'être : le LLM (DeepSeek) décide parfois d'`accept_deal` alors que le
client demande encore une photo ou propose un autre prix. On ne se fie pas au
seul jugement probabiliste du modèle : ce garde-fou code intercepte et rétrograde
l'action vers le bon tool, pour laisser le client « aller au bout ».
"""
from typing import Optional, Dict
import logging

from .detectors import (
    detect_photo_request,
    detect_variant_request,
    extract_price_offer,
)

logger = logging.getLogger("kalga.ai.deal_guard")

# Tokens visuels explicites : on ne route vers send_photo que si l'un d'eux est
# présent, pour éviter qu'un simple « envoie moi … » (ex. la localisation) soit
# pris à tort pour une demande de photo.
_VISUAL_TOKENS = ("photo", "image", "montre", "voir", "ressemble", "aperçu", "apercu")


def is_explicit_photo_request(client_message: str) -> bool:
    """
    True si le client demande EXPLICITEMENT une photo du produit actuel.

    Sert à honorer la demande de façon déterministe, sans dépendre du choix du
    LLM (qui, une fois en phase de clôture, fixe la livraison et ignore la photo).
    Exclut les demandes d'AUTRES variantes (gérées ailleurs) et les « envoie moi … »
    sans token visuel (ex. « envoie moi la localisation »).
    """
    msg = client_message or ""
    if detect_variant_request(msg):
        return False
    return detect_photo_request(msg) and any(tok in msg.lower() for tok in _VISUAL_TOKENS)


def resolve_accept_deal(
    client_message: str,
    current_offer: Optional[float],
    min_price: float,
    listed_price: float,
) -> Optional[Dict]:
    """
    Décide si un `accept_deal` proposé par le LLM doit être rétrogradé.

    Retourne :
      - None                            → clôture autorisée (rien ne s'y oppose)
      - {"name": "send_variants", ...}  → le client veut d'autres modèles d'abord
      - {"name": "send_photo", ...}     → le client veut une photo d'abord
      - {"name": "counter_offer", ...}  → le client fait une contre-offre à la baisse

    Priorité : une demande non satisfaite passe avant la négociation prix
    (variante > photo > contre-offre), afin de ne jamais conclure « dans le dos »
    du client.
    """
    msg = client_message or ""
    msg_lower = msg.lower()

    # 1. Demande d'autres variantes/modèles → montrer les variantes, ne pas conclure.
    if detect_variant_request(msg):
        logger.info("accept_deal rétrogradé → send_variants (demande d'autres modèles)")
        return {
            "name": "send_variants",
            "args": {"message": "Bien sûr ! Voici les autres modèles dispo 👇"},
        }

    # 2. Demande de photo du produit → envoyer la photo, ne pas conclure.
    #    Double condition : detect_photo_request ET un token visuel explicite.
    if detect_photo_request(msg) and any(tok in msg_lower for tok in _VISUAL_TOKENS):
        logger.info("accept_deal rétrogradé → send_photo (demande de photo)")
        return {
            "name": "send_photo",
            "args": {"message": "Bien sûr, je te montre ça !"},
        }

    # 3. Contre-offre à la baisse → négocier, ne pas conclure au prix précédent.
    offered = extract_price_offer(msg)
    reference = current_offer or listed_price
    if offered is not None and reference is not None and offered < reference:
        if offered < min_price:
            target = float(min_price)
            min_f = f"{int(min_price):,}".replace(",", " ")
            low_f = f"{int(offered):,}".replace(",", " ")
            message = f"{low_f} F c'est un peu bas ! Je peux faire {min_f} F, c'est mon dernier prix."
        else:
            target = float(offered)
            off_f = f"{int(offered):,}".replace(",", " ")
            message = f"Ok, je peux te faire {off_f} F ! Ça marche pour toi ?"
        logger.info(f"accept_deal rétrogradé → counter_offer (contre-offre {offered} < {reference})")
        return {
            "name": "counter_offer",
            "args": {"price": target, "message": message},
        }

    # 4. Rien ne s'oppose à la clôture.
    return None
