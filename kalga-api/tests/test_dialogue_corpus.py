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
    ('[Répond à la photo: "Modèle Fleur"] je veux celle la mais il faut revoir le prix',
     None, [T.CHOOSE_VARIANT, T.PRICE_OFFER]),  # bug n°5 : choix variante + négo, pas le catalogue
    # ── Accueil / social ──
    ("hello", None, [T.GREETING]),
    ("Bonjour, c'est disponible ?", None, [T.ASK_INFO, T.GREETING]),  # tri canonique : demandes avant social
    ("merci bye", None, [T.GOODBYE]),
    # ── Renseignement ──
    ("c'est combien ?", None, [T.ASK_INFO]),
    ("envoie la photo", None, [T.ASK_PHOTO]),
    ("tu as d'autres couleurs ?", None, [T.ASK_VARIANTS]),
    ("tu vends quoi d'autre ?", None, [T.ASK_OTHER_PRODUCTS]),
    ("Tu n'aurais pas d'autres fleurs moins cher !?", None, [T.ASK_OTHER_PRODUCTS]),  # bug n°7 : alternatives, PAS un rabais
    ("c'est du cuir véritable ?", None, [T.ASK_INFO]),
    ("c'est l'original", None, [T.ASK_INFO]),  # bug terrain n°4 : question qualité sans «?», JAMAIS une vente
    ('[Répond à la photo: "Venez faire votre commande #K023"] c\'est l\'original',
     None, [T.ASK_INFO]),
    ("où vous êtes ?", None, [T.ASK_LOCATION]),
    ("comment payer ? wave ?", None, [T.ASK_PAYMENT]),
    ("c'est combien la livraison ?", None, [T.ASK_DELIVERY_INFO]),
    # ── Négociation ──
    ("je te donne 15 000", None, [T.PRICE_OFFER]),
    ("18K et on est bons", None, [T.PRICE_OFFER]),
    ("c'est trop cher, fais un effort", None, [T.PRICE_OFFER]),
    ("on peut avoir un rabais sur le prix ?", None, [T.PRICE_OFFER]),  # bug n°10 : « rabais » = négo
    ("tu peux me faire une petite remise ?", None, [T.PRICE_OFFER]),
    ("fais-moi un geste sur le prix", None, [T.PRICE_OFFER]),
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
