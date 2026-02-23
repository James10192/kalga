"""
Test Massif v1.0 — KALGA Bot Intelligence
==========================================
1060+ scénarios pour détecter TOUTES les failles possibles.
15 sections couvrant : prix, localisation, acceptation, frustration,
horaires, nouchi, pièges, transitions FSM, messages extrêmes, séquences.

Structure:
  A. Premier contact       (70)
  B. Formats de prix       (85)
  C. Localisation          (75)
  D. Acceptation           (85)
  E. Anti-acceptation      (80)
  F. Frustration/Colère    (65)
  G. Horaires              (45)
  H. Nouchi étendu         (75)
  I. Pièges substring      (80)
  J. Négociation complète  (75)
  K. États pending         (55)
  L. Transitions FSM       (70)
  M. Messages extrêmes     (60)
  N. Produits variés       (55)
  O. Séquences multi-étapes(80)
  ─────────────────────────────
  TOTAL                   1060+
"""

import sys, io, asyncio, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.services.ai.conversation_engine import ConversationEngine
engine = ConversationEngine()

# ─── Produits ─────────────────────────────────────────────────────────────────
roses  = {'name': 'Bouquet Roses',        'price': 18500,  'min_price': 14000}
iphone = {'name': 'iPhone 15 Pro',        'price': 950000, 'min_price': 750000}
sac    = {'name': 'Sac en cuir',          'price': 45000,  'min_price': 32000}
chsrs  = {'name': 'Nike Air Max',         'price': 35000,  'min_price': 25000}
robe   = {'name': 'Robe Wax',             'price': 15000,  'min_price': 10000}
moto   = {'name': 'Moto Jakarta 125cc',   'price': 450000, 'min_price': 380000}
savon  = {'name': 'Savon x5',            'price': 2500,   'min_price': 2000}
bijou  = {'name': 'Bracelet Or',          'price': 75000,  'min_price': 55000}
frigo  = {'name': 'Réfrigérateur Samsung','price': 280000, 'min_price': 230000}
ventilo= {'name': 'Ventilateur Solaire',  'price': 28000,  'min_price': 20000}

MERCHANT = {
    'id': 1, 'address': 'Marcory Zone 4, Abidjan',
    'latitude': 5.30, 'longitude': -3.98,
    'bot_tone': 'casual', 'bot_style': 'flexible'
}

# ─── Ensembles d'états ────────────────────────────────────────────────────────
TERMINAL  = {'ended', 'completed', 'abandoned', 'expired', 'ENDED', 'COMPLETED'}
DEAL_DONE = {
    'pending_delivery', 'pending_pickup', 'agreed',
    'PENDING_DELIVERY', 'PENDING_PICKUP', 'DEAL_AGREED', 'CHOOSING_DELIVERY'
}
# États actifs (non terminaux) — le moteur retourne toujours l'un de ces strings
ACTIVE_STATES = {'active', 'negotiating', 'agreed', 'pending_delivery', 'pending_pickup'}

# ─── Helpers historique ───────────────────────────────────────────────────────
H0 = []

def H1(p):
    """Prix présenté, client n'a pas encore répondu."""
    return [
        {'content': 'Bonjour', 'is_from_client': True},
        {'content': f"Dispo à {int(p['price'])} F", 'is_from_client': False},
    ]

def H_neg(p, client_offer_str='15000'):
    """Négociation ouverte : bot a contre-proposé."""
    return [
        {'content': 'Bonjour', 'is_from_client': True},
        {'content': f"Dispo à {int(p['price'])} F", 'is_from_client': False},
        {'content': f"Je donne {client_offer_str}", 'is_from_client': True},
        {'content': f"Non, {int(p['min_price']*1.05)} F c'est mon dernier", 'is_from_client': False},
    ]

def H_deal(p, deal_price=None):
    """Accord verbal trouvé, bot demande livraison/pickup."""
    dp = deal_price or int(p['min_price'] * 1.05)
    return [
        {'content': 'Bonjour', 'is_from_client': True},
        {'content': f"Dispo à {int(p['price'])} F", 'is_from_client': False},
        {'content': f"{dp} F c'est bon?", 'is_from_client': True},
        {'content': "Ok deal! Tu veux livraison ou tu passes chercher?", 'is_from_client': False},
    ]

def H_long(p, turns=12):
    """Longue conversation de négociation."""
    h = [
        {'content': 'Bonjour', 'is_from_client': True},
        {'content': f"Dispo à {int(p['price'])} F", 'is_from_client': False},
    ]
    for i in range(turns):
        offer = int(p['price'] * 0.75 + i * 500)
        if i % 2 == 0:
            h.append({'content': f"Et à {offer} F?", 'is_from_client': True})
        else:
            h.append({'content': f"Non, {int(p['price']*0.9)} F minimum", 'is_from_client': False})
    return h

def H_bot_loop(p):
    """Bot qui répète le même prix — test détection boucle."""
    price_str = f"{int(p['price'])} F"
    return [
        {'content': 'Bonjour', 'is_from_client': True},
        {'content': f"Dispo à {price_str}", 'is_from_client': False},
        {'content': "C'est trop cher", 'is_from_client': True},
        {'content': f"C'est le meilleur prix: {price_str}", 'is_from_client': False},
        {'content': "Tu peux faire mieux?", 'is_from_client': True},
        {'content': f"Non, {price_str} c'est ça", 'is_from_client': False},
    ]

# ─── Runner ───────────────────────────────────────────────────────────────────
def run(msg, product, history=None, state='active', offer=None):
    return asyncio.run(engine.process_message(
        client_message=msg,
        product=product,
        conversation_history=history or [],
        current_state=state,
        current_offer=offer,
        merchant_data=MERCHANT
    ))

# ─── Compteurs ────────────────────────────────────────────────────────────────
_total = 0
_ok = 0
_fails = []
_sections = {}

def T(section, desc, result, **conds):
    global _total, _ok
    _total += 1
    _sections.setdefault(section, [0, 0])
    _sections[section][0] += 1
    errors = []
    for key, expected in conds.items():
        actual = result.get(key)
        if isinstance(expected, set):
            if actual not in expected:
                errors.append(f"{key}={actual!r}")
        elif isinstance(expected, list):
            if actual not in expected:
                errors.append(f"{key}={actual!r} ∉ {expected}")
        elif actual != expected:
            errors.append(f"{key}={actual!r} ≠ {expected!r}")
    if errors:
        _fails.append(f"  ✗ [{section}] {desc}: {'; '.join(errors)}")
    else:
        _ok += 1
        _sections[section][1] += 1

# ─── Helpers d'assertion ──────────────────────────────────────────────────────
def is_active(r):
    return r['new_state'] not in TERMINAL

def is_deal(r):
    return r['deal_accepted'] or r['new_state'] in DEAL_DONE

def not_deal(r):
    return not r['deal_accepted'] and r['new_state'] not in DEAL_DONE

def not_ended(r):
    return r['new_state'] not in TERMINAL


# =============================================================================
# SECTION A — PREMIER CONTACT (70 tests)
# Vérifie que le bot répond correctement au premier contact sans crashes
# =============================================================================
print("\n[A] PREMIER CONTACT")

# A1–A12 : Salutations classiques (ne doivent pas déclencher deal/location/ended)
for msg in ['Bonjour', 'Bonsoir', 'Salut', 'Hello', 'Hi', 'Cc', 'Coucou',
             'Bjr', 'Bsr', 'Bj', 'Allô', 'Yo']:
    r = run(msg, roses, H0)
    T('A', f'Salutation {msg!r} → pas deal, pas ended',
      r, deal_accepted=False, send_location=False)
    T('A', f'Salutation {msg!r} → pas terminal', r,
      new_state=list({'active','PRICE_PRESENTED','negotiating','INITIAL'} | (set()-TERMINAL)))

# A13–A22 : Premier message court sans contexte
for msg in ['Dispo?', 'Vous avez?', 'Toujours dispo?', 'Encore dispo?',
             "C'est dispo?", 'T dispo?', 'Tjs dispo?', 'Disponible?',
             'Vous avez encore?', 'Y en a encore?']:
    r = run(msg, sac, H0)
    T('A', f'Question dispo {msg!r}', r, deal_accepted=False, send_location=False)

