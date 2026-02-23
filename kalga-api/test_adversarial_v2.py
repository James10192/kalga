"""
Test Adversarial V2.0 — 100+ scénarios corsés
================================================
Méthode : Adversariale — chaque section teste AUSSI les faux-positifs
à éviter (garde-fous), les cas limites, et les transitions d'état.

12 sections (A → L), ~107 tests au total.
"""
import sys, io, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.services.ai.conversation_engine import ConversationEngine

engine = ConversationEngine()

# ─── Produits ────────────────────────────────────────────────────────────────
roses  = {'name': 'Bouquet Roses', 'price': 18500,  'min_price': 14000}
iphone = {'name': 'iPhone 15 Pro', 'price': 950000, 'min_price': 750000}
sac    = {'name': 'Sac en cuir',   'price': 45000,  'min_price': 32000}

merchant = {'address': 'Marcory Zone 4', 'latitude': 5.30, 'longitude': -3.98}

results = []

# ─── Historiques réutilisables ───────────────────────────────────────────────
H0 = []
H1 = [
    {'content': 'Salut', 'is_from_client': True},
    {'content': 'Dispo 18 500 F', 'is_from_client': False},
]
H2 = H1 + [
    {'content': '12000', 'is_from_client': True},
    {'content': '16 000 F minimum', 'is_from_client': False},
]
H3 = H1 + [
    {'content': '15000 ok', 'is_from_client': True},
    {'content': 'Deal 15 000! Livraison ou pickup?', 'is_from_client': False},
]
H4 = H2 + [
    {'content': '12000', 'is_from_client': True},
    {'content': '16 000 F', 'is_from_client': False},
    {'content': '12000', 'is_from_client': True},
    {'content': '16 000 F prix final', 'is_from_client': False},
]
H_IP = [
    {'content': 'dispo le iPhone?', 'is_from_client': True},
    {'content': 'Oui! 950 000 F', 'is_from_client': False},
]
H_SAC = [
    {'content': 'le sac?', 'is_from_client': True},
    {'content': 'Sac cuir 45 000 F', 'is_from_client': False},
]


async def test(label, msg, product=roses, state='active', offer=None, history=None,
               expected_intent=None, expected_deal=None,
               expected_location=None, expected_state=None):
    h = history if history is not None else []
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
    results.append((status, label, issues, resp[:80], intent, new_st))
    return r


