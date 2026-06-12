# REFERENCE.md — Index maître de la migration KALGA

> Dossier de référence maître pour les agents exécuteurs. Compile les 10 fichiers de
> `plans/reference/` + l'ADR `000-decisions-and-architecture.md` + le `README.md`.
> But : avant d'exécuter un plan `00X`, savoir **quels fichiers de référence lire**, **quelles
> décisions sont verrouillées**, et **quels GATES interactifs** remonter au proprio.
>
> Compilé le 2026-06-12. Sources stampées au commit `1e28bf5` (2026-06-11).

---

## 0. TL;DR — ordre d'exécution + fichiers de référence par plan

| Plan | Titre | Réf. principales à lire | GATE interactif ? |
|------|-------|-------------------------|-------------------|
| 001 | Scaffold `kalga-web` + init Convex | `tanstack-start`, `convex-core` (§6 login), `shadcn-tailwind` | **OUI — login Convex** (1re fois OAuth navigateur) |
| 002 | Schéma Convex + seed | `codebase-schema`, `convex-core` (§1-3) | non |
| 003 | Better Auth Local Install (OTP WhatsApp) | `convex-better-auth`, `codebase-whatsapp-bridge`, `convex-core` | **OUI — test OTP nécessite le bridge `ready`** |
| 004 | Python → Convex (v2 only, audit) | `codebase-python-dataflow`, `convex-python-client`, `codebase-whatsapp-bridge`, `convex-core` (§4 scheduler) | non (clé interne) |
| 005 | Design IA par écran | `shadcn-tailwind` | gate de validation visuelle proprio |
| 006 | Dashboard marchand | `convex-better-auth` (withOrg), `tanstack-start` (§6), `shadcn-tailwind`, `testing-e2e` | non |
| 007 | Storefront `{slug}.kalga.app` | `tanstack-start` (§5), `vercel-tanstack` (§4), `testing-e2e` | non |
| 008 | Admin back-office | `convex-better-auth` (admin), `codebase-whatsapp-bridge`, `shadcn-tailwind` | non |
| 009 | Déploiement Vercel | `vercel-tanstack`, `convex-core` (§5-6) | **OUI — domaine wildcard Vercel + nameservers + DNS email** |

Détail de chaque ligne plus bas (§3 checklists, §4 gates).

---

## 1. Catalogue des fichiers de référence (10)

Chaque entrée : ce qu'il contient + les pièges les plus mordants.