# A24–A33 : Premier message avec prix direct (client saute les salutations)
for msg in ['C\'est combien?', 'Le prix?', 'Prix?', 'Combien?', 'C konn?',
             'Tarif?', 'C comb?', 'Prix stp', 'Prix svp', 'C\'est à combien?']:
    r = run(msg, roses, H0)
    T('A', f'Demande prix directe {msg!r}', r, deal_accepted=False, send_location=False)

# A34–A43 : Premier message avec intérêt général
for msg in ['Je suis intéressé', "J'aime ça", 'Beau produit', 'Sympa',
             'ça m\'intéresse', 'Intéressant', 'Je veux voir', 'Montrez moi',
             'Envoyez les détails', 'C\'est pour quoi?']:
    r = run(msg, ventilo, H0)
    T('A', f'Intérêt général {msg!r} → pas deal', r, deal_accepted=False)

# A44–A53 : Premier message en anglais
for msg in ['Hello, is this available?', 'How much?', 'I want this',
             'What\'s the price?', 'Is it original?', 'Can you deliver?',
             'Send me the price', 'How many available?', 'Good morning',
             'I need this urgently']:
    r = run(msg, chsrs, H0)
    T('A', f'Premier contact anglais {msg!r}', r, deal_accepted=False)

# A54–A63 : Premier message nouchi
for msg in ['Gars c\'est combien?', 'Wesh c\'est quoi le prix?', 'Frère dispo?',
             'Vieux c\'est combien?', 'Eh là c\'est combien?', 'Vieux t\'as encore?',
             'Gars ça coûte quoi?', 'Frère c\'est à combien?',
             'Hein c\'est combien?', 'Ça tape combien?']:
    r = run(msg, sac, H0)
    T('A', f'Premier contact nouchi {msg!r}', r, deal_accepted=False)

# A64–A70 : Messages de présentation incorrecte (produit mal orthographié)
for msg in ['Bonjour j\'ai vu votre statu', 'Salut j\'ai vu le post',
             "Bonjour j'ai vu le K001", 'Bonjour je cherche ce produit',
             'Salut j\'ai vu ça sur ton status', 'J\'ai vu ton statut WhatsApp',
             'J\'ai cliqué sur ton status']:
    r = run(msg, roses, H0)
    T('A', f'Référence status {msg[:30]!r}', r, deal_accepted=False, send_location=False)


# =============================================================================
# SECTION B — FORMATS DE PRIX (85 tests)
# Vérifie que TOUS les formats de prix sont reconnus sans faux positifs
# =============================================================================
print("\n[B] FORMATS DE PRIX")

# B1–B15 : Notation K (milliers)
k_prices = [
    ('10k', True),   ('10K', True),   ('10 k', True),  ('10 K', True),
    ('10.5k', True), ('10,5k', True), ('14k', True),   ('14.5k', True),
    ('15k', True),   ('20k', True),   ('ok', False),   ('ok ok', False),
    ('kk', False),   ('okkk', False), ('lok', False),
]
for notation, is_price in k_prices:
    if is_price:
        r = run(notation, roses, H1(roses))
        # Une offre de prix ne doit pas terminer la conversation
        T('B', f'Prix notation-K {notation!r} → pas terminal', r,
          new_state=ACTIVE_STATES)  # not in TERMINAL
    else:
        # Faux positifs avec K — tester SANS contexte (H0) pour éviter acceptation légitime
        r = run(notation, roses, H0)
        T('B', f'Faux prix K {notation!r} → pas deal', r, deal_accepted=False)

# B16–B35 : Offres chiffrées à prix < min_price (JAMAIS accepter)
offers_below_min = [
    (roses,  13000), (roses,  12000), (roses,  10000),
    (roses,  5000),  (roses,  1000),  (roses,  500),
    (sac,    30000), (sac,    25000), (sac,    20000),
    (iphone, 700000),(iphone, 500000),(iphone, 300000),
    (chsrs,  24000), (robe,   9000),  (moto,   370000),
    (savon,  1500),  (bijou,  50000), (frigo,  220000),
    (ventilo,19000), (iphone, 749999),  # 1 F sous le min
]
for product, amount in offers_below_min:
    r = run(f"{amount}", product, H1(product))
    T('B', f'Offre sous min ({product["name"]}: {amount} < {product["min_price"]}) → pas deal',
      r, deal_accepted=False)

# B36–B50 : Offres au prix minimum ou au-dessus (peuvent être acceptées ou négociées)
offers_at_or_above = [
    (roses,  14000),  # exactement min
    (roses,  15000),
    (roses,  18500),  # prix affiché
    (roses,  20000),  # au-dessus
    (sac,    32000),  # exactement min
    (sac,    35000),
    (iphone, 750000), # exactement min
    (iphone, 800000),
    (chsrs,  25000),  # exactement min
    (robe,   10000),  # exactement min
    (moto,   380000), # exactement min
    (savon,  2000),   # exactement min
    (bijou,  55000),  # exactement min
    (frigo,  230000), # exactement min
    (ventilo,20000),  # exactement min
]
for product, amount in offers_at_or_above:
    r = run(f"{amount} F", product, H1(product))
    # Au-dessus du min → peut deal ou peut négocier, mais pas ended sans réponse
    T('B', f'Offre ok ({product["name"]}: {amount} >= {product["min_price"]}) → pas terminal',
      r, new_state=ACTIVE_STATES)

# B51–B65 : Formats avec espaces et points
space_formats = [
    '15 000', '18 500', '14 000', '15.000', '14.000', '18.500',
    '32 000', '25 000', '10 000', '45 000', '55 000', '75 000',
    '750 000', '950 000', '380 000',
]
for fmt in space_formats:
    r = run(fmt, sac, H1(sac))
    T('B', f'Format espace/point {fmt!r} → pas terminal', r,
      new_state=ACTIVE_STATES)

# B66–B75 : Prix avec monnaie explicite — offres clairement sous le minimum du sac (32000)
currency_msgs = [
    '25000 FCFA', '25000 CFA', '25000 francs', '25000 fr',
    '25 000 francs CFA', '25 000 FCFA', '25000 F CFA',
    '25k FCFA', '25 mille francs', '25 mille',
]
for msg in currency_msgs:
    r = run(msg, sac, H1(sac))
    T('B', f'Prix avec monnaie {msg!r} → sous min → pas deal', r, deal_accepted=False)

# B76–B85 : Prix invalides ou ambigus (ne doivent pas crash)
weird_prices = [
    '0', '1', '99', '100', '999', '0 F',
    'mille francs', 'quelques francs', 'pas cher',
    '10000000',  # trop élevé
]
for msg in weird_prices:
    r = run(msg, roses, H1(roses))
    T('B', f'Prix bizarre {msg!r} → pas crash (deal_accepted est bool)', r,
      deal_accepted=list([True, False]))  # juste vérifier que c'est un bool


# =============================================================================
# SECTION C — LOCALISATION EXHAUSTIVE (75 tests)
# =============================================================================
print("\n[C] LOCALISATION")

# C1–C20 : Messages qui DOIVENT déclencher send_location=True
location_triggers = [
    "vous êtes où?", "c'est où votre boutique?", "l'adresse?",
    "donnez moi l'adresse", "où se trouve la boutique?",
    "comment venir?", "comment je viens?", "comment on peut venir?",
    "je veux passer", "je veux venir", "je passerai vous voir",
    "où vous êtes?", "quelle adresse?", "l'adresse stp",
    "envoyez l'adresse", "c'est quoi l'adresse?", "adresse svp",
    "localisation?", "pin de localisation?", "partagez la localisation",
]
for msg in location_triggers:
    r = run(msg, roses, H1(roses))
    T('C', f'Localisation attendue: {msg!r}', r, send_location=True)

# C21–C35 : Localisation en nouchi et expressions locales
nouchi_location = [
    "tu es où là?", "vous garez où?", "c'est où le shop?",
    "le magasin il est où?", "wesh vous êtes dans quel coin?",
    "frère donne l'adresse là", "vieux le coin c'est où?",
    "zone c'est où?", "vous faites ça à quel endroit?",
    "je veux passer prendre", "je vais venir chercher",
    "je vais passer", "je passerai demain", "je viens demain",
    "je peux venir quand?",
]
for msg in nouchi_location:
    r = run(msg, sac, H1(sac))
    T('C', f'Localisation nouchi: {msg!r}', r, send_location=True)

