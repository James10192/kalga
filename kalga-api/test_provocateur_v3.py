"""
Test Provocateur V3.0 — 100 scénarios "pièges à réflexion"
===========================================================
Méthode : Chaque test a un TWIST. Le modèle doit distinguer
des messages qui se RESSEMBLENT mais ont des SENS OPPOSÉS.

10 catégories de pièges, 100+ tests.

Catégories :
  α — Faux accords    (acceptation qui n'en est pas)
  β — Vrais accords cachés (accord déguisé)
  γ — Localisation ambiguë (vrai / faux ASK_LOCATION)
  δ — Prix piégé      (offre vs objection vs question)
  ε — Substring traps (mot dans un mot)
  ζ — Nouchi ambigu   (expression ivoirienne à double sens)
  η — State-dependant (même mot = sens différent selon l'état)
  θ — Ponctuation / casse (modification du sens par la forme)
  ι — Double intention (deux signaux dans un message)
  κ — WhatsApp brut   (vrais messages comme les clients les envoient)
"""
import sys, io, asyncio, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.services.ai.conversation_engine import ConversationEngine

engine = ConversationEngine()

roses  = {'name': 'Bouquet Roses', 'price': 18500,  'min_price': 14000}
iphone = {'name': 'iPhone 15 Pro', 'price': 950000, 'min_price': 750000}
sac    = {'name': 'Sac cuir',      'price': 45000,  'min_price': 32000}

merchant = {'address': 'Treichville Av. 14', 'latitude': 5.30, 'longitude': -3.97}

results = []

