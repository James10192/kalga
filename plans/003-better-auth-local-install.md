# Plan 003 — Better Auth (Local Install) : OTP WhatsApp + org/admin + email opt-in

> **Executor instructions** : suivre étape par étape, vérifier chaque commande. STOP et
> reporter si une condition « STOP » survient. Mettre à jour la ligne 003 de `plans/README.md`.
>
> **Drift check** : `git diff --stat 1e28bf5..HEAD -- kalga-web/convex/`
> Si `convex/auth.ts` ou `convex/schema.ts` existent déjà autrement que décrit, comparer avant d'agir.
>
> **Doc à jour OBLIGATOIRE (règle proprio « use ctx7 »)** : avant de coder, lire la doc
> Convex Better Auth via ctx7 — `npx -y ctx7 docs /websites/labs_convex_dev_better-auth "local install organization admin phone plugin definePayload"`.
> Les versions/API du composant changent ; ne pas coder de mémoire.

## Status
- **Priority** : P1
- **Effort** : L
- **Risk** : MED (auth = surface sensible ; OTP couplé au bridge WhatsApp)
- **Depends on** : 001 (app + Convex), 002 (schéma `merchants`)
- **Category** : security / migration
- **Planned at** : commit `1e28bf5`, 2026-06-11

## Why this matters

L'auth marchand actuelle est nulle (téléphone en localStorage, aucune protection — findings
audit SEC-01/02/03). On la remplace par **Better Auth single-store sur Convex en Local Install**
(décision D4), avec login **téléphone + OTP WhatsApp** (D5), chaque marchand = **une org**
(D6), et un **plugin admin** pour le back-office. C'est le socle de sécurité de toute la v1 :
le scoping `organizationId` remplace les routes FastAPI non protégées.

## Current state