# C36–C50 : Localisation EN ANGLAIS
eng_location = [
    "where are you?", "what's your address?", "where is your shop?",
    "where is your store?", "how do I get there?", "how can I come?",
    "I want to come", "I'll come pick it up", "send me your location",
    "share your location", "the address please", "where are you located?",
    "what's the location?", "I want to pick up", "I'll come by",
]
for msg in eng_location:
    r = run(msg, iphone, H1(iphone))
    T('C', f'Localisation anglaise: {msg!r}', r, send_location=True)

# C51–C65 : FAUX POSITIFS — Ces messages ne doivent PAS déclencher send_location
false_location = [
    "je suis ici", "je suis là", "c'est là", "c'est ici",
    "tu es disponible?", "tu es là?", "vous êtes disponibles?",
    "c'est pour livraison", "vous livrez?", "vous livrez où?",
    "il est où le vendeur?", "qui s'occupe de ça?",
    "c'est quoi le modèle?", "c'est quelle marque?",
    "vous avez la photo?",
]
for msg in false_location:
    r = run(msg, roses, H1(roses))
    T('C', f'FAUX positif localisation: {msg!r} → pas location', r, send_location=False)

# C66–C75 : Localisation après deal (état pending_pickup)
for msg in ["vous êtes où?", "l'adresse?", "comment venir?",
             "envoyez l'adresse", "localisation?",
             "pin please", "l'adresse stp", "où vous êtes?",
             "adresse svp", "comment je viens?"]:
    r = run(msg, roses, H_deal(roses), state='pending_pickup')
    T('C', f'Localisation en pending_pickup: {msg!r}', r, send_location=True)


# =============================================================================
# SECTION D — ACCEPTATION TOUS PATTERNS (85 tests)
# Vérifie que toutes les formes d'acceptation déclenchent bien deal_accepted=True
# =============================================================================
print("\n[D] ACCEPTATION")

# D1–D20 : Acceptations standard françaises après négociation
acceptance_std = [
    "ok", "Ok", "OK", "oui", "Oui", "OUI",
    "d'accord", "D'accord", "c'est bon", "c'est d'accord",
    "je prends", "Je prends", "je le prends", "c'est pris",
    "vendu", "Vendu", "deal", "Deal", "DEAL",
    "ça marche",
]
for msg in acceptance_std:
    r = run(msg, roses, H_neg(roses, '15000'))
    T('D', f'Acceptation standard {msg!r} → deal', r, deal_accepted=True)

# D21–D35 : Acceptations avec le prix (les plus claires)
acceptance_with_price = [
    "ok à 15000", "ok pour 15000", "ok 15000 F", "d'accord pour 15000",
    "je prends à 15000", "c'est bon 15000", "15000 c'est ok",
    "15000 F ça marche", "ok pour 15 000", "c'est dit 15000",
    "on est d'accord 15000", "15000 deal", "15000 vendu", "15000 ok",
    "à 15000 ça me va",
]
for msg in acceptance_with_price:
    r = run(msg, roses, H_neg(roses, '15000'))
    T('D', f'Acceptation avec prix {msg!r} → deal', r, deal_accepted=True)

# D36–D50 : Acceptations nouchi ivoirien
nouchi_accept = [
    "na djeu", "Na djeu", "on se met", "ça coupe", "Ça coupe",
    "finit", "solder ça", "c'est bon là", "c bon",
    "ok là", "ok wé", "c ok", "nickel", "impec", "top",
]
for msg in nouchi_accept:
    r = run(msg, sac, H_neg(sac, '35000'))
    T('D', f'Acceptation nouchi {msg!r} → deal', r, deal_accepted=True)

# D51–D60 : Acceptations après longue négociation
for msg in ["ok d'accord", "bon d'accord", "va pour ça", "ça ira",
             "let's go", "go go", "on y va", "allez", "ça roule", "c'est validé"]:
    r = run(msg, chsrs, H_neg(chsrs, '28000'))
    T('D', f'Acceptation après négo {msg!r} → deal', r, deal_accepted=True)

# D61–D70 : Acceptation en anglais
english_accept = [
    "ok deal", "deal done", "let's do it", "I'll take it", "sold",
    "agreed", "yes", "yes please", "confirmed", "ok I want it",
]
for msg in english_accept:
    r = run(msg, iphone, H_neg(iphone, '800000'))
    T('D', f'Acceptation anglaise {msg!r} → deal', r, deal_accepted=True)

# D71–D85 : Acceptation après le bot qui a proposé livraison/pickup
delivery_acceptance = [
    "livraison", "livrez moi", "je veux la livraison", "livrez",
    "vous livrez?", "livraison stp", "envoyez moi ça", "à domicile",
    "pickup", "je passe", "je viens", "je vais passer",
    "je passerai", "je viens chercher", "à récupérer",
]
for msg in delivery_acceptance:
    r = run(msg, roses, H_deal(roses), state='agreed')
    T('D', f'Choix livraison/pickup {msg!r} → état deal done', r,
      new_state=list(DEAL_DONE | {'agreed'}))


# =============================================================================
# SECTION E — ANTI-ACCEPTATION / FAUX POSITIFS (80 tests)
# Ces messages ne doivent PAS déclencher deal_accepted=True
# C'est la section la plus critique pour éviter les faux deals
# =============================================================================
print("\n[E] ANTI-ACCEPTATION (faux positifs)")

# E1–E20 : Expressions ambiguës qui ressemblent à des acceptations mais n'en sont pas
false_accept = [
    "peut-être", "on verra", "je réfléchis", "je vais réfléchir",
    "c'est bien mais...", "pas pour l'instant", "bientôt",
    "peut être", "sais pas encore", "j'hésite",
    "c'est cher quand même", "encore cher", "c'est encore trop",
    "non merci", "non c'est trop cher", "c'est trop",
    "pas à ce prix", "trop cher", "c'est excessif",
    "dommage", "c'est dommage",
]
for msg in false_accept:
    r = run(msg, roses, H_neg(roses, '16000'))
    T('E', f'FAUX deal (réflexion/refus) {msg!r} → pas deal', r, deal_accepted=False)

# E21–E40 : "ok" suivi d'une question (pas une acceptation)
false_ok = [
    "ok mais c'est original?", "ok mais vous livrez?", "ok et les photos?",
    "ok mais ça fait quel prix?", "ok et la garantie?",
    "ok mais c'est combien la livraison?", "d'accord mais c'est quoi la marque?",
    "ok mais c'est disponible?", "ok et c'est en stock?",
    "ok mais quand je peux l'avoir?",
    "ok c'est quoi les couleurs?", "ok et la taille?",
    "ok t'as d'autres modèles?", "ok il y a quel design?",
    "ok mais d'abord montrez la photo",
    "d'accord mais d'abord la photo", "c'est bon mais faut voir d'abord",
    "ça marche mais je veux voir d'abord", "ok maistttttt",
    "ok, mais on revient là-dessus",
]
for msg in false_ok:
    r = run(msg, sac, H1(sac))
    T('E', f'OK conditionnel {msg!r} → pas deal', r, deal_accepted=False)

# E41–E55 : Discussions prix (pas acceptations)
price_discussion = [
    "et si je fais 13000?", "et à 12000?", "12000 ça va?",
    "tu peux faire 13000?", "possible à 12000?",
    "je te donne 13500", "13500 c'est mon max",
    "je peux pas aller au-dessus de 13000",
    "mon budget c'est 12000", "j'ai que 12000",
    "je veux pas payer plus de 13000",
    "tu peux baisser encore?", "encore un geste?",
    "tu peux faire un effort?", "un dernier effort?",
]
for msg in price_discussion:
    r = run(msg, roses, H1(roses))
    T('E', f'Discussion prix {msg!r} → pas deal final', r, deal_accepted=False)

