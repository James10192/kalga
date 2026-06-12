# Plan 004 — Réécriture du backend Python : SQLite → Convex (fonctions grossières, v2 only)

> **Executor instructions** : plan volumineux (effort L). Suivre les étapes dans l'ordre,
> vérifier chaque commande, committer par étape (le codebase doit rester lançable entre étapes).
> STOP et reporter aux conditions « STOP ». Mettre à jour la ligne 004 de `plans/README.md`.
>
> **Drift check** : `git diff --stat 1e28bf5..HEAD -- kalga-api/`
> Le backend Python évolue vite ; si les fichiers ci-dessous ont changé, relire avant d'agir.
>
> **Doc à jour** : `npx -y ctx7 library "convex python client" "call query mutation action from python"` puis `ctx7 docs <id> "ConvexClient setup auth"`.

## Status
- **Priority** : P1
- **Effort** : L (multi-jours)
- **Risk** : HIGH (réécrit le cœur data du backend + le hot path IA)
- **Depends on** : 002 (schéma Convex + queries de base). N'a PAS besoin de 003 (Python utilise une clé interne, pas une session Better Auth).
- **Category** : migration / tech-debt / security
- **Planned at** : commit `1e28bf5`, 2026-06-11

## Why this matters

Décision D3 : Convex = source de vérité unique, SQLite abandonné. Le Python doit lire/écrire
Convex, y compris pendant le chat (→ conversations live au dashboard). Ce plan porte aussi
plusieurs findings d'audit : supprime le double moteur v1/v2 (#5/#6), réécrit le scheduler
follow-up atomiquement (#7), verrouille `/api/chat/incoming` (sécurité), et nettoie les quick wins.

**Principe directeur (NON négociable)** : ne PAS porter les 13 repos SQLite en 13 appels réseau
fins (N round-trips sur le hot path IA). Définir un **petit jeu de fonctions Convex grossières**
appelées par Python ; les opérations multi-écritures deviennent **atomiques** côté Convex.

## Current state

- `kalga-api/` FastAPI (port 8001). Accès DB via `app/database/db.py` (façade) + 13 repos sous
  `app/database/repositories/`. Connexion SQLite : `app/database/connection.py`.
- Hot path : `app/services/chat_service.py` (1205 LOC) → `app/services/ai/conversation_ai.py`
  (v1) **et** `app/services/dialogue/engine.py` (v2). Toggle `settings.dialogue_engine == "v2"`
  dans `chat_service.py:237-328`. **v2 est le défaut** (PR #104).
- Scheduler : `app/services/followup_service.py` (boucle 60s, race condition SELECT-puis-INSERT lignes 90-111).
- Ingestion : `app/routers/chat.py:29-42` `POST /incoming` **non authentifié** (rate-limit only).
- Config : `app/core/config.py` (settings singleton). Clé interne : `INTERNAL_API_KEY` déjà prévue (cf. `validate_settings`).
- Quick wins : `requirements.txt` ligne `bcrypt==4.2.0` dupliquée ; `app/routers/merchant_commands.py.backup` orphelin ; `except: pass` muets (ex. `chat_service.py:165`).

Convex côté `kalga-web/convex/` (plans 001/002) : schéma + queries de lecture de base.

## Contrat des fonctions Convex grossières (à créer dans `kalga-web/convex/`)

Chaque fonction prend un argument `internalKey: v.string()` validé contre `process.env.INTERNAL_API_KEY`
(garde server-to-server — Python n'a pas de session utilisateur). Lever si invalide.

| Fonction | Type | Rôle (remplace quels repos) |
|---|---|---|
| `internal.getMerchantByPhone` | query | merchant_repo.get_by_phone (persona, slug, id) |
| `internal.checkProduct` | query | product_repo (lookup code, stock, variantes, embedding) |
| `internal.listProductsForTools` | query | product_repo (inventaire pour les tools IA) |
| `internal.recordTurn` | mutation | **atomique** : upsert conversation + insert message(s) + maj statut (remplace conversation_repo + une partie de chat_service) |
| `internal.upsertMemory` | mutation | client_history (LTM) + knowledge_base |
| `internal.decrementStock` | mutation | product_repo.decrement_stock (atomique, log si dépassement) |
| `internal.scheduleFollowup` | mutation | followup_service (utilise le **scheduler Convex** `ctx.scheduler.runAfter`) |
| `internal.recordStockEvent` / `internal.recordAnalytics` | mutation | stats |

(Adapter la liste après lecture réelle des repos ; garder le grain grossier.)

## Commands you will need

| But | Commande | Attendu |
|-----|----------|---------|
| Doc | `npx -y ctx7 docs <convex-python-id> "<sujet>"` | snippets |
| Python | `py -m pytest` (depuis `kalga-api/`) | tests passent |
| Lancer API | `uvicorn app.main:app --port 8001 --reload` | démarre sans erreur |
| Push Convex | depuis `kalga-web/` : `pnpm exec convex dev --once` | OK |
| Smoke chat | `POST /api/chat/incoming` avec header `INTERNAL_API_KEY` | réponse bot + message visible dans Convex |

(Windows : `py`, pas `python3`. UTF-8 : `PYTHONIOENCODING=utf-8`.)

## Scope

**In scope** :
- `kalga-web/convex/internal.ts` (+ découpage par domaine si > 250 LOC : `internal/chat.ts`, `internal/inventory.ts`, `internal/memory.ts`) — les fonctions grossières
- `kalga-api/app/infrastructure/convex_client.py` (nouveau) — wrapper du client Python Convex
- `kalga-api/app/database/db.py` + `app/database/repositories/*` — réécrits pour déléguer à Convex (ou remplacés par un module data Convex-backed)
- `kalga-api/app/services/chat_service.py` — câblage Convex + **suppression du chemin v1**
- `kalga-api/app/services/ai/conversation_ai.py` + `conversation_engine.py` — **supprimés** (v1)
- `kalga-api/app/services/followup_service.py` — réécrit en déclencheur du scheduler Convex
- `kalga-api/app/routers/chat.py` — `/incoming` exige `INTERNAL_API_KEY`
- `kalga-api/requirements.txt` (dédup bcrypt, ajout `convex`), suppression `app/routers/merchant_commands.py.backup`
- tests sous `kalga-api/tests/`

**Out of scope** :
- UI front (plans 006+).
- Better Auth (plan 003) — Python n'y touche pas.
- Allègement ML / hébergement (D7/D8) — Python garde torch/whisper/CLIP en local ici.
- `kalga-whatsapp/` (le bridge continue d'appeler `/incoming`, on ajoutera juste l'envoi du header `INTERNAL_API_KEY` côté bridge — **1 ligne**, voir Step 7).

## Steps

### Step 1 — Lire l'existant
Lire `db.py`, les 13 repos, `chat_service.py`, `followup_service.py`, `core/config.py`. Cartographier
quels repos sont appelés sur le hot path vs hors-ligne. Confirmer le toggle v1/v2.
**Verify** : (lecture) — liste des points d'appel DB par fonction grossière cible.

### Step 2 — Fonctions Convex grossières (lecture d'abord)
Créer `internal.getMerchantByPhone`, `checkProduct`, `listProductsForTools` (queries) avec garde
`internalKey`. Pousser.
**Verify** : `pnpm exec convex dev --once` → OK ; appel test via Python client renvoie le marchand `demo`.

### Step 3 — Client Python Convex
`app/infrastructure/convex_client.py` : singleton `ConvexClient(settings.convex_url)`, helpers
`query(name, args)` / `mutation(name, args)` injectant `internalKey=settings.internal_api_key`.
Ajouter `convex` à `requirements.txt`. `core/config.py` : ajouter `convex_url`.
**Verify** : `py -c "from app.infrastructure.convex_client import get_convex; print(get_convex())"` (depuis venv) → pas d'erreur ; `grep -q "^convex" requirements.txt && echo OK` → `OK`.

### Step 4 — Basculer les lectures
Réécrire les repos de **lecture** (merchant, product) pour déléguer aux queries Convex. Garder
les signatures publiques pour ne pas casser les appelants. Lancer l'API, vérifier qu'un GET
produits passe par Convex.
**Verify** : `uvicorn app.main:app --port 8001` démarre ; une lecture marchand/produit renvoie les données seedées Convex (pas SQLite).

### Step 5 — Fonctions d'écriture + bascule du chat
Créer `internal.recordTurn` (atomique), `upsertMemory`, `decrementStock`. Câbler `chat_service.py`
pour écrire via Convex. **Supprimer le chemin v1** (garder uniquement v2 `dialogue/engine.py`) :
retirer le toggle, supprimer `conversation_ai.py` + `conversation_engine.py`, nettoyer les imports.
**Verify** : `grep -rq "conversation_ai" app/ && echo BAD || echo OK` → `OK` ;
`POST /api/chat/incoming` (avec header) → réponse bot ; le message apparaît dans `convex data messages`.

### Step 6 — Scheduler follow-up atomique
Réécrire `followup_service.py` pour planifier via `internal.scheduleFollowup` (scheduler Convex
`ctx.scheduler.runAfter`), supprimant la boucle 60s et la race SELECT-puis-INSERT (audit #7).
**Verify** : programmer un follow-up → une seule entrée créée même sous appels concurrents (test) ;
plus de `while True: sleep(60)` dans `followup_service.py`.

### Step 7 — Verrouiller `/incoming` + header bridge
`chat.py:/incoming` (et `/incoming-media`) : exiger header `X-Internal-Key == settings.internal_api_key`,
sinon 401. Côté `kalga-whatsapp/`, ajouter l'envoi de ce header dans l'appel à `/incoming`
(modif minimale, 1-2 lignes, repérer le fetch existant).
**Verify** : `POST /incoming` sans header → 401 ; avec header → 200. `grep -q "X-Internal-Key" kalga-api/app/routers/chat.py && echo OK` → `OK`.

### Step 8 — Retirer SQLite + quick wins
Supprimer `connection.py` (aiosqlite) et toute init SQLite dans `main.py`/`db.py`. Dédupliquer
`bcrypt` dans `requirements.txt`. Supprimer `app/routers/merchant_commands.py.backup`. Remplacer
les `except: pass` muets repérés par `except Exception as e: logger.warning(...)`.
**Verify** : `grep -rq "aiosqlite" app/ && echo BAD || echo OK` → `OK` ;
`grep -c "bcrypt==4.2.0" requirements.txt` → `1` ; `ls app/routers/merchant_commands.py.backup 2>/dev/null && echo BAD || echo OK` → `OK`.

### Step 9 — Tests d'intégration
Écrire des tests d'intégration sur le chemin Convex-backed (audit #6) : message entrant →
`recordTurn` → message persisté ; négo simple ; deal agreed → statut. Mocker DeepSeek, pointer
Convex sur le déploiement de dev (ou convex-test).
**Verify** : `py -m pytest tests/ -k chat` → tous passent, ≥ 3 nouveaux tests.

## Test plan
- Tests d'intégration `tests/test_chat_convex.py` : happy path ingestion, négo, transition de statut, idempotence d'un `/incoming` rejoué.
- Test scheduler : pas de doublon de follow-up sous concurrence.
- Modèle : suivre un test existant du repo (`kalga-api/tests/`).

## Done criteria (toutes)

- [ ] Fonctions Convex grossières créées, gardées par `internalKey`, poussées sans erreur.
- [ ] `app/infrastructure/convex_client.py` + `convex` dans `requirements.txt` ; `convex_url`/`internal_api_key` dans config.
- [ ] Plus aucune référence à `aiosqlite`/`connection.py` ; SQLite retiré de `main.py`.
- [ ] **v1 supprimé** : `grep -rq "conversation_ai" app/` ne renvoie rien ; seul v2 subsiste.
- [ ] `followup_service.py` n'a plus de boucle `sleep(60)` ; planification via scheduler Convex.
- [ ] `/incoming` et `/incoming-media` exigent `X-Internal-Key` (401 sinon) ; bridge envoie le header.
- [ ] Quick wins : bcrypt dédupliqué, `.backup` supprimé, `except: pass` muets remplacés.
- [ ] `py -m pytest tests/ -k chat` passe avec ≥ 3 nouveaux tests d'intégration.
- [ ] `git status` : modifs limitées à `kalga-api/`, `kalga-web/convex/`, `kalga-whatsapp/` (1-2 lignes), `plans/`.
- [ ] Ligne 004 de `plans/README.md` → DONE.

## STOP conditions
- Le couplage data dans `chat_service.py`/`db.py` est bien plus enchevêtré que la carte du Step 1 (god files audit #8) → reporter un découpage avant de continuer plutôt que d'improviser.
- Le client Python Convex ne permet pas d'appeler les fonctions avec une garde par secret (API différente) → reporter le mécanisme d'auth server-to-server réel observé via ctx7.
- Supprimer v1 casse un chemin encore utilisé en prod-démo non couvert par v2 → STOP, lister le gap.
- Besoin de modifier `kalga-whatsapp/` au-delà de l'ajout du header → STOP.
- `migrate:fresh`/wipe DB ou toute opération destructive → **INTERDIT** sans accord explicite (règle proprio).

## Maintenance notes
- Après ce plan, Python tourne **en local** pointant sur Convex cloud (D9) ; l'hébergement (D7) et l'allègement ML (D8) restent à faire — ne pas toucher torch/whisper/CLIP ici.
- L'index vectoriel `products.imageEmbedding` (recherche visuelle Convex-native) peut remplacer CLIP-en-Python plus tard : à activer quand on allègera Python (renvoi vers ce plan).
- Reviewer : vérifier que chaque écriture Convex passe par une fonction gardée `internalKey` (jamais d'écriture client non scopée), et que le hot path fait peu d'appels grossiers (pas de N+1 réseau).
- god files `intent.py`/`chat_service.py` : allégés ici si l'occasion se présente, sinon dette suivie séparément.