### `reference/tanstack-start.md`
Patterns d'exécution TanStack Start v1.x (React 19, Vite, Nitro, Vercel). Routing fichier-based,
`shellComponent`, loaders/SSR (`ssr: true|'data-only'|false`), server routes (`Route + server.handlers`),
résolution tenant par Host header, scoping des providers à `/app/*`, env vars `VITE_*` vs `process.env`.
- **Pièges clés** : (1) exporter **`getRouter`** pas `createRouter` (sinon `entries.routerEntry.getRouter is not a function`) ; (2) ordre plugins Vite **`tanstackStart()` AVANT `viteReact()`** ; (3) un fichier route sans export `Route` est **ignoré silencieusement** ; (4) providers Convex/auth **JAMAIS** dans `__root.tsx` (casse l'hydratation des pages publiques) ; (5) lire **`x-forwarded-host`** d'abord (Vercel) pour le tenant.

### `reference/convex-core.md`
Cœur Convex : `defineSchema`/`defineTable`, validators `v.*`, index standard/`searchIndex`/`vectorIndex`,
query/mutation/action + variantes `internal*`, `ctx.runQuery`/`runMutation`, `ctx.vectorSearch`,
scheduler `ctx.scheduler.runAfter/runAt`, crons, env vars Convex, modes `convex dev` non-interactif.
- **Pièges clés** : (1) `ctx.db` **n'existe pas** dans une action → `ctx.runQuery/runMutation` ; (2) `_id`/`_creationTime` auto, ne pas les déclarer ; (3) vector search **uniquement en action** ; (4) `convex dev` (watch) ne sort jamais → **toujours `--once`** pour un agent ; (5) `_generated/` doit exister avant que TS compile ; (6) `convex` ESM → `ssr.noExternal`.

### `reference/convex-better-auth.md`
`@convex-dev/better-auth` **0.10+ en LOCAL INSTALL** (obligatoire car `organization`+`admin` non
supportés par l'install NPM par défaut). API actuelle : `createClient` + `authComponent.adapter(ctx)`,
`betterAuth` depuis **`better-auth/minimal`**, `registerRoutes(http, createAuth, {cors:true})`,
plugins `organization`/`admin`/`phoneNumber`/`convex` (en dernier), `definePayload` →
`activeOrganizationId`, `withOrg` helper, sender OTP, proxy react-start.
- **⚠ Divergence importante** : ce fichier dit **explicitement** que l'ancienne rule globale
  `convex-better-auth-setup.md` est **périmée** (elle décrit `convexAdapter`, `betterAuth` non-minimal,
  mount HTTP manuel). **Suivre CE fichier, pas l'ancienne rule.** Or le plan 003 référence encore la
  rule globale comme « pattern de référence » → en cas de conflit, **ce fichier gagne** (plus récent).
- **⚠ Conflit OTP avec le bridge** : ce fichier propose `POST ${WHATSAPP_BRIDGE_URL}/api/send-otp`,
  payload `{to, text}`, header `x-kalga-internal`. **C'est un exemple générique, PAS l'endpoint réel.**
  Le vrai endpoint est dans `codebase-whatsapp-bridge.md` : `POST /send`, payload
  `{merchant_phone, to, message}`, header `X-Internal-Key`. **Utiliser le vrai (voir §4 gate OTP).**
- **Autres pièges** : (1) `convex({})` doit être le **dernier** plugin ; (2) re-générer
  `generatedSchema.ts` après chaque ajout de plugin ; (3) `convexSiteUrl` en **`.site`** pas `.cloud` ;
  (4) `signIn`/`signOut`/`setActive` → **reload** (JWT cache) ; (5) `convex/betterAuth/auth.ts` ne
  contient QUE `export const auth`.

### `reference/convex-python-client.md`
Client Python `convex` (PyPI `convex`, pas `convex-py`). `ConvexClient(url)`, query/mutation/action
par nom `"module:export"`, args = dict unique, `set_admin_auth(deploy_key)` pour le server-to-server,
`ConvexError.data`, conversions de types, subscriptions.
- **Pièges clés** : (1) URL = **`.convex.cloud`** (pas `.site`) ; (2) client **synchrone/WebSocket** →
  instancier **un seul** au lifespan FastAPI, wrapper en `asyncio.to_thread` dans le code async ;
  (3) un `int` Python part en **Float64** (utiliser `ConvexInt64` pour les vrais bigint) ;
  (4) `set_admin_auth` = la voie server-to-server (deploy/admin key, jamais committée).

### `reference/vercel-tanstack.md`
Déploiement Vercel via Nitro (Build Output API v3, `.vercel/output/`). Domaine wildcard
`*.kalga.app` + apex + `app.`, résolution tenant SSR par `x-forwarded-host`, env vars par
environnement, build off-prod (CI Vercel), `npx convex deploy --cmd 'pnpm build'`.
- **Pièges clés** : (1) **Output Directory laissé vide** (Nitro écrit `.vercel/output/`, un override casse le SSR) ; (2) **Root Directory = `kalga-web`** si front en sous-dossier ; (3) wildcard SSL **exige les nameservers Vercel** (`ns1/ns2.vercel-dns.com`) — un simple CNAME ne suffit pas ; (4) bascule nameservers ⇒ **re-créer MX/TXT email** sinon l'email casse ; (5) secrets **jamais** préfixés `VITE_` ; (6) `VITE_*` figée au build (rebuild pour changer) ; (7) `ConvexHttpClient` instancié **par requête** en SSR (pas singleton, fuite tenant).

### `reference/shadcn-tailwind.md`
shadcn/ui 3.x + Tailwind v4 dans TanStack Start. Config Tailwind **en CSS** (`@theme`, pas de
`tailwind.config.js`), couleurs **OKLCH**, `tw-animate-css`, `components.json`, stratégie
« 1 accent + monochrome » (modifier `--primary`+`--ring`, pas `--accent`), dark mode par classe.
- **Pièges clés** : (1) CLI = **`shadcn`** pas `shadcn-ui` ; (2) Tailwind v4 = `@import "tailwindcss";` (pas les 3 `@tailwind`) ; (3) couleurs **OKLCH** (pas HSL `0 0% 98%`) ; (4) `components.json` → `tailwind.config: ""` + `css` pointe le vrai fichier ; (5) alias `@` requis dans `vite.config.ts` **ET** `tsconfig.json` ; (6) pour l'accent KALGA (vert `#16a34a` ≈ `oklch(0.627 0.17 149)`) modifier **`--primary`** PAS `--accent` sémantique.

### `reference/testing-e2e.md`
Stratégie tests : Playwright (E2E), Vitest (unit FE), convex-test (backend Convex), pytest (FastAPI).
Config `webServer`, web-first assertions (auto-wait), flows OTP (3 stratégies : OTP déterministe
`TEST_MODE`, endpoint test-only, mock réseau), convex-test (`edge-runtime`, `import.meta.glob` modules,
`finishAllScheduledFunctions`), CI GitHub Actions.
- **Pièges clés** : (1) `playwright install --with-deps chromium` obligatoire (sinon `Executable doesn't exist`) ; (2) **jamais `waitForTimeout`** (flaky) → assertions auto-wait ; (3) `page.route` enregistré **avant** `goto` ; (4) convex-test **exige `environment: 'edge-runtime'`** + `@edge-runtime/vm` + 2e arg `modules` ; (5) scheduler testé avec fake timers ; (6) **OTP réel impossible en CI** → `KALGA_TEST_MODE` + OTP déterministe ; (7) aligner le port `webServer.url` sur le vrai port `pnpm dev`.

### `reference/codebase-schema.md`
Schéma SQLite source (17 tables métier, `users`/`active_sessions` exclues → Better Auth). Pour
chaque table : colonnes, types, FK, enums avec **valeurs réelles**, index. C'est la **source de
vérité** pour modéliser `convex/schema.ts` (plan 002).
- **Pièges clés** : (1) `products.embedding` = BLOB CLIP → **exclure de tout JSON** ; en Convex devient `v.optional(v.array(v.float64()))` ; (2) `stock_quantity = -1` = **illimité** (PAS rupture ; rupture = `0`) ; (3) `pending_delivery`/`pending_pickup` sont des états **VIVANTS** (vente conclue mais conv active) ; (4) vente comptabilisée = `status = 'completed'` ; (5) `storefront_orders.status` n'a **pas** de whitelist (seul `new` garanti) ; (6) `activation_codes.created_by` / `admin_audit_logs.admin_user_id` → FK vers `users` Better Auth.

### `reference/codebase-python-dataflow.md`
Cartographie complète de la persistance Python + hot-path chat pour la réécriture Convex (plan 004).
Façade `db.py` + 13 repos (méthodes + lignes), hot-path `chat_service.handle_incoming_message`
(étapes + appels DB), toggle v1/v2 (comment supprimer v1 proprement), scheduler 60s + race condition,
settings à migrer.
- **Pièges clés** : (1) **principe directeur** : regrouper les ~10-15 appels DB séquentiels en **fonctions Convex grossières** (`chat.getContext` query + `chat.commitTurn` mutation atomique), pas 13 appels fins ; (2) **v2 only** : `dialogue/engine.py` reste, v1 (`conversation_ai.py`, `conversation_engine.py`, tools, `_execute_tool`) **supprimé** ; (3) garder l'**aval commun** (notifications, follow-ups, auto-learn) indépendant du moteur ; (4) la **race SELECT-then-INSERT** des follow-ups → résolue par atomicité de mutation Convex ; (5) garder le client DeepSeek brut, supprimer le reste de v1 ; (6) `engine.py` retourne `None` sur exception → en Convex, prévoir une **réponse de secours déterministe**.

### `reference/codebase-whatsapp-bridge.md`
Bridge WhatsApp (Node/Baileys, port 3001) + ingestion. **Endpoint d'envoi réel** (OTP), verrouillage
`/api/chat/incoming`. État au 2026-06-12.
- **Faits clés (autoritatifs)** : (1) envoi = **`POST http://localhost:3001/send`** (à la racine, PAS `/api/send`), payload `{merchant_phone, to, message}`, header **`X-Internal-Key`** ; (2) le bridge **protège DÉJÀ** ses POST par `X-Internal-Key` (skip si clé vide = mode dev) ; (3) le maillon faible est **côté API** : `/api/chat/incoming` n'a **aucune** vérif de clé → à verrouiller (plan 004) ; (4) le bridge renvoie **503** si la session émettrice n'est pas `ready` → l'OTP échoue si le marchand n'a pas scanné le QR ; (5) réutiliser `whatsapp_client.send_message()` (injecte déjà le header) pour l'OTP.

---

## 2. Décisions verrouillées (000) pertinentes par plan

Rappel des décisions D1–D12 de `000-decisions-and-architecture.md`, mappées aux plans qui les portent.

| Décision | Résumé | Plans concernés |
|---|---|---|
| **D1** Frontend = TanStack Start (réécriture, Nuxt = réf visuelle) | nouveau dossier `kalga-web/`, ne pas migrer le Nuxt | 001, 005, 006, 007, 008 |
| **D2** 3 surfaces, 1 app, routées par hostname | `kalga.app`=landing, `app.`=dashboard+`/admin`, `{slug}.`=storefront | 001, 006, 007, 008, 009 |
| **D3** Convex = SoT unique, SQLite abandonné, Python écrit dans Convex | conversations live au dashboard | 002, 004, 006 |
| **D4** Better Auth single-store **Local Install** (`organization`+`admin`) | conforme à la divergence du fichier `convex-better-auth.md` | 003, 006, 008 |
| **D5** Login marchand = **téléphone + OTP WhatsApp** v1, email+pwd opt-in settings | OTP via le bridge Baileys | 003, 006 |
| **D6** v1 = 1 proprio = 1 org (plugin `organization` quand même) | `activeOrganizationId` dans le JWT | 003, 006 |
| **D7** Hébergement backend reporté (Python/bridge en LOCAL) | front→Vercel, DB→Convex ; Oracle Cloud pressenti | 009 (front seul), 004 (note) |
| **D8** Stratégie ML Python reportée (torch/whisper/CLIP locaux) | allègement décidé à l'hébergement | 004 (ne pas toucher ML) |
| **D9** Python intégré à Convex dès phase 1 (local → Convex cloud) | pas d'étape SQLite jetable | 004 |
| **D10** Aucune migration de données — seed démo | KALGA non lancé, data = dev jetable | 002 (seed) |
| **D11** Périmètre v1 : landing + dashboard + storefront + admin, **abonnement par code d'activation** (paiement in-app exclu) | Wave/OM reporté | 006, 008 |
| **D12** Maquettes : références IA → validation → shadcn/ui ; **pas d'AI slop, 1 accent + monochrome, mobile-first, touch ≥ h-11, UI en français, code en anglais, pas d'em dash** | règles design KALGA | 005, 006, 007, 008 |

**Findings d'audit** (commit `1e28bf5`) — tous **conservés et dissous par la migration**, pas oubliés :
- SEC-01/03 (IDOR mutations/conversations) → **dissous** par scoping org `withOrg` (003/006).
- SEC-02 (`debug_token` sur forgot-password) → **supprimé**, reset géré par Better Auth (003).
- `/api/chat/incoming` non auth → **verrouillé** par `INTERNAL_API_KEY` (004).
- SEC-04 (CORS wildcard) → `debug=false` prod + origines explicites (004/009).
- SEC-05 (import CSV sans limite) → cap de taille (006/008).
- #5 double moteur v1/v2 → **v2 only** (004). #6 zéro test intégration ChatService → tests (004).
- #7 race scheduler follow-up → **mutation/scheduler Convex atomique** (004).
- #8 god files, quick wins (bcrypt dupliqué, `.backup`, `except: pass`) → nettoyage (004).

---

## 3. Checklist « à lire avant d'exécuter le plan 00X »

Chaque plan a son **Drift check** (commande git) et son **toolkit ctx7** dans le fichier de plan ;
ci-dessous on pointe les fichiers de référence et les points de vigilance transverses.

### Avant 001 (scaffold)
- Lire : `tanstack-start.md` (§0-2, §6-9), `convex-core.md` (§0, §6 modes login), `shadcn-tailwind.md` (§1-2) si on pose le design system tôt.
- Vérifs : `getRouter` exporté, `shellComponent` complet, `tanstackStart()` avant `viteReact()`, providers PAS dans `__root.tsx`, `schema.ts` minimal (le métier = 002).
- **GATE** : `convex dev` 1re fois demande un **login OAuth navigateur** (voir §4).

### Avant 002 (schéma)
- Lire : `codebase-schema.md` (intégral — source de vérité colonnes/enums/index), `convex-core.md` (§1-3).
- Vérifs : 17 tables métier (PAS `users`/`active_sessions`), chaque table porte `merchantId` + index `by_merchant`, enums = **valeurs réelles** du codebase-schema, `products.imageEmbedding: v.optional(v.array(v.float64()))` (PAS de BLOB, PAS d'index vectoriel encore), `merchants` a `slug` unique + `organizationId` optionnel.
- Note : `stock_quantity = -1` = illimité ; `pending_*` = états vivants.

### Avant 003 (Better Auth)
- Lire : **`convex-better-auth.md`** (intégral, c'est LE fichier maître — prime sur la rule globale), `codebase-whatsapp-bridge.md` (§1 endpoint OTP réel), `convex-core.md` (§5 env).
- Vérifs : Local Install (pas NPM default), `definePayload.activeOrganizationId`, `convex({})` en dernier, `withOrg`, `provisionMerchantOrg` (org + merchant + slug unique).
- **Sender OTP** : utiliser le **vrai** endpoint `POST /send` `{merchant_phone, to, message}` + `X-Internal-Key` (PAS l'exemple `/api/send-otp` du fichier better-auth — voir §4 gate).
- **GATE** : le test du flow OTP (Step 8) exige le **bridge lancé + session WhatsApp `ready`** (voir §4).

### Avant 004 (Python → Convex)
- Lire : `codebase-python-dataflow.md` (intégral), `convex-python-client.md`, `codebase-whatsapp-bridge.md` (§2-3 verrouillage `/incoming`), `convex-core.md` (§4 scheduler/crons, §3 internal*).
- Vérifs : fonctions grossières gardées par `internalKey`, `chat.getContext` + `chat.commitTurn` atomique, **v1 supprimé** (`grep conversation_ai` vide), scheduler Convex (plus de `sleep(60)`), `/incoming` 401 sans header, bridge envoie `X-Internal-Key` (1-2 lignes), quick wins nettoyés, ≥3 tests d'intégration.
- Dépend de **002 seulement** (pas 003) — Python utilise une clé de déploiement, pas une session.
- **INTERDIT** : `migrate:fresh`/wipe DB sans accord explicite (règle proprio).

### Avant 005 (design)
- Lire : `shadcn-tailwind.md` (§4 tokens, stratégie 1 accent + monochrome).
- Gate de validation visuelle proprio (D12) avant de coder 006/007/008.

### Avant 006 (dashboard)
- Lire : `convex-better-auth.md` (§10 client, §12 withOrg), `tanstack-start.md` (§6 providers scopés `/app/*`), `shadcn-tailwind.md` (§3 composants : sidebar, input-otp, form, table), `testing-e2e.md` (§6.1-6.2 specs).
- Dépend de 003 + 004 + 005. Conversations **live** = `useQuery` Convex (bénéfice D3).
- Providers Convex/Better Auth scopés `/app/*`, jamais `__root.tsx`.

### Avant 007 (storefront)
- Lire : `tanstack-start.md` (§5 résolution tenant par Host), `vercel-tanstack.md` (§4 SSR tenant + `x-forwarded-host`), `testing-e2e.md` (§6.3 specs storefront).
- Dépend de 002 + 005. Pas de provider auth (page publique). Sous-domaines réservés blacklistés (`app`, `www`, `api`, `admin`). `ConvexHttpClient` par requête.

### Avant 008 (admin)
- Lire : `convex-better-auth.md` (plugin `admin`), `codebase-whatsapp-bridge.md` (statut WA par marchand), `shadcn-tailwind.md`.
- Dépend de 003 + 005. Émission codes d'activation (D11), import CSV avec cap (SEC-05), audit logs.

### Avant 009 (Vercel)
- Lire : `vercel-tanstack.md` (intégral), `convex-core.md` (§5 env, §6 deploy key/prod).
- Dépend de 006 + 007 + 008. Build off-prod (CI Vercel). `debug=false`, origines CORS explicites (SEC-04).
- **GATE** : configuration **domaine wildcard Vercel + nameservers + re-création DNS email** (voir §4).

---

## 4. GATES interactifs à remonter au proprio

Le workflow d'exécution **ne peut pas franchir seul** ces points — chacun exige une action humaine,
un compte, ou un secret. À chaque gate : **STOP et reporter au proprio** avec l'instruction exacte.

### GATE-1 — Login Convex (plan 001, et tout `convex dev`/`deploy`)
- **Quoi** : la 1re exécution de `npx convex dev` demande un **login OAuth navigateur** + création de projet. Impossible sans compte (sauf mode anonyme limité).
- **Options** (cf. `convex-core.md` §6) :
  - Setup initial dev : `npx convex dev` (login navigateur) — **action proprio**.
  - CI/agent avec projet existant : `CONVEX_DEPLOY_KEY="..." npx convex dev --once` (pas de login) — **le proprio fournit la deploy key**.
  - Agent/VM isolée sans compte : `CONVEX_AGENT_MODE=anonymous npx convex dev --once` (backend local, permissions limitées).
- **À remonter** : « Le scaffold Convex exige soit un login navigateur (toi), soit une `CONVEX_DEPLOY_KEY` d'un projet existant. Laquelle ? » Le plan 001 liste déjà ça en STOP condition.

### GATE-2 — Test OTP WhatsApp (plan 003, Step 8 ; aussi tests E2E)
- **Quoi** : valider le flow OTP de bout en bout exige le **bridge `kalga-whatsapp` lancé** ET une **session WhatsApp `ready`** (QR scanné). Sinon le bridge renvoie **503** et l'OTP n'arrive jamais (cf. `codebase-whatsapp-bridge.md` piège §1).
- **Sous-gate (conflit endpoint)** : le code du sender OTP doit cibler le **vrai** endpoint `POST /send` `{merchant_phone, to, message}` + `X-Internal-Key`, **pas** l'exemple `/api/send-otp` `{to, text}` `x-kalga-internal` du fichier `convex-better-auth.md` (§11, générique). Si l'exécuteur suit aveuglément le better-auth ref, l'OTP **échouera silencieusement**. → reporter la correction.
- **Sous-gate (env secret)** : poser `WHATSAPP_BRIDGE_URL` + le secret partagé (`INTERNAL_API_KEY`/`WA_BRIDGE_SECRET`) côté Convex (`npx convex env set ...`) — **valeurs fournies par le proprio**, jamais committées.
- **À remonter** : « Pour tester l'OTP, lance le bridge et scanne le QR (session `ready`), et confirme la valeur de `INTERNAL_API_KEY`. En CI, on bascule sur OTP déterministe `KALGA_TEST_MODE` (testing-e2e §3.1). »

### GATE-3 — Domaine Vercel (plan 009)
- **Quoi** : le wildcard `*.kalga.app` (storefront multi-tenant) **exige les nameservers Vercel** (`ns1/ns2.vercel-dns.com`) pour le SSL auto par sous-domaine — un simple CNAME ne suffit pas (cf. `vercel-tanstack.md` §2.1).
- **Conséquences humaines** :
  - Basculer les nameservers chez le **registrar** (Namecheap/Gandi/…) — **action proprio**.
  - **Re-créer tous les enregistrements DNS existants** (MX email, TXT SPF/DKIM) dans Vercel, sinon l'**email casse** — **action proprio**.
  - Ajouter `kalga.app`, `app.kalga.app`, `*.kalga.app` au projet Vercel ; vérifier les certs.
- **Sous-gate (login Vercel + deploy key)** : `vercel login` (compte proprio) + `CONVEX_DEPLOY_KEY` en env Vercel production pour `npx convex deploy --cmd 'pnpm build'`.
- **À remonter** : « Le déploiement prod exige (a) un login Vercel, (b) la bascule des nameservers `kalga.app` vers Vercel + re-création des MX/TXT email, (c) la `CONVEX_DEPLOY_KEY` prod. Tout ça est manuel côté toi. »

### GATE-4 (mineur) — Validation visuelle design (plan 005)
- **Quoi** : D12 impose que les références IA par écran soient **validées par le proprio** avant de coder l'UI (006/007/008). Gate de validation, pas technique.
- **À remonter** : présenter les références, attendre l'OK avant de coder.

---

## 5. Notes transverses (s'appliquent à plusieurs plans)

- **pnpm exclusivement** (jamais npm), commits **sans `Co-Authored-By`**, **commit seulement les fichiers du scope** (règles proprio). Personal project KALGA → deploy direct (pas de PR imposée), mais les plans 001-004 demandent des branches `migration/00X`.
- **Secrets** : jamais committés, jamais préfixés `VITE_`. Côté Convex via `npx convex env set` ; côté front via `.env.local` (gitignoré) ; côté Vercel via env scopées par environnement.
- **ctx7 avant de coder** (training data périmé) : chaque plan liste ses requêtes ctx7. Les fichiers de référence ici sont des snapshots juin 2026 — si ctx7 montre une API divergente, **reporter avant de coder** (STOP condition standard).
- **Ne pas toucher** hors scope : `kalga-frontend/` (Nuxt, réf visuelle), `dashboard/`, `storefront/` (anciens statiques) restent intacts jusqu'à 009.
- **`migrate:fresh`/wipe DB / `git reset --hard` / force-push** : INTERDITS sans accord explicite (règles proprio multi-agent-git-safety + no-migrate-fresh).
- **Conflit de source à connaître** : sur Better Auth, **`reference/convex-better-auth.md` prime** sur la rule globale `convex-better-auth-setup.md` (le fichier le dit explicitement). Sur l'endpoint OTP, **`reference/codebase-whatsapp-bridge.md` prime** sur l'exemple générique de `convex-better-auth.md`.

---

## 6. Suffisance du contexte par plan (verdict) + STATUT RÉEL (2026-06-12)

| Plan | Contexte suffisant ? | **Statut réel d'exécution** | Réserve / reste à faire |
|------|----------------------|-----------------------------|-------------------------|
| 001 | **Oui** (modulo GATE-1 login Convex) | **DONE** | scaffold + init Convex faits (déploiement `dev:rugged-albatross-514`) |
| 002 | **Oui** — `codebase-schema.md` couvre tout | **DONE** | 17 tables Convex + 38 index + seed idempotent + queries de lecture ; drift `connection.py` = 0 |
| 003 | **Oui, avec vigilance** | **PARTIAL (GATE-2)** | code Local Install complet, sender OTP sur **vrai** endpoint `/send` ; drift versions (0.12.3 / better-auth 1.6.16) ; reste : test OTP live (Step 8) bloqué par session émettrice + `KALGA_OTP_SENDER_PHONE` |
| 004 | **Oui** — `codebase-python-dataflow.md` exhaustif | **PARTIAL (gate humain)** | fonctions Convex + client Python + verrou `/incoming` + quick wins + 7 tests OK ; reste : bascule hot-path writes vers `commitTurn`, suppression v1, retrait SQLite, rewrite `followup_service.py` Python (le STOP #1/#2/#3 a été honoré) |
| 005 | **Partiel** — tokens OK, contenu = GATE-4 | **REJETÉ / à refaire** (via `/ultrathink`) | design non validé ; plan à reprendre |
| 006 | **Cadré, pas détaillé** | **TODO** | plan à développer ; dépend de 003/004/005 |
| 007 | **Cadré** — réfs tenant/SSR présentes | **TODO** | plan à développer ; blacklist sous-domaines à confirmer |
| 008 | **Cadré** — réfs admin/bridge présentes | **TODO** | plan à développer ; cap import CSV à dimensionner |
| 009 | **Oui pour la mécanique** | **TODO** | bloqué par GATE-3 (DNS/nameservers/login manuelles proprio) |

**Synthèse exécution** : **001-002 = DONE**. **003-004 = PARTIAL** (code livré et vérifié, bloqués
par des gates humains documentés ci-dessous). **005 = à refaire**. **006-009 = TODO** (cadrés).

### Gates restants découverts pendant l'exécution (à remonter au proprio)

1. **GATE-2 étendu (003)** : test OTP live exige une **session WhatsApp CENTRALE KALGA émettrice**
   (`ready`) + poser `KALGA_OTP_SENDER_PHONE` côté Convex. Décision proprio : **quel numéro/session
   centrale émet les OTP signup**. `INTERNAL_API_KEY` déjà posée.
2. **GATE-4bis nouveau (004) — bascule write-path** : avant de basculer les écritures hot-path vers
   Convex et de supprimer SQLite/v1, il faut (a) fournir une `CONVEX_DEPLOY_KEY` OU confirmer le
   modèle **public+arg-secret `internalKey`** comme définitif, ET (b) ajouter au schéma Convex
   `conversations` les champs manquants (`selectedVariantId`, + champs joints `productName`/
   `productCode`/`price` que le moteur v2 consomme), ET (c) un **smoke chat live** (DeepSeek key +
   bridge) pour valider le rewiring. Tant que ce gate n'est pas franchi, v1 + `followup_service.py`
   SQLite restent en place.
3. **Drift versions Better Auth (003)** : reporté, **non bloquant** — `better-auth@1.5.3` (référence)
   est incompatible avec le composant 0.12 ; pin réel = `1.6.16`. API structurelle inchangée.

Les gates pré-existants **GATE-1** (login Convex), **GATE-3** (domaine Vercel), **GATE-4** (validation
design 005) restent valides.