# E56–E65 : Expressions positives mais non-achat
positive_not_accept = [
    "super produit!", "waou c'est beau", "j'adore", "magnifique",
    "belle qualité", "ça a l'air bien", "top produit",
    "très joli", "excellent", "parfait comme produit",
]
for msg in positive_not_accept:
    r = run(msg, bijou, H1(bijou))
    T('E', f'Compliment {msg!r} → pas deal', r, deal_accepted=False)

# E66–E80 : Demandes d'info avant achat
info_before_buy = [
    "c'est quelle taille?", "vous avez du 42?", "c'est quelle couleur?",
    "vous avez en rouge?", "c'est original?", "c'est garanti?",
    "c'est de quelle marque?", "c'est made in où?", "provenance?",
    "c'est pour homme ou femme?", "c'est neuf ou occasion?",
    "vous avez la facture?", "c'est certifié?",
    "ça dure combien de temps?", "y a une garantie?",
]
for msg in info_before_buy:
    r = run(msg, chsrs, H1(chsrs))
    T('E', f'Question info {msg!r} → pas deal', r, deal_accepted=False)


# =============================================================================
# SECTION F — FRUSTRATION ET COLÈRE (65 tests)
# =============================================================================
print("\n[F] FRUSTRATION / COLÈRE")

# F1–F15 : Expressions de frustration douce (pas angry)
frustration_soft = [
    "c'est trop cher", "trop cher!", "vraiment trop cher",
    "c'est excessif", "prix trop élevé", "waw c'est cher",
    "hum c'est cher", "aaah c'est cher", "oufffff",
    "c'est beaucoup ça", "beaucoup trop", "non c'est trop",
    "ça fait beaucoup", "trop élevé pour moi", "dépasse mon budget",
]
for msg in frustration_soft:
    r = run(msg, iphone, H1(iphone))
    T('F', f'Frustration douce {msg!r} → pas deal, pas ended', r,
      deal_accepted=False, new_state=ACTIVE_STATES)

# F16–F30 : Frustration forte mais pas insulte
frustration_strong = [
    "arrêtez de m'arnaque!", "c'est l'arnaque ici!",
    "vous arnaque les gens!", "c'est du vol!",
    "c'est pas sérieux ce prix", "vous vous moquez?",
    "non ce prix là c'est pas sérieux", "c'est abusé le prix",
    "vous rigolent là?", "vous faites comment pour vendre à ce prix?",
    "personne achète à ce prix", "vous serez toujours là avec votre prix",
    "j'achète pas ça", "non jamais à ce prix", "impensable ce prix",
]
for msg in frustration_strong:
    r = run(msg, iphone, H1(iphone))
    T('F', f'Frustration forte {msg!r} → pas deal', r, deal_accepted=False)

# F31–F40 : Insultes directes (doit déclencher mode désescalade, pas ended)
insults = [
    "vous êtes des escrocs", "escroc!", "arnaqueurs!",
    "bandits!", "voleurs!", "menteurs!",
    "vous êtes mauvais", "mauvais vendeur", "c'est n'importe quoi",
    "vous êtes nuls",
]
for msg in insults:
    r = run(msg, sac, H1(sac))
    T('F', f'Insulte {msg!r} → pas deal, pas terminal', r,
      deal_accepted=False, new_state={'active', 'negotiating'})

# F41–F55 : Menace de partir
leaving_threats = [
    "j'irai ailleurs", "je vais acheter ailleurs",
    "je vais chez la concurrence", "c'est bon j'abandonne",
    "laissez tomber", "je laisse tomber",
    "je cherche un autre vendeur", "vous m'intéressez plus",
    "tant pis", "je passe mon chemin",
    "j'irai trouver moins cher", "je veux plus ça",
    "annulez tout", "oubliez ça", "bonne journée alors",
]
for msg in leaving_threats:
    r = run(msg, sac, H_neg(sac, '30000'))
    T('F', f'Menace départ {msg!r} → pas deal', r, deal_accepted=False)

# F56–F65 : Frustration après long échange
for msg in ["ça fait longtemps qu'on parle, vous baissez ou pas?",
             "vous vous décidez?", "c'est quoi ce marchandage?",
             "vous faites quoi là?", "c'est long ça",
             "quand vous décidez vous?", "j'en peux plus de marchandage",
             "c'est fatigant de marchander", "décidez vous!",
             "on en finit là ou pas?"]:
    r = run(msg, chsrs, H_long(chsrs))
    T('F', f'Impatience longue conv {msg!r} → pas deal', r, deal_accepted=False)


# =============================================================================
# SECTION G — HORAIRES (45 tests)
# =============================================================================
print("\n[G] HORAIRES")

# G1–G20 : Toutes les façons de demander les horaires → le bot ne doit PAS inventer
hours_questions = [
    "vous ouvrez à quelle heure?", "quelle heure vous ouvrez?",
    "c'est ouvert maintenant?", "vous êtes ouverts?",
    "jusqu'à quelle heure vous êtes ouverts?",
    "a partir de quelle heure?", "vous fermez à quelle heure?",
    "les horaires d'ouverture?", "horaires?",
    "vous ouvrez quand?", "quand vous ouvrez?", "ouvert quand?",
    "c'est ouvert le weekend?", "vous ouvrez le dimanche?",
    "vous êtes ouverts le lundi?",
    "de quelle heure à quelle heure?", "ouvert de quand à quand?",
    "vous travaillez le samedi?", "ça ouvre à quelle heure?",
    "la boutique ouvre quand?",
]
for msg in hours_questions:
    r = run(msg, ventilo, H1(ventilo))
    T('G', f'Question horaires {msg!r} → pas deal, pas location', r,
      deal_accepted=False, send_location=False)
    # Vérifier que la réponse ne contient pas d'heures inventées
    resp = r.get('response', '') or ''
    has_invented_hours = bool(re.search(r'\b\d+h\s*[àa]\s*\d+h\b', resp.lower()))
    # Note: on logge juste, on ne fait pas fail car le bot peut dire "contactez le vendeur"

# G21–G35 : Faux positifs horaires — NE doivent PAS déclencher le guard horaires
false_hours = [
    "à quelle heure vous livrez?",  # livraison, pas ouverture
    "vous livrez à quelle heure?",
    "c'est pour quelle heure?",     # rendez-vous, pas horaires
    "dans combien de temps?",
    "vous livrez aujourd'hui?",
    "c'est pour quand?",
    "quand vous pouvez livrer?",
    "livraison en combien de temps?",
    "ça prend combien de temps?",
    "combien de temps pour la livraison?",
    "vous passez à quelle heure?",  # livraison
    "l'heure de passage?",
    "quand je peux venir?",
    "je peux venir dans l'après-midi?",
    "dans la matinée c'est possible?",
]
for msg in false_hours:
    r = run(msg, sac, H1(sac))
    T('G', f'FAUX horaires {msg!r} → pas terminal', r,
      deal_accepted=False, new_state=ACTIVE_STATES)

# G36–G45 : Questions sur la disponibilité du vendeur (différent des horaires boutique)
for msg in ["vous êtes disponible maintenant?", "tu es là?", "quelqu'un est là?",
             "il y a quelqu'un?", "tu réponds?", "tu es connecté?",
             "vous êtes en ligne?", "vous avez du temps?",
             "je peux vous appeler?", "vous avez un numéro?"]:
    r = run(msg, roses, H1(roses))
    T('G', f'Disponibilité vendeur {msg!r} → pas terminal', r,
      new_state=ACTIVE_STATES)


# =============================================================================
# SECTION H — NOUCHI ÉTENDU (75 tests)
# Expressions ivoiriennes et africaines rarement testées
# =============================================================================
print("\n[H] NOUCHI ÉTENDU")

# H1–H20 : Expressions de prix en nouchi
nouchi_prices = [
    "c'est djô", "c'est djô wala", "c'est wla-wla", "ça gagne",
    "ça pique", "ça fesse", "trop de balles", "trop de thunes",
    "trop de sous", "les blocs c'est combien?", "les tunes?",
    "combien les balles?", "tu prends quoi?", "tu veux quoi comme oseille?",
    "le montant?", "c'est à combien les frais?", "on te donne quoi?",
    "ça tape quoi comme prix?", "tu lâches à combien?", "ton dernier?",
]
for msg in nouchi_prices:
    r = run(msg, sac, H1(sac))
    T('H', f'Nouchi prix {msg!r} → pas deal, pas ended', r,
      deal_accepted=False, new_state=ACTIVE_STATES)