H0 = []
H1 = [
    {'content': 'Salut', 'is_from_client': True},
    {'content': 'Dispo! 18 500 F', 'is_from_client': False},
]
H2 = H1 + [
    {'content': '12000', 'is_from_client': True},
    {'content': '16 000 F minimum', 'is_from_client': False},
]
H3 = H1 + [
    {'content': '15000 ok deal', 'is_from_client': True},
    {'content': 'Deal 15 000! Livraison ou pickup?', 'is_from_client': False},
]
H_IP = [
    {'content': 'iPhone dispo?', 'is_from_client': True},
    {'content': 'Oui! 950 000 F', 'is_from_client': False},
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
    # α — FAUX ACCORDS (12 tests)
    # Twist: contient un mot d'accord mais CE N'EST PAS un accord
    # =========================================================
    print("\n[α] FAUX ACCORDS")

    # α01: "oui" au début mais "non" à la fin — cancelation
    await test('α01 oui mais non',
               'oui mais non',
               history=H2, state='negotiating', offer=16000,
               expected_deal=False)

    # α02: "ok" + rétractation immédiate — le "mais" annule
    await test('α02 ok cest quand meme trop cher',
               'ok c est quand meme trop cher',
               history=H2, state='negotiating', offer=16000,
               expected_deal=False)

    # α03: "banco" + changement d'avis dans la même phrase
    await test('α03 banco j ai change d avis',
               'banco j ai change d avis',
               history=H2, state='negotiating', offer=16000,
               expected_deal=False)

    # α04: "parfait" + restriction temporelle = ce n'est pas un accord
    await test('α04 parfait pour une autre fois',
               'parfait pour une autre fois',
               history=H1, state='active',
               expected_deal=False)

    # α05: "top" + objection = annulation
    await test('α05 top mais trop cher',
               'top mais trop cher',
               history=H2, state='negotiating', offer=16000,
               expected_deal=False)

    # α06: "c'est bon" ≠ accord si suivi de restriction
    await test('α06 c est bon pour une autre fois',
               "c est bon pour une autre fois",
               history=H1, state='active',
               expected_deal=False)

    # α07: "deal" + condition non remplie
    await test('α07 deal si tu baisses encore',
               'deal si tu baisses encore',
               history=H2, state='negotiating', offer=16000,
               expected_deal=False)

    # α08: Je prends note ≠ achat (déjà fixé, vérification de régression)
    await test('α08 je prends note du prix',
               'je prends note du prix',
               history=H1, state='active',
               expected_deal=False)

    # α09: "je veux savoir" ≠ vouloir acheter
    await test('α09 je veux savoir les details',
               'je veux savoir tous les details',
               history=H1, state='active',
               expected_deal=False)

    # α10: "je veux voir" ≠ accepter
    await test('α10 je veux voir les photos',
               'je veux voir les photos',
               history=H1, state='active',
               expected_deal=False)

    # α11: "oui oui" + doute = pas encore convaincu
    await test('α11 oui oui mais je suis pas sur',
               'oui oui mais je suis pas sur',
               history=H1, state='active',
               expected_deal=False)

    # α12: "accord" + conditionnel = ce n'est pas ferme
    await test('α12 accord si la qualite est bonne',
               'accord si la qualite est bonne',
               history=H2, state='negotiating', offer=16000,
               expected_deal=False)

    # =========================================================
    # β — VRAIS ACCORDS CACHÉS (10 tests)
    # Twist: pas de mot d'accord explicite mais ÇA L'EST
    # =========================================================
    print("\n[β] VRAIS ACCORDS CACHÉS")

    # β01: "non" en début = "non, pas de problème" → acceptation
    await test('β01 non c est bon je le prends',
               'non c est bon je le prends',
               history=H2, state='negotiating', offer=16000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # β02: "allez" = let's do it, mais c'est dans les goobdyes
    await test('β02 allez ok je prends',
               'allez ok je prends',
               history=H2, state='negotiating', offer=16000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # β03: Double négatif = accord ("pas non" = oui)
    await test('β03 pas de probleme banco',
               'pas de probleme banco',
               history=H2, state='negotiating', offer=14000,
               expected_deal=True)

    # β04: Prix au min = auto-deal (sans mot d'accord)
    await test('β04 14000 point final',
               '14000 point final',
               history=H1, state='active',
               expected_deal=True)

    # β05: "même 16000 ça marche" — "même" précède le mot d'accord
    await test('β05 meme 16000 ca marche',
               'meme 16000 ca marche',
               history=H2, state='negotiating', offer=12000,
               expected_deal=True)

    # β06: "go go go" — répétition de go
    await test('β06 go go go',
               'go go go',
               history=H2, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # β07: "nickel" = parfait, synonyme ivoirien d'accord
    await test('β07 nickel',
               'nickel',
               history=H2, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # β08: "impeccable" = parfait
    await test('β08 impeccable',
               'impeccable',
               history=H2, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # β09: "wê" (avec accent) = oui en nouchi
    await test('β09 wê daccord',
               'wê daccord',
               history=H2, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # β10: Prix = prix catalogue → auto-accept
    await test('β10 18500 je prends',
               '18500 je prends',
               history=H1, state='active',
               expected_deal=True)

    # =========================================================
    # γ — LOCALISATION AMBIGUË (10 tests)
    # Twist: même type de message, résultat radicalement différent
    # =========================================================
    print("\n[γ] LOCALISATION AMBIGUË")

    # γ01: "vous êtes à Cocody?" = vraie demande de localisation ✓
    await test('γ01 vous etes a Cocody?',
               'vous etes a Cocody?',
               history=H1, state='active',
               expected_location=True, expected_deal=False)

    # γ02: "tu as une boutique?" = question d'existence, PAS localisation
    await test('γ02 tu as une boutique?',
               'tu as une boutique?',
               history=H0,
               expected_location=False, expected_deal=False)

    # γ03: "vous livrez à Cocody?" = livraison, PAS localisation du magasin
    await test('γ03 vous livrez a Cocody?',
               'vous livrez a Cocody?',
               history=H1, state='active',
               expected_location=False, expected_deal=False)

    # γ04: "vous avez une boutique à Cocody?" = wrong_location ou localisation simple
    await test('γ04 boutique a Cocody?',
               'vous avez une boutique a Cocody?',
               history=H1, state='active',
               expected_location=True, expected_deal=False)

    # γ05: "la boutique elle est jolie" = compliment, PAS localisation
    await test('γ05 boutique jolie != loc',
               'la boutique elle est jolie',
               history=H1, state='active',
               expected_location=False, expected_deal=False)

    # γ06: "envoie la photo" ≠ localisation (envoie = ambiguë)
    await test('γ06 envoie la photo != loc forced',
               'envoie la photo',
               history=H1, state='active',
               expected_deal=False)

    # γ07: Localisation + deal = les deux vrais
    await test('γ07 ou etes vous apres accord',
               'vous etes ou exactement',
               history=H3, state='agreed', offer=15000,
               expected_location=True, expected_deal=True)

    # γ08: "localisation" seul 1er message = toujours valide
    await test('γ08 localisation seule 1er msg',
               'localisation',
               history=H0,
               expected_location=True, expected_deal=False)

    # γ09: "où est ce que je peux venir?" = localisation
    await test('γ09 ou je peux venir',
               'ou je peux venir',
               history=H1, state='active',
               expected_location=True)

    # γ10: "c'est loin de vous?" = question de distance, pas localisation exacte
    await test('γ10 c est loin?',
               "c est loin de vous?",
               history=H1, state='active',
               expected_deal=False)

    # =========================================================
    # δ — PRIX PIÉGÉ (10 tests)
    # Twist: même prix, interprétation radicalement différente selon le contexte
    # =========================================================
    print("\n[δ] PRIX PIÉGÉ")

    # δ01: Prix seul < min = offre basse
    await test('δ01 13000 seul = offre',
               '13000',
               history=H1, state='active',
               expected_intent='PRICE_OFFER', expected_deal=False)

    # δ02: MÊME prix mais avec "encore" → indignation, PAS offre
    await test('δ02 encore 18500 = indignation',
               'encore 18500???',
               history=H2, state='negotiating', offer=12000,
               expected_intent='OBJECTION_PRICE', expected_deal=False)

    # δ03: Prix entre guillemets ironiques
    await test('δ03 soi disant 18500',
               'soi disant 18 500 cest le prix?',
               history=H1, state='active',
               expected_intent='OBJECTION_PRICE', expected_deal=False)

    # δ04: "ça vaut pas" + prix = objection
    await test('δ04 ca vaut pas ce prix',
               'ca vaut vraiment pas 18500 ce truc',
               history=H1, state='active',
               expected_intent='OBJECTION_PRICE', expected_deal=False)

    # δ05: "minimum" + prix = offre ferme (pas objection)
    await test('δ05 minimum 13500 offre',
               '13500 c est mon maximum',
               history=H2, state='negotiating', offer=12000,
               expected_intent='PRICE_OFFER', expected_deal=False)

    # δ06: Prix dans une question rhétorique ≠ offre
    await test('δ06 tu crois 18500 raisonnable?',
               'tu crois que 18500 c est raisonnable?',
               history=H1, state='active',
               expected_intent='OBJECTION_PRICE', expected_deal=False)

    # δ07: "sans déconner" + prix = offre sincère
    await test('δ07 sans deconner 15000',
               'sans deconner je peux faire 15000',
               history=H1, state='active',
               expected_deal=True)  # 15000 > min 14000 → auto-accept

    # δ08: "850k" pour iPhone = DEAL (> min 750k)
    await test('δ08 850k iPhone deal',
               '850k',
               history=H_IP, product=iphone,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # δ09: Prix > prix affiché = accord immédiat
    await test('δ09 20000 sur roses = deal',
               '20000',
               history=H1, state='active',
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # δ10: "à partir de combien?" = question de prix, PAS une offre
    await test('δ10 a partir de combien?',
               'a partir de combien vous pouvez negocier?',
               history=H1, state='active',
               expected_intent='PRICE_QUESTION', expected_deal=False)

    # =========================================================
    # ε — SUBSTRING TRAPS (10 tests)
    # Twist: un mot contient un autre mot qui activerait une logique incorrecte
    # =========================================================
    print("\n[ε] SUBSTRING TRAPS")

    # ε01: "BONSOIR" contient "bon" et "soir" — ne doit pas = accord
    await test('ε01 bonsoir != acceptation',
               'bonsoir',
               history=H0,
               expected_deal=False)

    # ε02: "Treichville" contient "ville" → quartier check? Non (pas dans la liste)
    await test('ε02 Treichville = adresse, pas localisation',
               'Treichville carrefour 27',
               history=H3, state='agreed', offer=15000,
               expected_intent='PROVIDE_ADDRESS', expected_deal=True)

    # ε03: "boutiquier" contient "boutique" → fausse localisation?
    await test('ε03 boutiquier contient boutique',
               'tu es un boutiquier serieux?',
               history=H1, state='active',
               expected_location=False, expected_deal=False)

    # ε04: "Yopougon Selmer" contient "ou" dans "Yopougon" → direction_words piège
    await test('ε04 Yopougon contient ou substr',
               'je suis a Yopougon Selmer',
               history=H3, state='agreed', offer=15000,
               expected_intent='PROVIDE_ADDRESS', expected_deal=True)

    # ε05: "laissez-moi" contient "laisse" → goodbye?
    await test('ε05 laissez-moi reflechir != goodbye',
               'laissez-moi reflechir un peu',
               history=H1, state='active',
               expected_intent='OBJECTION_TIMING', expected_deal=False)

    # ε06: "commandé" contient "commande" — status correction?
    await test('ε06 j ai commande = acte positif',
               'j ai deja commande chez vous avant',
               history=H1, state='active',
               expected_deal=False)

    # ε07: "arnaqueur" contient "arnaque" → trust_objection ou frustration?
    await test('ε07 arnaqueur = frustration pas objection',
               'les gens disent que tu es un arnaqueur',
               history=H1, state='active',
               expected_intent='EXPRESS_FRUSTRATION')

    # ε08: "marcory" est dans le mot "marcorer"? Non. Test que quartier = exact
    await test('ε08 Marcory Zone 4 = adresse livraison',
               'Marcory Zone 4 immeuble SIFCA',
               history=H3, state='agreed', offer=15000,
               expected_intent='PROVIDE_ADDRESS', expected_deal=True)

    # ε09: "je compte payer" — "compte" contient-il quelque chose?
    await test('ε09 je compte payer = interet',
               'je compte payer comment?',
               history=H1, state='active',
               expected_deal=False)

    # ε10: "Riviera 3" — "riviera" dans la liste quartiers → adresse livraison
    await test('ε10 Riviera 3 = adresse',
               'Riviera 3 derriere Total',
               history=H3, state='agreed', offer=15000,
               expected_intent='PROVIDE_ADDRESS', expected_deal=True)

    # =========================================================
    # ζ — NOUCHI AMBIGU (10 tests)
    # Twist: expressions ivoiriennes à double sens ou mal comprises
    # =========================================================
    print("\n[ζ] NOUCHI AMBIGU")

    # ζ01: "wê wê" (wê + wê) — double affirmation nouchi
    await test('ζ01 we we double affirmation',
               'wê wê',
               history=H2, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # ζ02: "c'est pas cho" = "c'est pas cher" = acceptation du prix
    await test('ζ02 c est pas cho = acceptable',
               'c est pas trop cho finalement',
               history=H1, state='active',
               expected_deal=False)  # intéressant mais pas encore deal

    # ζ03: "ça dégage" = partir = SAY_GOODBYE nouchi
    await test('ζ03 ca degage = goodbye',
               'ca degage ici trop cher',
               history=H2, state='negotiating',
               expected_intent='SAY_GOODBYE', expected_deal=False)

    # ζ04: "hein?" seul = incompréhension, PAS un accord
    await test('ζ04 hein seul = confusion',
               'hein?',
               history=H1, state='active',
               expected_deal=False)

    # ζ05: "dja même 15000" = accord à 15000 (nouchi + prix)
    await test('ζ05 dja meme 15000',
               'dja meme 15000',
               history=H2, state='negotiating', offer=12000,
               expected_deal=True)  # 15000 >= 14000 → auto-deal

    # ζ06: "oo oo" répétition = vraiment oui
    await test('ζ06 oo oo double',
               'oo oo daccord',
               history=H2, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # ζ07: "c'est fort" = c'est cher (nouchi)
    await test('ζ07 c est fort = cher',
               'c est fort quand meme ce prix la',
               history=H1, state='active',
               expected_intent='OBJECTION_PRICE', expected_deal=False)

    # ζ08: "ze" = je (faute de frappe très courante)
    await test('ζ08 ze prends = je prends',
               'ze la prends a 14000',
               history=H1, state='active',
               expected_deal=True)  # 14000 = min_price → auto-accept via prix (message court < 30 chars)

    # ζ09: "non c'est bon hein" = validation finale nouchi
    await test('ζ09 non c est bon hein = accord',
               'non c est bon hein je le prends',
               history=H2, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # ζ10: "wari" seul = argent — pas d'accord mais intérêt pour payer
    await test('ζ10 wari seul',
               'wari',
               history=H1, state='active',
               expected_deal=False)

    # =========================================================
    # η — STATE-DEPENDANT (10 tests)
    # Twist: même message, signification OPPOSÉE selon l'état
    # =========================================================
    print("\n[η] STATE-DEPENDANT")

    # η01: "je viens" en état active (premier contact) ≠ pickup
    await test('η01 je viens = visite curiosite',
               'je viens voir',
               history=H0, state='active',
               expected_deal=False, expected_location=False)

    # η02: MÊME "je viens" en état agreed = PICKUP
    await test('η02 je viens apres accord = pickup',
               'je viens voir',
               history=H3, state='agreed', offer=15000,
               expected_intent='CHOOSE_PICKUP', expected_deal=True, expected_location=True)

    # η03: "encore?" en état active = question
    await test('η03 encore = relance curieuse',
               'encore disponible?',
               history=H0,
               expected_deal=False)

    # η04: "où exactement?" early = demande de loc
    await test('η04 ou exactement early = location',
               'c est ou exactement?',
               history=H1, state='active',
               expected_location=True, expected_deal=False)

    # η05: "où exactement?" après accord = location AVEC deal
    await test('η05 ou exactement apres deal = loc + deal',
               'c est ou exactement?',
               history=H3, state='agreed', offer=15000,
               expected_location=True, expected_deal=True)

    # η06: "non" seul en active = refus
    await test('η06 non seul en active',
               'non',
               history=H1, state='active',
               expected_deal=False)

    # η07: "c'est bon" en agreed = confirmation état actuel
    await test('η07 c est bon en agreed',
               'c est bon',
               history=H3, state='agreed', offer=15000,
               expected_deal=True)  # état agreed → reste agreed

    # η08: "je reviendrai" en nego = timing objection
    await test('η08 je reviendrai = timing',
               'je reviendrai demain',
               history=H2, state='negotiating', offer=12000,
               expected_intent='OBJECTION_TIMING', expected_deal=False)

    # η09: "finalement 14000" en nego = accord auto
    await test('η09 finalement 14000 = auto-deal',
               'finalement 14000',
               history=H2, state='negotiating', offer=12000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # η10: "laisse tomber" après accord = correction de statut?
    await test('η10 laisse tomber apres accord',
               'laisse tomber',
               history=H3, state='agreed', offer=15000,
               expected_deal=True)  # état agreed protège, SAY_GOODBYE reste en agreed

    # =========================================================
    # θ — PONCTUATION ET CASSE (8 tests)
    # Twist: même mot, ponctuation différente = sens différent
    # =========================================================
    print("\n[θ] PONCTUATION ET CASSE")

    # θ01: "OK." avec point = accord (point strippé)
    await test('θ01 ok point = accord',
               'ok.',
               history=H2, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # θ02: "DEAL!!!!" majuscules + exclamations = accord enthousiaste
    await test('θ02 DEAL!!!! majuscules',
               'DEAL!!!!',
               history=H2, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # θ03: "NON!!!!" majuscules + exclamations = frustration
    await test('θ03 NON!!!! = frustration',
               'NON!!!!',
               history=H2, state='negotiating', offer=12000,
               expected_deal=False)

    # θ04: "TU TE FOUS DE MOI???" = frustration pure
    await test('θ04 majuscules pure frustration',
               'TU TE FOUS DE MOI???',
               history=H2, state='negotiating',
               expected_intent='EXPRESS_FRUSTRATION', expected_deal=False)

    # θ05: "go." (point) = accord strippé
    await test('θ05 go point = accord',
               'go.',
               history=H2, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # θ06: "banco!" (exclamation) = accord enthousiaste — déjà fixé
    await test('θ06 banco! exclamation = accord',
               'banco!',
               history=H2, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # θ07: "18 500" prix avec espace = bien détecté
    await test('θ07 18 500 avec espace = accord',
               '18 500',
               history=H1, state='active',
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # θ08: "9 999" = prix bas (9999 < 14000) = offre basse
    await test('θ08 9 999 = offre basse',
               '9 999',
               history=H1, state='active',
               expected_intent='PRICE_OFFER', expected_deal=False)

    # =========================================================
    # ι — DOUBLE INTENTION (10 tests)
    # Twist: le message contient deux signaux contradictoires
    # =========================================================
    print("\n[ι] DOUBLE INTENTION")

    # ι01: Prix + acceptation = auto-deal au prix proposé
    await test('ι01 15000 ok = accord prix',
               '15000 ok',
               history=H2, state='negotiating', offer=12000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # ι02: Localisation + acceptation = localisation prioritaire ou deal?
    await test('ι02 livraison + adresse = delivery deal',
               'je veux la livraison, je suis a Cocody Angre',
               history=H3, state='agreed', offer=15000,
               expected_deal=True)  # CHOOSE_DELIVERY ou PROVIDE_ADDRESS → deal=True

    # ι03: Frustration + prix = frustration gagne
    await test('ι03 frustration + prix',
               'FRANCHEMENT 18500 C EST DU VOL',
               history=H1, state='active',
               expected_intent='EXPRESS_FRUSTRATION', expected_deal=False)

    # ι04: Qualité + prix = qualité gagne?
    await test('ι04 qualite + prix',
               'c est de l original? et ca coute combien?',
               history=H1, state='active',
               expected_deal=False)

    # ι05: Localisation + pickup = pickup gagne (post-accord)
    await test('ι05 pickup + localisation post-accord',
               'je passe chercher, c est ou exactement?',
               history=H3, state='agreed', offer=15000,
               expected_deal=True, expected_location=True)

    # ι06: Bonjour + prix = prix présenté
    await test('ι06 bonjour + combien',
               'bonjour c est combien?',
               history=H0,
               expected_intent='PRICE_QUESTION', expected_deal=False)

    # ι07: Accord + hésitation = accord (first signal wins)
    await test('ι07 accord + hesitation',
               'ok 14000 mais je suis pas encore 100%',
               history=H1, state='active',
               expected_deal=True)  # 14000 >= min → auto-deal malgré hésitation

    # ι08: Goodbye + localisation = goodbye gagne
    await test('ι08 au revoir + position',
               'au revoir et envoie la position quand meme',
               history=H2, state='negotiating',
               expected_intent='SAY_GOODBYE', expected_deal=False)

    # ι09: Pickup + livraison = pickup gagne (premier détecté)
    await test('ι09 pickup vs livraison',
               'je viens chercher ou tu livres?',
               history=H3, state='agreed', offer=15000,
               expected_deal=True)

    # ι10: Status correction + prix = status correction gagne
    await test('ι10 correction + prix',
               "j ai rien achete c est juste 14000 que j avais propose",
               history=H3, state='agreed', offer=15000,
               expected_deal=False)  # status_correction priorité absolue

    # =========================================================
    # κ — WHATSAPP BRUT (10 tests)
    # Twist: vrais messages comme les clients ivoiriens les tapent vraiment
    # =========================================================
    print("\n[κ] WHATSAPP BRUT")

    # κ01: Tout en minuscules, fautes de frappe typiques
    await test('κ01 salut dispo reeel?',
               'salut il est encore diposible?',
               history=H0,
               expected_intent='EXPRESS_INTEREST', expected_deal=False)

    # κ02: Mix français/dioula
    await test('κ02 wari yeke obe = combien',
               'wari yeke obe',
               history=H0,
               expected_intent='PRICE_QUESTION', expected_deal=False)

    # κ03: Abréviation "pq" = pourquoi
    await test('κ03 pk si cher',
               'pk c est si cher',
               history=H1, state='active',
               expected_intent='OBJECTION_PRICE', expected_deal=False)

    # κ04: Message WhatsApp typique avec plusieurs idées
    await test('κ04 message reel complexe',
               'slt je voulais savoir le truc sur ton status cest tjs dispo?',
               history=H0,
               expected_intent='EXPRESS_INTEREST', expected_deal=False)

    # κ05: Réponse ultra courte typique
    await test('κ05 ok court en nego',
               'ok',
               history=H2, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # κ06: Chiffre en "k" minuscule pour iPhone
    await test('κ06 800k deal iPhone',
               '800k',
               history=H_IP, product=iphone, state='active',
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # κ07: "frère/frérot" dans la phrase = pas frustration
    await test('κ07 frere = pas frustration',
               'frere c est combien exactement',
               history=H0,
               expected_intent='PRICE_QUESTION', expected_deal=False)

    # κ08: Émoji dans le message (simulé en texte)
    await test('κ08 message avec emoji texte',
               'super je prends :)',
               history=H2, state='negotiating', offer=14000,
               expected_intent='ACCEPT_OFFER', expected_deal=True)

    # κ09: Demande vocale simulée (texte de transcription imprécis)
    await test('κ09 transcription imprécise',
               'oui je veux le produit que vous avez mis',
               history=H1, state='active',
               expected_deal=True)  # "je veux le produit" → acceptation

    # κ10: Urgence dans le message
    await test('κ10 urgent cest pour demain',
               'urgent svp c est pour demain matin',
               history=H1, state='active',
               expected_deal=False)  # intérêt urgent mais pas deal encore


asyncio.run(run_all())


# ============================================================
# RAPPORT
# ============================================================
total   = len(results)
passed  = sum(1 for r in results if r[0] == 'OK')
failed  = total - passed
crashes = sum(1 for r in results if r[0] == 'CRASH')

print()
print('=' * 70)
print('TEST PROVOCATEUR V3.0 — RAPPORT FINAL')
print('=' * 70)
print(f'Total: {total} | OK: {passed} | FAIL: {failed} | CRASH: {crashes}')
print(f'Score: {passed}/{total} = {passed/total*100:.1f}%')

if failed + crashes > 0:
    print()
    print('ECHECS — ANALYSE:')
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
print('PAR CATEGORIE:')
cat_names = {
    'α': 'Faux accords',
    'β': 'Vrais accords cachés',
    'γ': 'Localisation ambiguë',
    'δ': 'Prix piégé',
    'ε': 'Substring traps',
    'ζ': 'Nouchi ambigu',
    'η': 'State-dependant',
    'θ': 'Ponctuation/Casse',
    'ι': 'Double intention',
    'κ': 'WhatsApp brut',
}
cats = {}
for status, label, *_ in results:
    c = label[0]
    if c not in cats:
        cats[c] = {'ok': 0, 'fail': 0}
    if status == 'OK':
        cats[c]['ok'] += 1
    else:
        cats[c]['fail'] += 1

for c, counts in cats.items():
    total_c = counts['ok'] + counts['fail']
    tag = 'OK  ' if counts['fail'] == 0 else 'FAIL'
    name = cat_names.get(c, c)
    print(f'  [{tag}] {c} ({name}): {counts["ok"]}/{total_c}')