- `kalga-web/` (TanStack Start) + Convex initialisé (plan 001).
- `convex/schema.ts` modélise les tables métier, dont `merchants` avec `organizationId: v.optional(v.string())`, `slug`, `phone` (plan 002). **Les tables d'auth NE sont PAS dans schema.ts** — Better Auth les gère.
- Bridge WhatsApp `kalga-whatsapp/` expose un envoi de message (utilisé pour livrer l'OTP). **Lire** `kalga-whatsapp/src/api/` pour trouver l'endpoint d'envoi exact (ex. `POST /send`) et le port (3001) avant de câbler le sender OTP.

**Règle de référence (à respecter)** : la SOURCE MAÎTRE est **`plans/reference/convex-better-auth.md`**
(snapshot juin 2026, API actuelle 0.10+). Elle **PRIME** sur la rule globale
`~/.claude/rules/convex-better-auth-setup.md`, qui est **périmée** (elle décrit `convexAdapter`,
`betterAuth` non-minimal, mount HTTP manuel — ne PAS suivre). API actuelle à utiliser :
- `createClient` + `authComponent.adapter(ctx)` ; `betterAuth` importé de **`better-auth/minimal`**.
- `registerRoutes(http, createAuth, { cors: true })` pour monter `/api/auth/*` (pas de mount manuel).
- Plugins dans l'ordre, **`convex({})` en DERNIER**.
- **Local Install obligatoire** (le composant NPM ne supporte PAS `organization`/`admin`).
- `definePayload` DOIT injecter `activeOrganizationId` dans le JWT (sinon mutations multi-tenant « No active org »).
- `convexSiteUrl` en **`.site`** (pas `.cloud`) ; re-générer `generatedSchema.ts` après chaque ajout de plugin.
- `signIn`/`signOut`/`setActive` suivis d'un **reload** (cache JWT).

## Commands you will need

| But | Commande (depuis `kalga-web/`) | Attendu |
|-----|------|---------|
| Doc Better Auth | `npx -y ctx7 docs /websites/labs_convex_dev_better-auth "<sujet>"` | snippets à jour |
| Push Convex | `pnpm exec convex dev --once` | OK, pas d'erreur de schéma/validation |
| Set env Convex | `pnpm exec convex env set <KEY> <VALEUR>` | variable posée |
| Typecheck | `pnpm exec tsc --noEmit` | exit 0 |
| Build | `pnpm build` | exit 0 |

## Scope

**In scope** :
- `kalga-web/convex/auth.ts`, `kalga-web/convex/auth.config.ts`, `kalga-web/convex/convex.config.ts`, `kalga-web/convex/http.ts`
- `kalga-web/convex/lib/withOrg.ts`
- composants Better Auth Local Install (selon la doc ctx7 : dossier généré par l'install local)
- `kalga-web/src/lib/auth-client.ts`, `kalga-web/src/lib/auth-server.ts`, `kalga-web/src/routes/api/auth.$.ts`
- `kalga-web/convex/merchants.ts` — mutation `provisionMerchantOrg` (crée org + doc merchant au signup)
- `kalga-web/vite.config.ts` — ajouter `@convex-dev/better-auth` à `ssr.noExternal`
- `kalga-web/.env.example` — noms des nouvelles variables

**Out of scope** :
- UI de login/dashboard finale → plan 006 (ici, une page de test minimale suffit pour valider l'auth).
- Écritures chat/IA Python → plan 004.
- Modifier `kalga-whatsapp/` au-delà de l'**appel** à son endpoint d'envoi (ne pas refactorer le bridge).

## Steps

### Step 1 — Lire les références
Lire **`plans/reference/convex-better-auth.md`** (source maître, prime sur l'ancienne rule) +
**`plans/reference/codebase-whatsapp-bridge.md`** (§1 endpoint OTP réel). Confirmer via ctx7
(`/websites/labs_convex_dev_better-auth`) que l'API du composant n'a pas encore bougé.
**Verify** : (lecture) — noter la commande d'install local exacte ET l'endpoint d'envoi réel `POST /send`.

### Step 2 — Local Install du composant
Installer `@convex-dev/better-auth` + `better-auth` en **Local Install** (suivre la doc ctx7 :
copie locale du composant pour débloquer `organization`/`admin`). `convex/convex.config.ts` :
`app.use(betterAuth)`.
**Verify** : `pnpm exec convex dev --once` → OK ; `grep -q "app.use(betterAuth)" convex/convex.config.ts && echo OK` → `OK`.

### Step 3 — Instance Better Auth (`convex/auth.ts`)
`createAuth(ctx)` avec : `emailAndPassword` activé, plugins `organization` (creatorRole `owner`,
`allowUserToCreateOrganization: true`), `admin`, `phone` (sender OTP = appel HTTP au bridge
WhatsApp via l'endpoint trouvé en Step 1), et `convex({ jwt: { definePayload } })` injectant
`activeOrganizationId` dans le JWT. `user.additionalFields.activeOrganizationId` (input:false).
**Verify** : `grep -q "definePayload" convex/auth.ts && grep -q "activeOrganizationId" convex/auth.ts && echo OK` → `OK` ;
`grep -qE "organization\\(|admin\\(|phoneNumber\\(|phone\\(" convex/auth.ts && echo OK` → `OK`.

### Step 4 — Sender OTP via WhatsApp
Implémenter la fonction d'envoi d'OTP (appelée par le plugin `phone`). **Endpoint RÉEL** (cf.
`codebase-whatsapp-bridge.md`, autoritatif — NE PAS utiliser l'exemple `/api/send-otp` `{to,text}`
du fichier convex-better-auth.md qui est générique) :
- `POST ${KALGA_WHATSAPP_URL}/send` (racine, pas `/api/send`)
- payload `{ merchant_phone, to, message }`, header **`X-Internal-Key`** (= `INTERNAL_API_KEY` partagé)
- message « Votre code KALGA : {code} »
**⚠ Session émettrice (décision à confirmer avec le proprio)** : le bridge envoie DEPUIS une session
WhatsApp `ready`. Au signup, le marchand n'a pas encore connecté la sienne → il faut une **session
WhatsApp centrale KALGA** (numéro système) comme `merchant_phone` émetteur des OTP. Si non résolu →
STOP et reporter (l'OTP signup ne peut pas partir sans session émettrice).
**Fallback** : si l'appel échoue (503 session pas `ready`, etc.), lever une erreur claire
(« Envoi OTP indisponible ») — ne pas avaler silencieusement. Documenter le TODO « fallback email OTP ».
**Verify** : `grep -q "KALGA_WHATSAPP_URL" convex/auth.ts && echo OK` → `OK` ; `pnpm exec tsc --noEmit` → exit 0.

### Step 5 — HTTP handler + proxy front
`convex/http.ts` : monter `/api/auth/*` (GET/POST/OPTIONS) sur `createAuth(ctx).handler`.
Front : `src/lib/auth-client.ts` (createAuthClient + `organizationClient()` + `convexClient()`),
`src/lib/auth-server.ts`, route proxy `src/routes/api/auth.$.ts` (`Route + server.handlers`).
**Verify** : `grep -q "/api/auth/" convex/http.ts && echo OK` → `OK` ;
`test -f src/routes/api/auth.\$.ts && grep -q "server" src/routes/api/auth.\$.ts && echo OK` → `OK`.

### Step 6 — Pont marchand ↔ org (`provisionMerchantOrg`)
Mutation Convex : au signup d'un marchand, créer l'**organisation** Better Auth + un doc
`merchants` lié (`organizationId` = id de l'org, `slug` dérivé du nom, unique), définir
`activeOrganizationId`. Helper `convex/lib/withOrg.ts` (résout `activeOrganizationId` →
merchant doc → `merchantId`, lève si pas d'org). Toutes les futures mutations métier passeront par lui.
**Verify** : `grep -q "export async function withOrg" convex/lib/withOrg.ts && echo OK` → `OK` ;
`grep -q "provisionMerchantOrg" convex/merchants.ts && echo OK` → `OK`.

### Step 7 — Env + SSR + page de test
- Poser (Convex) : `BETTER_AUTH_SECRET` (`openssl rand -base64 32`), `SITE_URL`, `KALGA_WHATSAPP_URL`.
- `vite.config.ts` : `@convex-dev/better-auth` dans `ssr.noExternal`.
- `.env.example` : ajouter les NOMS (`VITE_CONVEX_SITE_URL`, etc.), jamais les valeurs.
- Page de test `/login-test` minimale : saisir téléphone → recevoir OTP → saisir code → voir l'état connecté (jetable, remplacée en 006). `signIn`/`signOut` suivis de `window.location.href` reload.
**Verify** : `pnpm exec convex env list | grep -q BETTER_AUTH_SECRET && echo OK` → `OK` ;
`grep -q "better-auth" vite.config.ts && echo OK` → `OK` ; `pnpm build` → exit 0.

### Step 8 — Validation manuelle du flow
Avec le bridge WhatsApp lancé localement, tester un signup réel (numéro test) → OTP reçu sur
WhatsApp → code → session active → `useQuery` d'une query scopée `withOrg` retourne les données du
marchand. Si pas de browser auto dispo, fournir une checklist manuelle.
**Verify** : OTP reçu sur WhatsApp ET query scopée org renvoie les données du bon marchand.

## Test plan
- Test Convex (vitest/convex-test si présent) : `withOrg` lève « No active organization » sans org ;
  `provisionMerchantOrg` crée org + merchant + slug unique ; refuse un slug déjà pris.
- Validation manuelle Step 8 (OTP end-to-end). Modèle de test : suivre un test existant du repo si présent.

## Done criteria (toutes)

- [ ] `@convex-dev/better-auth` en **Local Install**, plugins `organization` + `admin` + `phone` + `emailAndPassword` actifs dans `convex/auth.ts`.
- [ ] `definePayload` injecte `activeOrganizationId` dans le JWT (grep le confirme).
- [ ] Sender OTP appelle le bridge WhatsApp (`KALGA_WHATSAPP_URL`) et lève une erreur explicite si échec (pas de `pass` silencieux).
- [ ] `/api/auth/*` monté côté Convex + proxy front (`api/auth.$.ts`).
- [ ] `withOrg` existe et est la voie de scoping ; `provisionMerchantOrg` crée org+merchant+slug unique.
- [ ] `BETTER_AUTH_SECRET`, `SITE_URL`, `KALGA_WHATSAPP_URL` posés ; `.env.example` à jour ; **aucun secret committé**.
- [ ] `pnpm exec tsc --noEmit` exit 0 ; `pnpm build` exit 0 ; `convex dev --once` OK.
- [ ] Flow OTP validé manuellement (Step 8).
- [ ] `git status` : modifs limitées à `kalga-web/` et `plans/` (PAS `kalga-whatsapp/`).
- [ ] Ligne 003 de `plans/README.md` → DONE.

## STOP conditions
- La doc ctx7 du composant diffère structurellement de la règle `convex-better-auth-setup.md` (API changée) → reporter la nouvelle API avant de coder.
- L'endpoint d'envoi du bridge WhatsApp est introuvable ou exige une auth non documentée → reporter.
- `organization`/`admin` lèvent une erreur de schéma malgré le Local Install (install incomplet) → STOP, ne pas contourner en retirant les plugins.
- Besoin de modifier `kalga-whatsapp/` au-delà d'un appel HTTP → STOP.

## Maintenance notes
- **Fallback OTP** (bridge down) explicitement différé : prévoir email OTP de secours plus tard.
- L'OTP couple l'auth à la dispo du bridge — à surveiller quand on hébergera le bridge (D7).
- 006 remplacera `/login-test` par l'UI réelle ; garder `withOrg` comme unique voie de scoping (la sécurité multi-tenant en dépend — reviewer doit le vérifier sur chaque nouvelle mutation).
- `email+mot de passe` est activé mais l'UI d'ajout dans les settings vient en 006 (D5).