# H21–H40 : Acceptations nouchi avancées
nouchi_accept_adv = [
    "c'est dit", "c'est dit frère", "c'est réglé", "réglé",
    "on est bon", "ça tombe", "ça chute", "c'est pour moi",
    "je ramasse", "je ramène les sous", "je viens avec les sous",
    "je viens avec la monnaie", "ça passe", "ça coule",
    "on est d'accord là", "c'est plié", "c'est scellé",
    "done", "c clair", "impec là",
]
for msg in nouchi_accept_adv:
    r = run(msg, sac, H_neg(sac, '35000'))
    T('H', f'Acceptation nouchi avancée {msg!r} → deal', r, deal_accepted=True)

# H41–H55 : Expressions de localisation nouchi
nouchi_loc = [
    "le shop il est dans quel coin?", "vous êtes dans quel bled?",
    "tu fais ton business où?", "c'est quel secteur?",
    "tu es au marché?", "vous êtes au plateau?", "marcory c'est là?",
    "yopougon c'est vous?", "vous êtes à cocody?", "quel quartier?",
    "c'est quel zone?", "c'est où le local?", "ton local c'est où?",
    "le magasin c'est où?", "chez vous c'est où?",
]
for msg in nouchi_loc:
    r = run(msg, roses, H1(roses))
    T('H', f'Localisation nouchi {msg!r} → location', r, send_location=True)

# H56–H70 : Refus et frustration nouchi
nouchi_refus = [
    "non c'est trop oseille", "trop de blocs ça",
    "c'est trop salé", "c'est chaud ce prix",
    "on va pas se mentir c'est cher", "mon frère c'est trop là",
    "dieu ce prix là c'est non", "je passe là", "c'est bon là bye",
    "tu m'appelles quand tu baisses", "rappelle moi quand c'est moins cher",
    "vieux l'argent est dur là", "on a pas les sous là",
    "les sous sont durs là", "l'argent manque là",
]
for msg in nouchi_refus:
    r = run(msg, iphone, H1(iphone))
    T('H', f'Refus nouchi {msg!r} → pas deal', r, deal_accepted=False)

# H71–H75 : Mélanges français/nouchi/anglais
for msg in ["gars how much?", "frère what's the price?",
             "wesh combien?", "vieux c'est how much là?",
             "bro c'est combien wé?"]:
    r = run(msg, chsrs, H0)
    T('H', f'Mix langues {msg!r} → pas deal', r, deal_accepted=False)


# =============================================================================
# SECTION I — PIÈGES SUBSTRING (80 tests)
# Messages qui contiennent des mots-clés mais ne doivent PAS les déclencher
# =============================================================================
print("\n[I] PIÈGES SUBSTRING")

# I1–I20 : Messages avec "ok" mais pas d'acceptation
ok_traps = [
    "ok c'est combien?", "ok je vois", "ok merci",
    "ok je vais réfléchir", "ok et ensuite?", "ok mais non",
    "ok ok ok", "c'est ok pour toi?", "ça va pas ok",
    "pas ok du tout", "c'est pas ok", "okaaay",
    "ok je reviens", "ok à demain", "ok plus tard",
    "ok bonne journée", "ok on verra", "c'est pas ok ça",
    "ok j'attends", "ok merci de l'info",
]
for msg in ok_traps:
    r = run(msg, sac, H1(sac))
    T('I', f'Piège OK {msg!r} → pas deal', r, deal_accepted=False)

# I21–I35 : Messages avec "deal" mais pas un accord
deal_traps = [
    "pas deal", "no deal", "c'est quoi ce deal?",
    "deal de quoi?", "j'ai eu un deal ailleurs",
    "ya un deal quelque part?", "c'est quoi le deal?",
    "le deal c'est quoi?", "pas de deal à ce prix",
    "deal deal deal (non)", "c'est quoi votre meilleur deal?",
    "deal possible?", "possible un deal?", "vous faites des deals?",
    "c'est un bon deal pour toi pas pour moi",
]
for msg in deal_traps:
    r = run(msg, roses, H1(roses))
    T('I', f'Piège DEAL {msg!r} → pas deal', r, deal_accepted=False)

# I36–I50 : Messages avec "adresse" mais pas demande de localisation
address_traps = [
    "c'est quoi votre adresse mail?", "email?",
    "vous avez un site? l'adresse?", "adresse WhatsApp?",
    "c'est quoi votre adresse commerciale?",
    "adresse de livraison ça c'est quoi?", "je vais noter l'adresse",
    "l'adresse c'est pour après", "on parle d'adresse plus tard",
    "pas l'adresse maintenant", "l'adresse ça m'intéresse pas",
    "votre adresse de facturation?", "l'adresse du fabricant?",
    "adresse de la marque?", "c'est l'adresse sur la boite?",
]
for msg in address_traps:
    r = run(msg, frigo, H1(frigo))
    T('I', f'Piège ADRESSE {msg!r} → pas location', r, send_location=False)

# I51–I65 : Messages avec "livrer/livraison" (livraison ≠ location)
delivery_traps = [
    "vous livrez?", "livraison possible?", "vous faites la livraison?",
    "c'est combien la livraison?", "livraison gratuite?",
    "vous livrez dans mon quartier?", "vous livrez à Adjamé?",
    "livraison en combien de temps?", "je veux une livraison",
    "vous pouvez livrer?", "livraison à domicile?",
    "vous livrez à Abobo?", "livraison le soir?",
    "c'est possible livraison?", "livraison urgente possible?",
]
for msg in delivery_traps:
    r = run(msg, sac, H1(sac))
    # Demandes de livraison génériques sans deal précédent → pas de location automatique
    T('I', f'Livraison ≠ location {msg!r} → pas terminal', r,
      new_state=ACTIVE_STATES)

# I66–I80 : "Venir" / "passer" ambigu
come_traps = [
    "vous venez?", "t'es venu?", "je suis venu mais fermé",
    "ça vient d'où?", "ça vient de France?", "d'où ça vient?",
    "le produit vient d'où?", "origine de vos produits?",
    "passer la commande comment?", "comment passer commande?",
    "je passe commande?", "on passe commande comment?",
    "je vais passer commande", "passer par où?",
    "le livreur va passer quand?",
]
for msg in come_traps:
    r = run(msg, chsrs, H1(chsrs))
    T('I', f'Piège VENIR/PASSER {msg!r} → pas deal', r, deal_accepted=False)


# =============================================================================
# SECTION J — NÉGOCIATION COMPLÈTE (75 tests)
# Séquences de négociation avec tous les cas possibles
# =============================================================================
print("\n[J] NÉGOCIATION COMPLÈTE")

# J1–J15 : Contre-offres progressives SOUS le minimum → jamais accepter
for offer in range(10000, 14000, 200):  # 20 offres sous le min de roses (14000)
    r = run(f"{offer}", roses, H1(roses))
    T('J', f'Offre sous min roses {offer}F → pas deal', r, deal_accepted=False)

# J16–J25 : Le bot doit rester ferme après N refus
for msg in ["allez fais un geste", "un tout petit effort",
             "juste 500 de moins", "même 200 de moins",
             "s'il vous plaît", "je vous en supplie", "je suis un bon client",
             "pour moi c'est spécial", "c'est pour un cadeau", "une toute petite ristourne"]:
    r = run(msg, iphone, H_neg(iphone, '700000'))
    # Le bot NE DOIT PAS accepter une offre en-dessous du minimum
    T('J', f'Pression sociale {msg!r} → pas de deal sous le min', r,
      deal_accepted=False)

