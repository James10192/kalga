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
