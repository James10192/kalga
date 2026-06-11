# Refonte du moteur de dialogue — Design

**Date** : 2026-06-11
**Statut** : Validé (en attente de relecture marchand avant plan d'implémentation)
**Périmètre** : `kalga-api` — nouveau paquet `app/services/dialogue/`, intégration `chat_service`
**Approche retenue** : B — refonte ciblée du cerveau conversationnel (validée par le marchand)

---

## 1. Problème

Trois bugs terrain en deux jours, tous documentés par captures WhatsApp :

1. **Clôture prématurée** : « Je veux ça à 9000 et envoie moi plus de photo » → le bot a
   conclu la vente (pending_pickup + localisation + goodbye), ignorant la contre-offre ET
   la demande de photo.
2. **Demande ignorée + clôture en texte libre** : « Je veux d'autres photos » (2×) → le bot
   répond « Banco à 10 000 F ! On fait comment pour la livraison ? » sans envoyer de photo.
3. **Photo non sollicitée** (régression d'un correctif) : « hello » en réponse à un Statut
   arrive comme `[Répond à la photo: "#K053"] Hello` → le mot « photo » de la **métadonnée
   bridge** déclenchait l'envoi de photo.

**Cause systémique unique** : la décision « que faire de ce message ? » est éparpillée sur
4 couches non coordonnées — détecteurs à mots-clés (pollués par les métadonnées), LLM en
texte libre (peut « dire » des décisions business sans aucun garde-fou), tools LLM (gardés
après coup), cas spéciaux dans `chat_service`. Chaque correctif local crée une régression
ailleurs. Les deux god-functions (`generate_response` ~470 l, `handle_incoming_message`
~400 l) rendent le tout non testable.

## 2. Principe directeur

**Inverser le contrôle.** Aujourd'hui le LLM décide et le code rattrape. Demain :

> Le **code décide QUOI faire** (intentions, règles métier, état de la vente).
> Le **LLM décide COMMENT le dire** (formulation naturelle, ton, persona).

Les bugs ci-dessus deviennent des impossibilités structurelles, plus des consignes de prompt.

## 3. Décisions du marchand (gravées dans la machine à états)

1. **Accueil** : le bot salue et **suit la logique de la discussion** — pas de pitch récité,
   pas de photo ni de prix imposés ; si le client demande le prix d'emblée, il répond.
2. **Photos** : **uniquement à la demande du client — et alors TOUJOURS fournies**, dans
   tous les états, avant toute autre considération.
3. **Négociation** : **sans limite de tours, jusqu'à l'entente**. Le bot tient son prix
   plancher avec des formulations variées (anti-boucle sur la forme, fermeté sur le fond).

## 4. Architecture cible — pipeline à 5 étages

```
Message brut (bridge)
  → ① SAS D'ENTRÉE        sanitizer : retire [Répond à…]/[🎤…], normalise
  → ② COMPRÉHENSION       extraction de TOUTES les intentions (multi-intentions)
                          règles déterministes d'abord ; LLM classifieur JSON pour l'ambigu
  → ③ DÉCISION            machine à états de vente + politique + calcul de négo
                          → PLAN D'ACTIONS ordonné (100 % code, 0 % LLM)
  → ④ PAROLE              le LLM habille le plan (brief verrouillé) ; gabarits si LLM absent
  → ⑤ CONTRÔLE DE SORTIE  filet : aucun langage de clôture hors état CONCLUSION,
                          aucun prix < minimum, aucune promesse hors plan
  → Réponse + actions (photo, localisation, changement d'état)
```

**Ce qu'on garde tel quel** : mémoire 3 couches (STM/LTM/épisodique), base de connaissances,
actions d'exécution (`_execute_tool` : photos, variantes, localisation…), repositories,
bridge, module `merchant_commands`, waitlist/stock.

## 5. Catalogue d'intentions (fermé — `intents.py`)

`GREETING`, `ASK_INFO(sujet)` (description, qualité, état, garantie…), `ASK_PHOTO`,
`ASK_OTHER_PHOTOS`, `ASK_VARIANTS`, `ASK_OTHER_PRODUCTS`, `ASK_LOCATION`, `ASK_PAYMENT`,
`ASK_DELIVERY_INFO` (frais/délais), `PRICE_OFFER(montant)`, `ACCEPT_PRICE(montant)`,
`CHOOSE_DELIVERY`, `CHOOSE_PICKUP`, `GIVE_ADDRESS(texte)`, `GOODBYE`, `FRUSTRATION`,
`CORRECTION`, `HUMAN_REQUEST`, `UNCLEAR`.

Un message peut porter **plusieurs intentions** ; l'extraction les retourne **toutes**,
ordonnées. Règles déterministes (reprises et consolidées depuis `detectors.py`) pour les
cas fiables ; `llm_classifier` (sortie JSON stricte, catalogue imposé, timeout court) pour
l'ambigu uniquement. Échec LLM → on continue avec les règles seules.

## 6. Machine à états de vente (`sale_state.py`)

| État interne | Statut DB (inchangé) | Rôle |
|---|---|---|
| ACCUEIL | `active` | Salutation contextuelle, suit le message du client |
| RENSEIGNEMENT | `active` | Répondre à chaque demande avant toute relance |
| NÉGOCIATION | `negotiating` | Contre-offres calculées par le code |
| CONCLUSION | `agreed` | Prix accepté explicitement → livraison ou retrait ? |
| LOGISTIQUE_LIVRAISON | `pending_delivery` | Collecte d'adresse, notification marchand |
| LOGISTIQUE_RETRAIT | `pending_pickup` | Envoi localisation, notification marchand |
| APRÈS-VENTE | `completed` | Merci + lien boutique, extraction LTM |
| FIN | `ended` | Sortie polie sans vente, relances programmées |

**Verrou de CONCLUSION** (la porte anti-« Banco ») — on n'y entre que si :
- le client accepte **un prix précis** (« ok pour 18 000 », « je prends à 18k »), OU
- il dit « ok/banco/je prends » **immédiatement après** une offre chiffrée ferme du bot,
- ET le message ne contient **aucune autre intention en attente** (photo, variante, question).
Un « oui » répondant à « ça t'intéresse ? » ne franchit jamais cette porte.

**Transitions clés** : contre-offre client en CONCLUSION/LOGISTIQUE → retour NÉGOCIATION
(l'accord saute) · changement livraison↔retrait accepté en LOGISTIQUE · toute demande
d'info dans n'importe quel état → traitée puis retour à l'état courant.

**Règles transverses (tous états)** : `ASK_PHOTO`/`ASK_OTHER_PHOTOS` → action photo,
toujours · `ASK_LOCATION` → localisation sans conclure · `FRUSTRATION` → apaisement ·
`HUMAN_REQUEST`/litige → passage au marchand · `CORRECTION` → mode correction ·
`GOODBYE` clair → FIN · rupture de stock → waitlist (logique existante).

## 7. Politique et plan d'actions (`policy.py`, `actions.py`)

`policy.decide(intents, state, context) -> ActionPlan` — fonction **pure**.

Catalogue d'actions : `SEND_TEXT(faits_à_transmettre)`, `SEND_PHOTO`, `SEND_VARIANTS`,
`SEND_LOCATION`, `SEND_PAYMENT_INFO`, `COUNTER_OFFER(prix)`, `CONFIRM_DEAL(prix)`,
`REQUEST_ADDRESS`, `NOTIFY_MERCHANT(raison)`, `HANDOVER_HUMAN`, `END_CONVERSATION`,
`JOIN_WAITLIST`.

**Ordre d'exécution d'un plan** : demandes du client d'abord (photo/variantes/infos),
négociation/transition de vente ensuite. Exemple — « je veux ça à 9000 et envoie moi plus
de photo » → `[SEND_PHOTO, COUNTER_OFFER(9500)]` : les deux, dans cet ordre.

## 8. Négociation calculée (`negotiation.py`)

Pure et déterministe : prix plancher effectif = `min_price` ajusté fidélité (logique
actuelle conservée) ; concessions **décroissantes** (l'écart entre dernier prix bot et
offre client se réduit de moitié à chaque tour, arrondi commerçant, jamais sous le
plancher) ; arrivé au plancher → le prix ne bouge plus, `speech` varie les formulations.
Offre client ≥ prix affiché → acceptation directe. Contre-offre client < plancher après
plusieurs refus → le bot propose le plancher comme dernier prix et le tient.

## 9. Contrat LLM (`speech.py`, `llm_classifier.py`)

Le client DeepSeek passe derrière un **Protocol** (`LLMClient`) :
`classify(message, contexte) -> liste d'intentions | None` et
`speak(brief) -> texte | None`. Un **FakeLLMClient** sert tous les tests.

**Brief de parole (verrouillé)** : décision prise + faits à transmettre + interdits
(conclure, promettre, mentionner le prix minimum) + persona marchand + mémoire client
(LTM/épisodique pour personnaliser : « content de te revoir ! ») + fenêtre STM.
LLM indisponible → gabarits (recyclage de `fallback_responses`) : moins naturel,
jamais faux.

**Filet de sortie (`output_guard.py`)** : familles de motifs interdits selon l'état —
langage de clôture (« banco », « on s'entend pour », « livraison ou tu viens ») hors
CONCLUSION/LOGISTIQUE ; tout montant < plancher ; promesses hors plan. Violation →
une reprise corrective, sinon gabarit sûr.

**Budget perf** : messages clairs = 0 appel de compréhension + 1 appel de parole
(ou 0 si gabarit) ; ambigus = 2 appels max. Aujourd'hui : 1 appel systématique + corrections.

## 10. Composants

```
app/services/dialogue/
├── __init__.py
├── sanitizer.py        ① nettoyage métadonnées bridge/système
├── intents.py          ② catalogue fermé + dataclasses Intent
├── understanding.py    ② extraction multi-intentions par règles
├── llm_classifier.py   ② classifieur LLM JSON (secours)
├── sale_state.py       ③ FSM de vente + mapping statuts DB
├── policy.py           ③ (intentions, état, contexte) → ActionPlan
├── negotiation.py      ③ calcul des contre-offres (pur)
├── actions.py          ③ dataclasses Action / ActionPlan
├── speech.py           ④ brief → LLM ; gabarits de secours
├── output_guard.py     ⑤ filet de sortie
├── llm_protocol.py     Protocol LLMClient + FakeLLMClient (tests)
└── orchestrator.py     chef d'orchestre mince (~100 l, zéro logique métier)
```

`chat_service` appelle `orchestrator.handle()` à la place de `generate_response()` (drapeau,
voir §12). L'exécution des actions réutilise la mécanique `_execute_tool` existante.
Absorbés à terme : `detectors.py` (→ understanding), `deal_guard.py` (→ policy),
`fallback_responses.py` (→ speech), `engine/` (→ FSM/policy), `generate_response` (→ pipeline).

## 11. Tests

- **Unitaires** par module : transitions FSM, maths de négo, règles d'intentions
  (y compris messages préfixés bridge), filet de sortie, politique multi-intentions.
- **Scénarios rejoués** (FakeLLM, déterministes, sans réseau) : les **3 bugs terrain en
  tests de régression permanents** + ~15 conversations complètes (parcours nominal
  accueil→livraison, client radin, multi-intentions, vocal transcrit, frustré, changement
  livraison↔retrait, rupture de stock→waitlist, client connu fidélité…).
- Les 61 tests existants restent verts pendant toute la migration.

## 12. Migration — étrangleur en 5 phases

| Phase | Contenu | Livrable vérifiable |
|---|---|---|
| P1 | sanitizer + intents + understanding | extraction multi-intentions testée sur corpus — ✅ fait |
| P2 | sale_state + policy + negotiation | le cerveau complet décide juste, sans LLM, au test — ✅ fait |
| P3 | llm_protocol + speech + output_guard + llm_classifier | conversations complètes au FakeLLM — ✅ fait |
| P4 | orchestrator + branchement `chat_service` derrière `DIALOGUE_ENGINE` (`v1` défaut, `v2` opt-in) | test réel WhatsApp sur le numéro du marchand, comparaison test-chat — ✅ branché et testé e2e ; test WhatsApp réel : au marchand |
| P5 | bascule `v2` par défaut + **suppression** de l'ancien chemin | zéro code mort (règle du projet) |

Chaque phase : commitée, testée, démontrable. Le bot en production ne casse jamais.

## 13. Hors périmètre (explicitement)

- Migration Postgres / pool de connexions (chantier séparé, déjà identifié).
- Multi-photos par produit (le modèle n'a qu'une `image_path` ; « d'autres photos »
  est honoré honnêtement — variantes ou renvoi — en attendant cette évolution).
- Refonte du module `merchant_commands` (sain), du bridge, du dashboard.
- TTS/transcription/recherche visuelle (conservés tels quels, branchés en amont).

## 14. Risques et parades

- **Régression de comportement à la bascule** → drapeau + corpus de scénarios + période
  de double-run sur le numéro du marchand (P4) avant défaut (P5).
- **Catalogue d'intentions incomplet** → `UNCLEAR` route vers le classifieur LLM puis,
  en dernier recours, une réponse de clarification ; chaque manque observé devient une
  règle + un test (boucle d'amélioration).
- **Latence du classifieur** → appelé seulement sur l'ambigu, timeout court, dégradation
  vers règles seules.