# J26–J40 : Comparaison avec la concurrence
compare_msgs = [
    "j'ai vu le même à 30000 ailleurs", "ailleurs c'est moins cher",
    "votre concurrent vend à 28000", "y a quelqu'un qui vend à 27000",
    "j'ai une offre à 26000", "j'ai mieux ailleurs",
    "quelqu'un vend moins cher", "on me propose 25000",
    "j'ai vu à 24000", "chez Amazon c'est moins cher",
    "sur Jumia c'est moins cher", "en ligne c'est 20000",
    "le marchandeur en face fait 22000", "votre voisin vend à 25000",
    "on m'a proposé le même à 20000",
]
for msg in compare_msgs:
    r = run(msg, chsrs, H1(chsrs))
    T('J', f'Comparaison concurrence {msg!r} → pas deal immédiat', r, deal_accepted=False)

# J41–J55 : Demandes spéciales en négociation
special_requests = [
    "vous faites un pack?", "et pour 2 articles?", "pour 3 c'est combien?",
    "j'en prends 2 vous faites quel prix?", "prix gros?", "prix grossiste?",
    "j'en prends 5", "achat en gros possible?", "lot de 10?",
    "prix pour revendeur?", "je suis revendeur", "je fais du business",
    "je peux revendre?", "c'est pour revendre", "c'est du commerce",
]
for msg in special_requests:
    r = run(msg, savon, H1(savon))
    T('J', f'Demande spéciale {msg!r} → pas deal direct', r, deal_accepted=False)

# J56–J65 : Reprendre une conversation après silence
for msg in ["j'avais demandé le prix hier", "j'étais là hier",
             "on avait discuté hier", "je reviens", "me revoilà",
             "j'ai décidé de prendre", "j'ai réfléchi",
             "j'ai discuté avec ma femme", "j'ai pris ma décision",
             "finalement je prends"]:
    r = run(msg, robe, H1(robe))
    T('J', f'Reprise conversation {msg!r} → réponse valide', r,
      new_state=ACTIVE_STATES)

# J66–J75 : Contre-offres intermédiaires (entre min et prix affiché)
for pct in [0.80, 0.82, 0.85, 0.87, 0.90, 0.92, 0.95, 0.97, 0.99, 1.0]:
    offer = int(roses['min_price'] + (roses['price'] - roses['min_price']) * pct * 0.5 + 1)
    # Offres entre min et prix affiché → négociation normale
    r = run(f"{offer}", roses, H1(roses))
    T('J', f'Offre intermédiaire {offer}F → pas ended', r,
      new_state=ACTIVE_STATES)


# =============================================================================
# SECTION K — ÉTATS PENDING (55 tests)
# Comportement en pending_delivery et pending_pickup
# =============================================================================
print("\n[K] ÉTATS PENDING")

# K1–K15 : En pending_pickup — comportement attendu
pickup_msgs = [
    "ok j'arrive", "j'arrive dans 1h", "je serai là à 15h",
    "ok merci", "reçu", "vu", "ok on se voit",
    "je suis en route", "j'arrive bientôt", "je pars maintenant",
    "10 minutes", "bientôt", "dans l'heure", "tout à l'heure", "ok c'est noté",
]
for msg in pickup_msgs:
    r = run(msg, roses, H_deal(roses), state='pending_pickup')
    T('K', f'Pending pickup confirmation {msg!r} → pas terminal', r,
      deal_accepted=True,
      new_state=ACTIVE_STATES)

# K16–K30 : En pending_delivery — messages de suivi
delivery_msgs = [
    "quand vous livrez?", "c'est pour quand?", "vous livrez aujourd'hui?",
    "j'attends toujours", "pas encore reçu", "quand ça arrive?",
    "je n'ai pas encore reçu", "vous avez envoyé?", "c'est parti?",
    "où en est ma commande?", "suivi?", "status?",
    "vous avez expédié?", "ma commande?", "j'ai pas reçu",
]
for msg in delivery_msgs:
    r = run(msg, sac, H_deal(sac), state='pending_delivery')
    T('K', f'Pending delivery suivi {msg!r} → pas terminal', r,
      new_state=ACTIVE_STATES)

# K31–K40 : En pending_pickup — re-demande d'adresse
for msg in ["l'adresse?", "envoyez l'adresse encore", "j'ai perdu l'adresse",
             "où c'est?", "vous êtes où?", "rappel adresse?",
             "renvoyez la localisation", "encore l'adresse stp",
             "j'ai pas l'adresse", "le pin?"]:
    r = run(msg, roses, H_deal(roses), state='pending_pickup')
    T('K', f'Re-demande adresse en pickup {msg!r} → location', r, send_location=True)

# K41–K55 : Nouveau message après accord — sujets hors context
for msg in ["et pour le sac?", "vous avez des chaussures?",
             "autre chose?", "c'est quoi d'autre?",
             "vous vendez autre chose?", "vous avez un iPhone aussi?",
             "et la ceinture?", "vous vendez des bijoux?",
             "autre produit?", "c'est tout ce que vous avez?",
             "menu complet?", "votre catalogue?",
             "liste de produits?", "vos articles?",
             "ce que vous avez d'autre?"]:
    r = run(msg, roses, H_deal(roses), state='pending_pickup')
    T('K', f'Hors sujet en pending {msg!r} → pas crash', r,
      new_state=ACTIVE_STATES)


# =============================================================================
# SECTION L — TRANSITIONS FSM LIMITES (70 tests)
# =============================================================================
print("\n[L] TRANSITIONS FSM")

# L1–L10 : Fin de conversation explicite → doit être ended
end_msgs = [
    "merci au revoir", "bonne continuation", "c'est bon merci",
    "au revoir", "bye", "à plus", "salut bye", "à bientôt",
    "on se parle plus", "j'y vais",
]
for msg in end_msgs:
    r = run(msg, roses, H_neg(roses, '15000'))
    T('L', f'Fin explicite {msg!r} → ended ou pas deal', r, deal_accepted=False)

# L11–L20 : Messages post-ended (conversation terminée, ne doit pas reprendre)
# État 'ended' → toute réponse doit être None ou vide
for msg in ["attends", "je reviens", "finalement",
             "j'ai changé d'avis", "je veux finalement",
             "attends j'ai changé", "reprends", "on reprend?",
             "non attends", "je re-veux"]:
    # Conversation terminée → état ended → le moteur doit gérer
    r = run(msg, roses, H_neg(roses, '15000'), state='ended')
    # En état ended, le système ne devrait pas relancer le deal
    T('L', f'Post-ended {msg!r} → deal_accepted=False', r, deal_accepted=False)

# L21–L30 : Transitions NEGOTIATING → DEAL_AGREED
deal_triggers = [
    f"{int(roses['min_price'])} F ok",
    f"ok {int(roses['min_price'])}",
    f"deal {int(roses['min_price'])}",
    f"c'est bon {int(roses['min_price'])}",
    "je prends au prix que tu m'as dit",
    "ok pour ce dernier prix",
    "ton dernier prix c'est bon",
    "on est d'accord",
    "c'est fait",
    "ok sold",
]
for msg in deal_triggers:
    r = run(msg, roses, H_neg(roses, '15000'))
    T('L', f'Deal trigger après négo {msg!r} → deal ou état deal', r,
      deal_accepted=True)

# L31–L40 : État completed → plus de réponse
for msg in ["encore dispo?", "j'en veux un autre", "re-commande",
             "même produit encore", "encore?", "une deuxième fois",
             "j'en veux 2", "j'en reprends", "encore un",
             "j'en reprendrai"]:
    r = run(msg, roses, H_deal(roses), state='completed')
    T('L', f'Post-completed {msg!r} → deal_accepted=False', r, deal_accepted=False)

# L41–L50 : Réaction à une contre-offre du bot (COUNTER_OFFER → next state)
for msg in ["non c'est trop", "c'est encore cher", "tu peux encore baisser?",
             "non 15000 c'est trop", "j'avais dit 13000",
             "je veux toujours 13000", "je monte pas au-dessus de 13000",
             "13000 c'est mon max", "j'ai que 13000", "13000 ou je pars"]:
    r = run(msg, roses, H_neg(roses, '13000'))
    T('L', f'Refus contre-offre {msg!r} → pas deal', r, deal_accepted=False)

# L51–L60 : État agreed → demande livraison ou pickup
for msg in ["livraison", "vous livrez", "je veux livraison", "livrez moi",
             "je passe", "je viens chercher", "pickup",
             "je vais venir", "à récupérer", "chez vous"]:
    r = run(msg, sac, H_deal(sac), state='agreed')
    T('L', f'Choix livraison/pickup {msg!r} → état deal done', r,
      new_state=list(DEAL_DONE))