async def run_all():

    # =========================================================
    # A — PREMIER CONTACT (10 tests)
    # =========================================================
    print("\n[A] PREMIER CONTACT")

    await test('A01 Salut simple',           'Salut',
               expected_intent='EXPRESS_INTEREST', expected_deal=False)
    await test('A02 Allo',                   'Allo',
               expected_intent='EXPRESS_INTEREST', expected_deal=False)
    await test('A03 Abréviation bsr',        'bsr',
               expected_intent='EXPRESS_INTEREST', expected_deal=False)
    await test('A04 Disponible?',            'c dispo?',
               expected_intent='EXPRESS_INTEREST', expected_deal=False)
    await test('A05 Toujours en vente',      'toujours en vente?',
               expected_intent='EXPRESS_INTEREST', expected_deal=False)
    await test('A06 Prix direct 1er msg',    "c'est combien?",
               expected_intent='PRICE_QUESTION', expected_deal=False)
    await test('A07 Loc 1er msg',            'vous etes ou',     history=H0,
               expected_location=True, expected_deal=False)
    await test('A08 Position 1er msg',       'envoie moi la position', history=H0,
               expected_location=True, expected_deal=False)
    await test('A09 Adresse 1er msg',        'votre adresse svp', history=H0,
               expected_location=True, expected_deal=False)
    await test('A10 Message long interet',   'je viens de voir ton status ca m interesse vraiment',
               expected_intent='EXPRESS_INTEREST', expected_deal=False)

    # =========================================================
    # B — PRIX ET OFFRES — LIMITES (12 tests)
    # =========================================================
    print("\n[B] PRIX ET OFFRES — LIMITES")

    await test('B01 Prix bas',               '12000',     history=H1,
               expected_intent='PRICE_OFFER', expected_deal=False)
    await test('B02 Prix espace bas',        '12 000',    history=H1,
               expected_intent='PRICE_OFFER', expected_deal=False)
    await test('B03 Prix = min (deal)',      '14000',     history=H1,
               expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('B04 Prix > min (deal)',      '16000',     history=H1,
               expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('B05 iPhone trop bas',        '700k',      history=H_IP, product=iphone,
               expected_intent='PRICE_OFFER', expected_deal=False)
    await test('B06 iPhone deal',            '800k',      history=H_IP, product=iphone,
               expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('B07 Offre avec marqueur',    'je fais 13000', history=H1,
               expected_intent='PRICE_OFFER', expected_deal=False)
    await test('B08 Je donne + prix',        'je donne 12000 pas plus', history=H1,
               expected_intent='PRICE_OFFER', expected_deal=False)
    await test('B09 Prix + cho = objection', '18500 c est cho', history=H1,
               expected_intent='OBJECTION_PRICE', expected_deal=False)
    await test('B10 Trop cher + prix',       'c est trop cher 18500', history=H1,
               expected_intent='OBJECTION_PRICE', expected_deal=False)
    await test('B11 iPhone 250 000 (bas)',   '250 000',   history=H_IP, product=iphone,
               expected_intent='PRICE_OFFER', expected_deal=False)
    await test('B12 Sac = min price',        '32000',     history=H_SAC, product=sac,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # =========================================================
    # C — LOCALISATION — TOUS CAS (10 tests)
    # =========================================================
    print("\n[C] LOCALISATION — TOUS CAS")

    await test('C01 Loc 1er msg classique',  'vous etes ou',          history=H0,
               expected_location=True, expected_deal=False)
    await test('C02 Loc early H1',           'localisation stp',      history=H1,
               expected_location=True)
    await test('C03 Loc pendant négociation','c est ou le magasin',   history=H2,
               state='negotiating', offer=12000,
               expected_location=True, expected_deal=False)
    await test('C04 Loc après deal',         'c est ou exactement',   history=H3,
               state='agreed', offer=15000,
               expected_location=True, expected_deal=True)
    await test('C05 Loc quartier avec ?',    'vous etes a Cocody?',   history=H1,
               expected_location=True)
    await test('C06 Envoie position',        'envoie la position',    history=H1,
               expected_location=True)
    await test('C07 Position 1er msg',       'envoie moi la position',history=H0,
               expected_location=True, expected_deal=False)
    await test('C08 Adresse magasin 1er msg','adresse du magasin',    history=H0,
               expected_location=True, expected_deal=False)
    await test('C09 Donne moi la position',  'donne moi la position', history=H1,
               expected_location=True)
    await test('C10 Ou se trouve boutique',  'ou se trouve la boutique', history=H1,
               expected_location=True)

    # =========================================================
    # D — ACCEPTATION ET DESIGNATION (10 tests)
    # =========================================================
    print("\n[D] ACCEPTATION ET DESIGNATION")

    await test('D01 lui la',                 'lui la',     history=H1,
               expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('D02 elle la',                'elle la',    history=H1,
               expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('D03 je la prends',           'je la prends', history=H2,
               state='negotiating', offer=12000,
               expected_intent='ACCEPT_OFFER')
    await test('D04 je les prends',          'je les prends', history=H2,
               state='negotiating', offer=12000,
               expected_intent='ACCEPT_OFFER')
    await test('D05 banco seul',             'banco',      history=H2,
               state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER')
    await test('D06 weh je prends',          'weh je prends', history=H2,
               state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER')
    await test('D07 dja on se comprend',     'dja on se comprend', history=H2,
               state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER')
    await test('D08 go!',                    'go!',        history=H2,
               state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER')
    # ── Gardes-fous : "je veux" NE DOIT PAS toujours = acceptation ──
    # D09: "je veux savoir combien de temps" — "combien" déclenche PRICE_QUESTION
    # L'essentiel : pas de deal, pas d'acceptation implicite
    await test('D09 GUARD je veux savoir',   'je veux savoir combien de temps', history=H1,
               expected_deal=False)
    await test('D10 GUARD je veux voir',     'je veux voir la boutique', history=H1,
               expected_intent='EXPRESS_INTEREST', expected_deal=False)

    # =========================================================
    # E — PICKUP ET LIVRAISON (8 tests)
    # =========================================================
    print("\n[E] PICKUP ET LIVRAISON")

    await test('E01 Je viens chercher',      'je viens chercher', history=H3,
               state='agreed', offer=15000,
               expected_intent='CHOOSE_PICKUP', expected_deal=True, expected_location=True)
    await test('E02 Je passe demain',        'je passe demain',   history=H3,
               state='agreed', offer=15000,
               expected_intent='CHOOSE_PICKUP', expected_deal=True)
    await test('E03 Livraison svp',          'livraison svp',     history=H3,
               state='agreed', offer=15000,
               expected_intent='CHOOSE_DELIVERY', expected_deal=True)
    await test('E04 Je veux la livraison',   'je veux la livraison', history=H3,
               state='agreed', offer=15000,
               expected_intent='CHOOSE_DELIVERY', expected_deal=True)
    await test('E05 Retrait sur place',      'retrait sur place', history=H3,
               state='agreed', offer=15000,
               expected_intent='CHOOSE_PICKUP', expected_deal=True)
    await test('E06 Adresse Cocody',         'Cocody Angre derriere le lycee', history=H3,
               state='agreed', offer=15000,
               expected_intent='PROVIDE_ADDRESS', expected_deal=True)
    await test('E07 Oui livraison',          'oui livraison',     history=H3,
               state='agreed', offer=15000,
               expected_intent='CHOOSE_DELIVERY', expected_deal=True)
    await test('E08 Je me deplace',          'je me deplace',     history=H3,
               state='agreed', offer=15000,
               expected_intent='CHOOSE_PICKUP', expected_deal=True)

    # =========================================================
    # F — FRUSTRATION ET OBJECTIONS (10 tests)
    # =========================================================
    print("\n[F] FRUSTRATION ET OBJECTIONS")

    await test('F01 Arnaqueur = frustration', 'tu es un arnaqueur',    history=H1,
               expected_intent='EXPRESS_FRUSTRATION')
    await test('F02 Majuscules = frustration','TU TE FOUS DE MOI',     history=H2,
               state='negotiating',
               expected_intent='EXPRESS_FRUSTRATION')
    await test('F03 Exclamations x3',        'c est abusé!!!',         history=H2,
               state='negotiating',
               expected_intent='EXPRESS_FRUSTRATION')
    await test('F04 Voleur = frustration',   'vous etes des voleurs',  history=H1,
               expected_intent='EXPRESS_FRUSTRATION')
    await test('F05 Peur arnaque = trust',   'j ai peur d etre arnaque',history=H1,
               expected_intent='OBJECTION_TRUST')
    await test('F06 Original? = quality',    "c est original?",        history=H1,
               expected_intent='OBJECTION_QUALITY')
    await test('F07 Faux ou vrai? = quality','c est du vrai ou du faux?', history=H1,
               expected_intent='OBJECTION_QUALITY')
    await test('F08 Je reflechis = timing',  'je vais reflechir',      history=H1,
               expected_intent='OBJECTION_TIMING')
    await test('F09 Laisse tomber',          'laisse tomber',          history=H2,
               state='negotiating',
               expected_intent='SAY_GOODBYE', expected_deal=False)
    await test('F10 Trop cher simple',       'c est trop cher',        history=H1,
               expected_intent='OBJECTION_PRICE')

    # =========================================================
    # G — PIEGES FAUX-POSITIFS (12 tests — les plus corsés)
    # =========================================================
    print("\n[G] PIEGES FAUX-POSITIFS")

    # G01: "ok" sans contexte → PAS d'achat
    await test('G01 ok sans contexte',           'ok',  history=H0,
               expected_deal=False)
    # G02: "oui" premier message → PAS d'achat
    await test('G02 oui 1er message',            'oui', history=H0,
               expected_deal=False)
    # G03: "je veux juste regarder" → PAS une acceptation (BUG connu: startswith)
    await test('G03 GUARD je veux juste regarder','je veux juste regarder', history=H1,
               expected_intent='EXPRESS_INTEREST', expected_deal=False)
    # G04: Question livraison ≠ demande de livraison
    await test('G04 vous livrez? != CHOOSE_DEL',  'vous livrez a abidjan?', history=H3,
               state='agreed', offer=15000,
               expected_intent='EXPRESS_INTEREST')
    # G05: "je passe" au 1er message = visite curiosité, pas pickup
    await test('G05 je passe 1er msg != pickup',  'je passe voir', history=H0,
               expected_deal=False)
    # G06: "je viens chercher" 1er message sans deal → pas de location envoyée
    await test('G06 je viens 1er msg != deal',    'je viens chercher', history=H0,
               expected_deal=False)
    # G07: "je prends note de ton prix" → plus ACCEPT_OFFER (bug corrigé)
    # "prix" dans price_questions → PRICE_QUESTION, acceptable (deal=False = essentiel)
    await test('G07 GUARD je prends note',        'je prends note de ton prix', history=H1,
               expected_deal=False)
    # G08: Prix dans une plainte ≠ offre réelle
    await test('G08 plainte prix != offre',       '18500 c est trop', history=H1,
               expected_intent='OBJECTION_PRICE', expected_deal=False)
    # G09: "d'accord" seul en nego = acceptation (positif attendu)
    await test('G09 d accord = accept',           'd accord', history=H2,
               state='negotiating', offer=16000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)
    # G10: Adresse fournie après accord = PROVIDE_ADDRESS
    await test('G10 adresse = PROVIDE_ADDRESS',   'Yopougon Selmer carrefour', history=H3,
               state='agreed', offer=15000,
               expected_intent='PROVIDE_ADDRESS')
    # G11: "merci" seul ≠ deal
    await test('G11 merci != deal',               'merci', history=H1,
               expected_deal=False)
    # G12: Accusation escroc = frustration (pas objection)
    await test('G12 escrocs = frustration',       'vous etes des escrocs', history=H1,
               expected_intent='EXPRESS_FRUSTRATION')

    # =========================================================
    # H — HORAIRES (5 tests)
    # =========================================================
    print("\n[H] HORAIRES")

    await test('H01 Heure ouverture',        'vous ouvrez a quelle heure', expected_deal=False)
    await test('H02 Heure fermeture',        'vous fermez quand',          expected_deal=False)
    await test('H03 Weekend ouvert?',        'ouvert le samedi?',          expected_deal=False)
    await test('H04 Ouvert maintenant?',     'vous etes ouverts maintenant?', expected_deal=False)
    await test('H05 Horaires boutique',      'horaires de la boutique stp', expected_deal=False)

    # =========================================================
    # I — CORRECTION DE STATUT (5 tests)
    # =========================================================
    print("\n[I] CORRECTION STATUT")

    await test('I01 j ai rien achete',       "j'ai rien achete",  state='pending_pickup',
               expected_deal=False)
    await test('I02 j ai pas commande',      'j ai pas commande', state='pending_pickup',
               expected_deal=False)
    await test('I03 on n a pas conclu',      'on n a pas conclu', history=H3,
               state='agreed', offer=15000, expected_deal=False)
    await test('I04 j ai rien decide',       'j ai rien decide',  state='agreed',
               expected_deal=False)
    await test('I05 j ai pas dit oui',       'j ai pas dit oui',  history=H3,
               state='agreed', offer=15000, expected_deal=False)

    # =========================================================
    # J — FLUX MULTI-ETAPES ET TRANSITIONS (10 tests)
    # =========================================================
    print("\n[J] FLUX MULTI-ETAPES")

    await test('J01 Deal direct depuis active','15000 ok je prends', history=H1,
               expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('J02 Deal depuis negotiating', 'ok ok daccord', history=H2,
               state='negotiating', offer=16000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('J03 Adresse après accord',    'Abobo PK18',    history=H3,
               state='agreed', offer=15000,
               expected_intent='PROVIDE_ADDRESS', expected_deal=True)
    await test('J04 Relance nego après accord','13000 finalement', history=H3,
               state='agreed', offer=15000,
               expected_deal=True)   # reste deal=True (DEAL_AGREED protège)
    await test('J05 Offre > min depuis neg',  'bon 14500 ok',  history=H4,
               state='negotiating', offer=12000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('J06 Loc en nego != deal',     'c est ou le magasin', history=H2,
               state='negotiating', offer=12000,
               expected_deal=False, expected_location=True)
    await test('J07 Deal iPhone 800k',        '800 000',       history=H_IP,
               product=iphone, state='active',
               expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('J08 Loc + deal après accord', 'c est ou?',     history=H3,
               state='agreed', offer=15000,
               expected_deal=True, expected_location=True)
    await test('J09 Pickup depuis agreed',    'je passe',      history=H3,
               state='agreed', offer=15000,
               expected_deal=True, expected_location=True)
    await test('J10 Adresse livraison iPhone','Plateau immeuble Trade Center',
               history=H_IP, product=iphone, state='agreed', offer=800000,
               expected_intent='PROVIDE_ADDRESS', expected_deal=True)

    # =========================================================
    # K — NOUCHI AVANCÉ (10 tests)
    # =========================================================
    print("\n[K] NOUCHI AVANCE")

    await test('K01 oo daccord',             'oo daccord',         history=H2,
               state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER')
    await test('K02 c est cho',              'c est cho le prix',  history=H1,
               expected_intent='OBJECTION_PRICE')
    await test('K03 cho cho',               'cho cho ca vraiment', history=H1,
               expected_intent='OBJECTION_PRICE')
    await test('K04 c est comment',          'c est comment',
               expected_intent='PRICE_QUESTION', expected_deal=False)
    await test('K05 weh banco',              'weh banco',          history=H2,
               state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER')
    await test('K06 celui la',              'celui la',            history=H1,
               expected_intent='ACCEPT_OFFER')
    await test('K07 je veux lui la',         'je veux lui la',     history=H1,
               expected_intent='ACCEPT_OFFER')
    await test('K08 c est ou boutique 1er msg','c est ou votre boutique', history=H0,
               expected_location=True, expected_deal=False)
    await test('K09 prix gonfle',            'le prix est gonfle', history=H1,
               expected_intent='OBJECTION_PRICE')
    await test('K10 dja on deal',            'dja on deal',        history=H2,
               state='negotiating', offer=16000,
               expected_intent='ACCEPT_OFFER')

    # =========================================================
    # L — CAS LIMITES ET AMBIGUS (10 tests)
    # =========================================================
    print("\n[L] CAS LIMITES ET AMBIGUS")

    await test('L01 Message court hein',     'hein',   history=H1, expected_deal=False)
    await test('L02 Expression inconnue zo', 'zo',     history=H1, expected_deal=False)
    await test('L03 Nombre 4 chiffres',      '9999',   history=H1,
               expected_intent='PRICE_OFFER', expected_deal=False)
    await test('L04 Message très long',
               'je suis tres interesse par ce produit que tu as mis dans ton status '
               'whatsapp et je voudrais en savoir plus sur la qualite et les conditions de vente',
               expected_intent='EXPRESS_INTEREST', expected_deal=False)
    await test('L05 Frustration ponctuation','c est quoi ça???', history=H2,
               state='negotiating', expected_deal=False)
    await test('L06 Reprise après silence',  'je suis la',  history=H4,
               state='negotiating', offer=12000, expected_deal=False)
    await test('L07 Accord multi-mots',      '15000 ok je suis partant', history=H2,
               state='negotiating', offer=12000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)
    await test('L08 Refus poli',             'non merci ca va aller', history=H1,
               expected_intent='SAY_GOODBYE', expected_deal=False)
    await test('L09 Offre avec espace + k',  '14k',    history=H1,
               expected_intent='ACCEPT_OFFER', expected_deal=True)  # 14000 = min
    await test('L10 Réponse très courte ok', 'ok',     history=H2,
               state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)


asyncio.run(run_all())


# ============================================================
# RAPPORT FINAL
# ============================================================
total   = len(results)
passed  = sum(1 for r in results if r[0] == 'OK')
failed  = total - passed
crashes = sum(1 for r in results if r[0] == 'CRASH')

print()
print('=' * 70)
print('TEST ADVERSARIAL V2.0 — RAPPORT FINAL')
print('=' * 70)
print(f'Total: {total} | OK: {passed} | FAIL: {failed} | CRASH: {crashes}')
print(f'Score: {passed}/{total} = {passed/total*100:.1f}%')

if failed + crashes > 0:
    print()
    print('ECHECS DETECTES:')
    print('-' * 70)
    for status, label, issues, resp, intent, state in results:
        if status != 'OK':
            print(f'  [{status}] {label}')
            for issue in issues:
                print(f'    -> {issue}')
            print(f'    Response: {resp}')
            print(f'    Intent={intent} | State={state}')
            print()

print()
print('PAR SECTION:')
section_names = {
    'A': 'Premier contact',
    'B': 'Prix et offres',
    'C': 'Localisation',
    'D': 'Acceptation/Désignation',
    'E': 'Pickup/Livraison',
    'F': 'Frustration/Objections',
    'G': 'Pièges faux-positifs',
    'H': 'Horaires',
    'I': 'Correction statut',
    'J': 'Flux multi-étapes',
    'K': 'Nouchi avancé',
    'L': 'Cas limites',
}
sections = {}
for status, label, *_ in results:
    sec = label[0]
    if sec not in sections:
        sections[sec] = {'ok': 0, 'fail': 0}
    if status == 'OK':
        sections[sec]['ok'] += 1
    else:
        sections[sec]['fail'] += 1

for sec, counts in sorted(sections.items()):
    total_s = counts['ok'] + counts['fail']
    tag = 'OK  ' if counts['fail'] == 0 else 'FAIL'
    name = section_names.get(sec, sec)
    print(f'  [{tag}] {sec} ({name}): {counts["ok"]}/{total_s}')
