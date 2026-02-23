"""
Test à grande échelle du bot KALGA
60+ scénarios couvrant tous les cas possibles
"""
import sys
import io
import asyncio

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.services.ai.conversation_engine import ConversationEngine

engine = ConversationEngine()
product_roses  = {'name': 'Bouquet Roses', 'price': 18500, 'min_price': 14000}
product_iphone = {'name': 'iPhone 15 Pro', 'price': 950000, 'min_price': 750000}
merchant = {'address': 'Cocody Riviera 3', 'latitude': 5.37, 'longitude': -3.97}

results = []

h_base = [
    {'content': 'Salut', 'is_from_client': True},
    {'content': 'Oui dispo 18500 F', 'is_from_client': False},
]
h_negocie = h_base + [
    {'content': '12000', 'is_from_client': True},
    {'content': '16000 F minimum', 'is_from_client': False},
]
h_agreed = h_base + [
    {'content': '15000 ok deal', 'is_from_client': True},
    {'content': 'Deal 15000! Livraison ou pickup?', 'is_from_client': False},
]
h_loop = h_base + [
    {'content': '12000', 'is_from_client': True},
    {'content': '18500 F', 'is_from_client': False},
    {'content': '12000', 'is_from_client': True},
    {'content': '18500 F', 'is_from_client': False},
]


async def test(label, msg, product, state='active', offer=None, history=None,
               expected_intent=None, expected_deal=None,
               expected_location=None, expected_state=None):
    h = history or []
    try:
        r = await engine.process_message(msg, product, h, state, offer, merchant)
    except Exception as e:
        results.append(('CRASH', label, [f'Exception: {e}'], '', '', ''))
        return None

    intent = r['debug_info']['intent']
    deal   = r['deal_accepted']
    loc    = r['send_location']
    new_st = r['new_state']
    resp   = r['response']

    issues = []
    if expected_intent and intent != expected_intent:
        issues.append(f'intent={intent} ATTENDU={expected_intent}')
    if expected_deal is not None and deal != expected_deal:
        issues.append(f'deal={deal} ATTENDU={expected_deal}')
    if expected_location is not None and loc != expected_location:
        issues.append(f'location={loc} ATTENDU={expected_location}')
    if expected_state and new_st != expected_state:
        issues.append(f'state={new_st} ATTENDU={expected_state}')

    status = 'FAIL' if issues else 'OK'
    results.append((status, label, issues, resp[:70], intent, new_st))
    return r