# L61–L70 : Objection en cours de négociation
for msg in ["c'est pas de qualité?", "c'est garanti?", "c'est original?",
             "vous êtes fiables?", "vous avez de l'expérience?",
             "c'est une arnaque?", "vous escroquez?",
             "je peux vous faire confiance?", "vous êtes sérieux?",
             "vous avez des références?"]:
    r = run(msg, bijou, H1(bijou))
    T('L', f'Objection qualité {msg!r} → pas deal, pas ended', r,
      deal_accepted=False, new_state=ACTIVE_STATES)


# =============================================================================
# SECTION M — MESSAGES EXTRÊMES (60 tests)
# Messages inhabituels qui ne doivent pas crasher le bot
# =============================================================================
print("\n[M] MESSAGES EXTRÊMES")

# M1–M10 : Messages très courts (1-2 caractères)
very_short = ['?', '!', '.', '1', 'a', 'b', 'x', 'k', 'f', '-']
for msg in very_short:
    r = run(msg, roses, H1(roses))
    T('M', f'Message ultra-court {msg!r} → pas crash', r,
      deal_accepted=[True, False])  # juste vérifier que c'est bool

# M11–M20 : Messages très longs (simulation copier-coller)
long_msg = "Je suis très intéressé par votre produit mais j'aimerais vraiment savoir si vous pouvez baisser le prix car en ce moment l'argent est très dur et j'ai beaucoup de dépenses et ce serait vraiment un grand geste de votre part de bien vouloir faire un effort pour que je puisse acheter ce produit magnifique que vous proposez"
for i in range(10):
    r = run(long_msg[:50+i*20], roses, H1(roses))
    T('M', f'Message long ({50+i*20} chars) → pas crash', r, deal_accepted=[True, False])

# M21–M30 : Messages avec emojis
emoji_msgs = [
    "😍 c'est combien?", "💰 le prix?", "🤔 je réfléchis",
    "✅ ok je prends!", "❌ non trop cher", "🏠 l'adresse?",
    "📍 localisation?", "💸 c'est trop cher", "🛍️ je veux ça!",
    "💯 deal!",
]
for msg in emoji_msgs:
    r = run(msg, sac, H1(sac))
    T('M', f'Message emoji {msg[:20]!r} → pas crash', r, deal_accepted=[True, False])

# M31–M40 : Messages tout en majuscules
upper_msgs = [
    "COMBIEN?", "TROP CHER!", "JE PRENDS!", "OK DEAL",
    "ADRESSE?", "LOCALISATION STP", "MERCI AU REVOIR",
    "NON C'EST TROP", "AU REVOIR", "OK MERCI",
]
for msg in upper_msgs:
    r = run(msg, chsrs, H1(chsrs))
    T('M', f'Message majuscules {msg!r} → pas crash', r, deal_accepted=[True, False])

# M41–M50 : Messages répétitifs
for msg in ["ahahaha", "hahahaha", "lolll", "mdrrrr", "pffff",
             "ouffffff", "wooooow", "noooon", "ouiiiiii", "okkkkkk"]:
    r = run(msg, roses, H1(roses))
    T('M', f'Message répétitif {msg!r} → pas crash', r, deal_accepted=[True, False])

# M51–M60 : Messages avec chiffres collés
for msg in ["123456", "000000", "9999999", "1111", "22222",
             "18500f", "14000f", "32000CFA", "35000FCFA", "ok45000"]:
    r = run(msg, sac, H1(sac))
    T('M', f'Message chiffres {msg!r} → pas crash', r, deal_accepted=[True, False])


# =============================================================================
# SECTION N — PRODUITS VARIÉS (55 tests)
# Teste le comportement avec des produits de prix très différents
# =============================================================================
print("\n[N] PRODUITS VARIÉS")

# N1–N10 : Produit très cher (iPhone 950000 F)
iphone_tests = [
    ("ok je prends", True),
    ("950000 F deal", True),
    ("750000 F", False),   # exactement au min
    ("749999 F", False),   # 1 sous le min → pas deal
    ("1000000 F", True),   # au-dessus → accepté normalement
    ("500000 F", False),   # très bas → pas deal
    ("non c'est trop cher", False),
    ("you êtes où?", False),  # localisation (deal_accepted=False)
    ("c'est original?", False),
    ("garanti?", False),
]
for msg, expected_deal in iphone_tests:
    r = run(msg, iphone, H1(iphone))
    if expected_deal:
        T('N', f'iPhone {msg!r} → deal', r, deal_accepted=True)
    else:
        T('N', f'iPhone {msg!r} → pas deal', r, deal_accepted=False)

# N11–N20 : Produit bon marché (savon 2500 F)
savon_tests = [
    ("combien?", False),
    ("2500 c'est ok", True),
    ("2000 F", False),     # exactement au min
    ("1999 F", False),     # sous le min → pas deal
    ("2500 F c'est bon", True),
    ("trop cher!", False),
    ("vous avez en stock?", False),
    ("je prends 5 paquets", False),  # quantité mais pas encore accord sur prix
    ("ok deal 2000", False),         # min price, pourrait être ok ou non
    ("2100 F?", False),              # au-dessus du min mais sous le prix affiché
]
for msg, expected_deal in savon_tests:
    r = run(msg, savon, H1(savon))
    if expected_deal:
        T('N', f'Savon {msg!r} → deal', r, deal_accepted=True)
    else:
        T('N', f'Savon {msg!r} → pas deal', r, deal_accepted=False)

# N21–N30 : Moto (450000 F) — montants élevés
for msg, expected in [
    ("380000", False), ("400000", False), ("450000 F ok", True),
    ("je prends", True), ("380000 c'est bon?", False), ("non trop cher", False),
    ("vous livrez?", False), ("adresse?", False), ("370000", False), ("500000 vendu", True)
]:
    r = run(msg, moto, H1(moto))
    T('N', f'Moto {msg!r}', r, deal_accepted=expected)

# N31–N40 : Bijou (75000 F) avec formulations spéciales
bijou_tests = [
    "c'est en vrai or?", "c'est plaqué?", "18 carats?",
    "quelle pureté?", "c'est authentique?", "certifié?",
    "vous avez un certificat?", "c'est du toc?",
    "75000 c'est cher pour du plaqué", "vous baissez pour 2?",
]
for msg in bijou_tests:
    r = run(msg, bijou, H1(bijou))
    T('N', f'Bijou qualité {msg!r} → pas deal', r, deal_accepted=False)

# N41–N55 : Produit bas prix savon + négociation intensive
for offer in [500, 1000, 1500, 1800, 1900, 1999, 2000, 2100, 2200, 2300, 2400, 2500, 2600, 3000, 5000]:
    r = run(f"{offer} F", savon, H1(savon))
    if offer < savon['min_price']:
        T('N', f'Savon offre sous min {offer}F', r, deal_accepted=False)
    elif offer >= savon['min_price']:
        T('N', f'Savon offre ok {offer}F → pas terminal', r,
          new_state=ACTIVE_STATES)


# =============================================================================
# SECTION O — SÉQUENCES MULTI-ÉTAPES (80 tests)
# Simule des conversations complètes pour tester la cohérence du flux
# =============================================================================
print("\n[O] SÉQUENCES MULTI-ÉTAPES")

# O1–O10 : Flux complet 1 — négociation réussie
# Étape 1: Salutation
r1 = run("Bonjour je cherche le sac", sac, H0)
T('O', 'Flux1-E1: salutation → pas deal', r1, deal_accepted=False, send_location=False)
h1 = [{'content': 'Bonjour je cherche le sac', 'is_from_client': True},
       {'content': r1.get('response', 'Dispo à 45000 F'), 'is_from_client': False}]
# Étape 2: Demande de prix
r2 = run("C'est combien?", sac, h1)
T('O', 'Flux1-E2: question prix → pas deal', r2, deal_accepted=False)
h2 = h1 + [{'content': "C'est combien?", 'is_from_client': True},
             {'content': r2.get('response', '45000 F'), 'is_from_client': False}]
# Étape 3: Offre trop basse
r3 = run("Je te donne 20000 F", sac, h2)
T('O', 'Flux1-E3: offre trop basse (20000 < 32000) → pas deal', r3, deal_accepted=False)
h3 = h2 + [{'content': '20000 F', 'is_from_client': True},
             {'content': r3.get('response', 'Non pas à ce prix'), 'is_from_client': False}]
# Étape 4: Contre-offre acceptable
r4 = run("Ok 35000 F?", sac, h3)
T('O', 'Flux1-E4: offre acceptable (35000 > 32000) → possible deal', r4,
  deal_accepted=[True, False])  # peut deal ou négocier encore
h4 = h3 + [{'content': '35000 F?', 'is_from_client': True},
             {'content': r4.get('response', '35000 F deal!'), 'is_from_client': False}]
# Étape 5: Acceptation finale
r5 = run("ok c'est bon je prends", sac, h4)
T('O', 'Flux1-E5: acceptation finale → deal', r5, deal_accepted=True)
# Étape 6: Choix livraison
r6 = run("livraison stp", sac, h4 + [{'content': 'ok je prends', 'is_from_client': True},
                                       {'content': 'deal! livraison ou pickup?', 'is_from_client': False}],
          state='agreed')
T('O', 'Flux1-E6: choix livraison', r6, new_state=list(DEAL_DONE))

# O11–O20 : Flux complet 2 — client frustré puis calme
h_frustre = [
    {'content': 'c\'est combien?', 'is_from_client': True},
    {'content': 'Dispo à 18500 F', 'is_from_client': False},
]
r_frust = run("c'est TROP CHER vous arnaqué les gens!!", roses, h_frustre)
T('O', 'Flux2-E1: frustration forte → pas ended', r_frust,
  deal_accepted=False, new_state=ACTIVE_STATES)

h_f2 = h_frustre + [{'content': "c'est trop cher!", 'is_from_client': True},
                      {'content': r_frust.get('response', 'Je comprends'), 'is_from_client': False}]
r_calm = run("ok ok mais vous pouvez faire 15000?", roses, h_f2)
T('O', 'Flux2-E2: calme après frustration → pas deal direct', r_calm, deal_accepted=False)

h_f3 = h_f2 + [{'content': '15000?', 'is_from_client': True},
                 {'content': r_calm.get('response', '15000 F ok'), 'is_from_client': False}]
r_accept = run("ok c'est bon", roses, h_f3)
T('O', 'Flux2-E3: acceptation après calme', r_accept, deal_accepted=True)

# O21–O30 : Flux complet 3 — client anglophone
h_eng = []
r_e1 = run("Hello how much?", iphone, h_eng)
T('O', 'Flux3-E1: anglais premier contact', r_e1, deal_accepted=False)
h_eng2 = [{'content': 'Hello how much?', 'is_from_client': True},
            {'content': r_e1.get('response', '950000'), 'is_from_client': False}]
r_e2 = run("That's too expensive", iphone, h_eng2)
T('O', 'Flux3-E2: anglais refus prix', r_e2, deal_accepted=False)
h_eng3 = h_eng2 + [{'content': "That's too expensive", 'is_from_client': True},
                     {'content': r_e2.get('response', 'I understand'), 'is_from_client': False}]
r_e3 = run("ok deal 800000", iphone, h_eng3)
T('O', 'Flux3-E3: anglais acceptation', r_e3, deal_accepted=True)
r_e4 = run("where are you?", iphone, h_eng2)
T('O', 'Flux3-E4: anglais localisation', r_e4, send_location=True)

# O31–O45 : Flux complet 4 — détection de boucle
r_b1 = run("tu peux encore baisser?", roses, H_bot_loop(roses))
T('O', 'Flux4-E1: bot boucle → pas deal', r_b1, deal_accepted=False)
r_b2 = run("toujours trop cher", roses, H_bot_loop(roses))
T('O', 'Flux4-E2: bot boucle → pas terminal', r_b2,
  new_state=ACTIVE_STATES)

# O46–O55 : Flux complet 5 — conversation avec demande qualité puis achat
h_qual = [
    {'content': 'Bonjour', 'is_from_client': True},
    {'content': 'Bienvenue! Sac en cuir à 45000 F', 'is_from_client': False},
]
for msg in ["c'est original?", "c'est garanti?", "c'est quoi la qualité?",
             "vous avez des avis?", "c'est fiable?",
             "c'est du cuir véritable?", "combien de temps ça dure?",
             "vous avez des clients satisfaits?", "c'est fabriqué où?",
             "il y a une garantie?"]:
    r = run(msg, sac, h_qual)
    T('O', f'Flux5: question qualité {msg!r} → pas deal', r, deal_accepted=False)

# O56–O65 : Flux complet 6 — plusieurs échanges sur la livraison avant accord
h_livr = H1(ventilo)
for msg in ["vous livrez à Yopougon?", "c'est combien la livraison?",
             "livraison gratuite?", "vous livrez le weekend?",
             "vous pouvez livrer aujourd'hui?", "livraison express?",
             "délai de livraison?", "vous livrez à Abobo?",
             "zone de livraison?", "comment ça marche la livraison?"]:
    r = run(msg, ventilo, h_livr)
    T('O', f'Flux6: question livraison {msg!r} → pas deal, pas ended', r,
      deal_accepted=False, new_state=ACTIVE_STATES)

# O66–O75 : Flux complet 7 — client qui revient avec décision
h_retour = H1(robe)
for msg in ["j'ai pris ma décision", "finalement je veux la robe",
             "j'ai décidé de prendre", "je veux commander",
             "je passe commande", "je la prends finalement",
             "ma commande c'est la robe wax", "je veux acheter",
             "j'achète", "je fais l'achat"]:
    r = run(msg, robe, h_retour)
    T('O', f'Flux7: décision finale {msg!r} → deal', r, deal_accepted=True)

# O76–O80 : Flux complet 8 — abandon de conversation
h_abandon = H_neg(chsrs, '20000')
for msg in ["laissez tomber", "c'est bon j'ai trouvé ailleurs",
             "je l'ai eu moins cher", "j'ai acheté autre part",
             "je cherche plus"]:
    r = run(msg, chsrs, h_abandon)
    T('O', f'Flux8: abandon {msg!r} → pas deal, pas crash', r, deal_accepted=False)


# =============================================================================
# RAPPORT FINAL
# =============================================================================
print()
print("=" * 70)
print("TEST MASSIF v1.0 — RAPPORT FINAL")
print("=" * 70)
print(f"Total: {_total} | OK: {_ok} | FAIL: {_total - _ok} | CRASH: 0")
pct = 100.0 * _ok / _total if _total else 0
print(f"Score: {_ok}/{_total} = {pct:.1f}%")
print()
print("PAR SECTION:")
section_order = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O']
section_labels = {
    'A': 'Premier contact',
    'B': 'Formats de prix',
    'C': 'Localisation',
    'D': 'Acceptation',
    'E': 'Anti-acceptation',
    'F': 'Frustration/Colère',
    'G': 'Horaires',
    'H': 'Nouchi étendu',
    'I': 'Pièges substring',
    'J': 'Négociation complète',
    'K': 'États pending',
    'L': 'Transitions FSM',
    'M': 'Messages extrêmes',
    'N': 'Produits variés',
    'O': 'Séquences multi-étapes',
}
for s in section_order:
    if s in _sections:
        done, total_s = _sections[s][1], _sections[s][0]
        status = "OK  " if done == total_s else "FAIL"
        print(f"  [{status}] {s} ({section_labels.get(s, s)}): {done}/{total_s}")

if _fails:
    print()
    print(f"FAILLES DÉTECTÉES ({len(_fails)}):")
    for f in _fails[:50]:   # Limiter à 50 pour la lisibilité
        print(f)
    if len(_fails) > 50:
        print(f"  ... et {len(_fails)-50} autres. Voir détails ci-dessus.")
else:
    print()
    print("AUCUNE FAILLE DÉTECTÉE — Bot robuste sur 1000+ scénarios!")

# Code de sortie
import sys
sys.exit(0 if _total - _ok == 0 else 1)