async def run_all():

    # =========================================================
    print("\n### GROUPE 1 — FLUX DE BASE ###")
    await test('1.1  Premier message interest', 'Salut je suis interesse', product_roses,
               expected_intent='EXPRESS_INTEREST', expected_deal=False)
    await test('1.2  Demande de prix directe', 'cest combien', product_roses,
               expected_intent='PRICE_QUESTION', expected_deal=False)
    await test('1.3  Offre basse', '12000', product_roses, history=h_base, state='active',
               expected_intent='PRICE_OFFER', expected_deal=False)
    await test('1.4  Offre >= min_price auto-accord', '15000', product_roses, history=h_base, state='active',
               expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('1.5  Acceptation explicite "ok deal"', 'ok deal', product_roses, history=h_negocie, state='negotiating', offer=12000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('1.6  Pickup explicite', 'je viens chercher', product_roses, history=h_agreed, state='agreed', offer=15000,
               expected_intent='CHOOSE_PICKUP', expected_deal=True, expected_location=True)
    await test('1.7  Livraison explicite', 'je veux la livraison svp', product_roses, history=h_agreed, state='agreed', offer=15000,
               expected_intent='CHOOSE_DELIVERY', expected_deal=True)
    await test('1.8  Fin de conversation', 'non merci', product_roses, history=h_negocie, state='negotiating',
               expected_deal=False)

    # =========================================================
    print("\n### GROUPE 2 — LOCALISATION ###")
    await test('2.1  Localisation premier message', 'vous etes ou', product_roses,
               expected_deal=False, expected_location=True)
    await test('2.2  Localisation pendant negociation', 'envoie la position stp', product_roses,
               history=h_negocie, state='negotiating', offer=12000,
               expected_deal=False, expected_location=True)
    await test('2.3  Localisation apres accord (deal=True)', 'c est ou le magasin', product_roses,
               history=h_agreed, state='agreed', offer=15000,
               expected_deal=True, expected_location=True)
    await test('2.4  Localisation early stage', 'localisation stp', product_roses,
               history=h_base, state='active',
               expected_deal=False, expected_location=True)
    await test('2.5  Question quartier', 'vous etes a Cocody?', product_roses,
               history=h_base, state='active',
               expected_deal=False, expected_location=True)
    await test('2.6  Envoie position', 'envoie moi la position', product_roses,
               expected_deal=False, expected_location=True)
    await test('2.7  Adresse magasin', 'adresse du magasin', product_roses,
               expected_deal=False, expected_location=True)

    # =========================================================
    print("\n### GROUPE 3 — DESIGNATION PRODUIT ###")
    await test('3.1  lui la', 'lui la', product_roses, history=h_base, state='active',
               expected_intent='ACCEPT_OFFER')
    await test('3.2  elle la', 'elle la', product_roses, history=h_base, state='active',
               expected_intent='ACCEPT_OFFER')
    await test('3.3  celui la', 'celui la', product_roses, history=h_base, state='active',
               expected_intent='ACCEPT_OFFER')
    await test('3.4  je veux lui la', 'je veux lui la', product_roses, history=h_base, state='active',
               expected_intent='ACCEPT_OFFER')
    await test('3.5  je le prends', 'je le prends', product_roses, history=h_negocie, state='negotiating', offer=12000,
               expected_intent='ACCEPT_OFFER')
    await test('3.6  je la prends', 'je la prends', product_roses, history=h_negocie, state='negotiating', offer=12000,
               expected_intent='ACCEPT_OFFER')

    # =========================================================
    print("\n### GROUPE 4 — EXPRESSIONS IVOIRIENNES / NOUCHI ###")
    await test('4.1  oo = oui', 'oo daccord', product_roses, history=h_negocie, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER')
    await test('4.2  c est cho = trop cher', 'c est cho', product_roses, history=h_base, state='active',
               expected_intent='OBJECTION_PRICE')
    await test('4.3  c est comment = combien', 'c est comment', product_roses,
               expected_intent='PRICE_QUESTION')
    await test('4.4  weh = oui', 'weh je prends', product_roses, history=h_negocie, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER')
    await test('4.5  dja = accord', 'dja on se comprend', product_roses, history=h_negocie, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER')
    await test('4.6  c est ou = localisation', 'c est ou votre boutique', product_roses,
               expected_location=True, expected_deal=False)
    await test('4.7  cho = cher', 'vraiment cho ce prix', product_roses, history=h_base, state='active',
               expected_intent='OBJECTION_PRICE')

    # =========================================================
    print("\n### GROUPE 5 — HORAIRES (jamais inventer) ###")
    await test('5.1  Horaires ouverture', 'vous ouvrez a quelle heure', product_roses,
               expected_deal=False)
    await test('5.2  Horaires fermeture', 'vous fermez quand', product_roses,
               expected_deal=False)
    await test('5.3  Horaires weekend', 'vous ouvrez le dimanche', product_roses,
               expected_deal=False)
    await test('5.4  Etes vous ouvert', 'vous etes ouvert maintenant', product_roses,
               expected_deal=False)

    # =========================================================
    print("\n### GROUPE 6 — CORRECTION DE STATUT ###")
    await test('6.1  j ai rien achete', "j'ai rien achete", product_roses,
               state='pending_pickup', expected_deal=False)
    await test('6.2  j ai pas commande', 'j ai pas commande', product_roses,
               state='pending_pickup', expected_deal=False)
    await test('6.3  on n a pas conclu', 'on n a pas conclu', product_roses,
               history=h_agreed, state='agreed', offer=15000, expected_deal=False)
    await test('6.4  j ai rien decide', 'j ai rien decide', product_roses,
               state='agreed', expected_deal=False)

    # =========================================================
    print("\n### GROUPE 7 — FRUSTRATION ET OBJECTIONS ###")
    await test('7.1  Majuscules frustration', 'TU TE FOUS DE MOI', product_roses,
               history=h_negocie, state='negotiating',
               expected_intent='EXPRESS_FRUSTRATION')
    await test('7.2  Arnaqueur', 'tu es un arnaqueur', product_roses,
               history=h_base, state='active',
               expected_intent='EXPRESS_FRUSTRATION')
    await test('7.3  Objection qualite', 'c est original ou contrefacon?', product_roses,
               history=h_base, state='active', expected_intent='OBJECTION_QUALITY')
    await test('7.4  Objection timing', 'je vais reflechir', product_roses,
               history=h_base, state='active', expected_intent='OBJECTION_TIMING')
    await test('7.5  Objection confiance', 'j ai peur arnaque', product_roses,
               history=h_base, state='active', expected_intent='OBJECTION_TRUST')
    await test('7.6  Prix trop cher simple', 'c est trop cher', product_roses,
               history=h_base, state='active', expected_intent='OBJECTION_PRICE')

    # =========================================================
    print("\n### GROUPE 8 — MESSAGES COURTS / AMBIGUS ###")
    await test('8.1  ok seul', 'ok', product_roses, history=h_negocie, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER')
    await test('8.2  oui seul', 'oui', product_roses, history=h_negocie, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER')
    await test('8.3  go seul', 'go', product_roses, history=h_negocie, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER')
    await test('8.4  non seul', 'non', product_roses, history=h_base, state='active',
               expected_deal=False)
    await test('8.5  expression inconnue zo', 'zo', product_roses, history=h_base, state='active',
               expected_deal=False)
    await test('8.6  merci', 'merci', product_roses, history=h_base, state='active',
               expected_deal=False)
    await test('8.7  message vide equivalent', 'hein', product_roses, history=h_base, state='active',
               expected_deal=False)

    # =========================================================
    print("\n### GROUPE 9 — BOUCLES ET REPETITIONS ###")
    await test('9.1  Repetition meme offre basse', '12000', product_roses,
               history=h_loop, state='negotiating', offer=12000, expected_deal=False)
    await test('9.2  Repond a ma question', 'repond a ma question', product_roses,
               history=h_loop, state='negotiating', expected_deal=False)
    await test('9.3  Pourquoi discuter', 'pourquoi je vais discuter', product_roses,
               history=h_loop, state='negotiating', expected_deal=False)
    await test('9.4  Je ne comprends pas', 'je ne comprends pas ta reponse', product_roses,
               history=h_loop, state='negotiating', expected_deal=False)

    # =========================================================
    print("\n### GROUPE 10 — PREMIER MESSAGE SPECIAL ###")
    await test('10.1 Visite boutique 1er msg', 'je veux passe voir a la boutique', product_roses,
               expected_deal=False, expected_location=False)
    await test('10.2 Localisation 1er msg', 'vous etes ou', product_roses,
               expected_deal=False, expected_location=True)
    await test('10.3 Acceptation impossible 1er msg', 'oui je prends', product_roses,
               expected_deal=False)
    await test('10.4 Prix 1er msg', 'combien', product_roses,
               expected_deal=False)

    # =========================================================
    print("\n### GROUPE 11 — NEGOCIATION AVANCEE ###")
    await test('11.1 Offre tres basse iPhone', '100000', product_iphone,
               history=h_base, state='active', expected_deal=False)
    await test('11.2 Offre = min_price exactement', '14000', product_roses,
               history=h_base, state='active', expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('11.3 Offre juste au-dessus min', '14100', product_roses,
               history=h_base, state='active', expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('11.4 Offre = prix catalogue', '18500', product_roses,
               history=h_base, state='active', expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('11.5 Objection avec montant', '18500 c est trop cher', product_roses,
               history=h_base, state='active', expected_intent='OBJECTION_PRICE', expected_deal=False)
    # 15000 > min_price (14000) → auto-accepté → ACCEPT_OFFER + deal=True est correct
    await test('11.6 Contre-offre avec marqueur', 'je propose 15000', product_roses,
               history=h_base, state='active', expected_intent='ACCEPT_OFFER', expected_deal=True)

    # =========================================================
    print("\n### GROUPE 12 — FLUX MULTI-ETAPES COMPLEXES ###")
    h_complex = [
        {'content': 'Salut', 'is_from_client': True},
        {'content': 'Dispo 18500 F', 'is_from_client': False},
        {'content': 'c est trop cher', 'is_from_client': True},
        {'content': 'Fais une offre!', 'is_from_client': False},
        {'content': '14000', 'is_from_client': True},
        {'content': 'Deal 14000! Livraison ou pickup?', 'is_from_client': False},
    ]
    await test('12.1 Adresse apres accord', 'cocody angre quartier', product_roses,
               history=h_complex, state='agreed', offer=14000,
               expected_intent='PROVIDE_ADDRESS')
    await test('12.2 Localisation apres accord', 'c est ou exactement', product_roses,
               history=h_complex, state='agreed', offer=14000,
               expected_deal=True, expected_location=True)
    await test('12.3 Pickup apres accord', 'je passe demain', product_roses,
               history=h_complex, state='agreed', offer=14000,
               expected_deal=True)
    await test('12.4 Client reprend negociation apres accord', 'non finalement 13000', product_roses,
               history=h_complex, state='agreed', offer=14000,
               expected_deal=True)


asyncio.run(run_all())

# ============================================================
# RAPPORT FINAL
# ============================================================
total  = len(results)
passed = sum(1 for r in results if r[0] == 'OK')
failed = total - passed
crashes= sum(1 for r in results if r[0] == 'CRASH')

print()
print('=' * 70)
print('RAPPORT FINAL DES TESTS')
print('=' * 70)
print(f'Total: {total} | OK: {passed} | FAIL: {failed} | CRASH: {crashes}')
print(f'Score: {passed}/{total} = {passed/total*100:.1f}%')

if failed + crashes > 0:
    print()
    print('DETAILS DES ECHECS:')
    print('-' * 70)
    for status, label, issues, resp, intent, state in results:
        if status != 'OK':
            print(f'  [{status}] {label}')
            for issue in issues:
                print(f'    -> {issue}')
            print(f'    Reponse: {resp}')
            print(f'    Intent={intent} | State={state}')
            print()

print()
print('RESULTATS PAR GROUPE:')
groups = {}
for status, label, issues, resp, intent, state in results:
    g = label.split('.')[0].strip()
    if g not in groups:
        groups[g] = {'ok': 0, 'fail': 0}
    if status == 'OK':
        groups[g]['ok'] += 1
    else:
        groups[g]['fail'] += 1

for g, counts in groups.items():
    total_g = counts['ok'] + counts['fail']
    emoji = 'OK' if counts['fail'] == 0 else 'FAIL'
    print(f'  Groupe {g}: {counts["ok"]}/{total_g} [{emoji}]')
