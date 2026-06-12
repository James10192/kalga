# Déploiement Vercel — TanStack Start (KALGA) — Référence d'exécution

> Fichier de référence pour agents exécuteurs SANS contexte. Patterns concrets, copiables.
> Sources : ctx7 `/websites/vercel`, `/websites/tanstack_start_framework_react` (docs `tanstack.com/start/latest/.../react`).
> Stack cible KALGA : TanStack Start v1.x (out-of-beta mars 2026) + React 19 + Vite 6/8 + **Nitro** + Convex backend, déployé sur **Vercel**.
> Domaines KALGA (décision D2 archi) :
> - `kalga.app` / `www.kalga.app` → landing
> - `app.kalga.app` → dashboard marchand + `/admin` back-office
> - `{slug}.kalga.app` → storefront public (1 sous-domaine par marchand = tenant) → **wildcard `*.kalga.app`**

---

## 0. Vue d'ensemble — comment ça marche

TanStack Start ne déploie pas "tout seul". La couche déploiement est **Nitro** (agnostique). Nitro détecte automatiquement Vercel quand il build dans l'environnement CI Vercel (variable `VERCEL=1`), et produit l'output au format **Build Output API v3** dans `.vercel/output/`. Vercel sert ensuite cet output : static depuis le CDN, SSR depuis une Vercel Function.

```
pnpm build  →  vite build (plugin tanstackStart + nitro)
            →  Nitro preset "vercel" (auto-détecté en CI Vercel)
            →  .vercel/output/   (Build Output API v3)
            →  Vercel sert : static CDN + SSR function
```

**Conséquence clé** : on ne configure PAS `outputDirectory` manuellement quand Nitro cible Vercel — Nitro écrit dans `.vercel/output/` et Vercel le détecte. Voir §1.

---

## 1. Déployer une app TanStack Start sur Vercel

### 1.1 `vite.config.ts` — plugin Nitro (load-bearing)

```ts
// vite.config.ts
import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import { defineConfig } from 'vite'
import { nitro } from 'nitro/vite'
import viteReact from '@vitejs/plugin-react'

export default defineConfig({
  // Ordre des plugins IMPORTANT : tanstackStart() AVANT nitro() AVANT viteReact()
  plugins: [
    tanstackStart(),
    nitro(),          // sans { preset } : auto-détecte Vercel en CI (VERCEL=1)
    viteReact(),
  ],
})
```

> `pnpm add nitro` est requis (la couche déploiement n'est pas incluse par défaut).
> Pour forcer explicitement : `nitro({ preset: 'vercel' })`. En CI Vercel, l'auto-détection suffit ; ne PAS hardcoder un preset différent.
> Versions testées KALGA : `@tanstack/react-start` 1.132+, `vite` 6/8, `react` 19.2, Node 22 (runtime Vercel par défaut).

### 1.2 `package.json`

```json
{
  "type": "module",
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "start": "node .output/server/index.mjs"
  }
}
```

> Le script `build` = `vite build` (PAS `tanstack build` ni `nitro build` séparé). Le plugin Nitro s'enclenche pendant `vite build`.

### 1.3 Configuration projet Vercel (Dashboard ou `vercel.json`)

Réglages **Project Settings → Build & Development** :
- **Framework Preset** : `Vite` (ou "Other" — Nitro gère l'output, le preset Vercel sert surtout les défauts UI)
- **Build Command** : `pnpm build` (laisser vide pour utiliser le script `build`)
- **Output Directory** : **laisser vide / défaut** — Nitro écrit dans `.vercel/output/` (Build Output API). NE PAS mettre `dist` ni `build`.
- **Install Command** : `pnpm install` (Vercel détecte `pnpm-lock.yaml` automatiquement)
- **Node.js Version** : 22.x

`vercel.json` minimal (à la racine du projet front `kalga-web/`) :

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": "pnpm build",
  "installCommand": "pnpm install --frozen-lockfile",
  "framework": "vite",
  "git": {
    "deploymentEnabled": {
      "main": true,
      "develop": false
    }
  }
}
```

> ⚠ Si le front KALGA est dans un **sous-dossier** du repo (`kalga-web/`), régler **Root Directory = `kalga-web`** dans Project Settings → General. Sinon Vercel build à la racine du monorepo et échoue.
> ⚠ Ne PAS mettre `"outputDirectory"` : Nitro+Vercel passent par `.vercel/output/`, un override casse le déploiement SSR.

### 1.4 Déploiement

```bash
# Setup CLI (une fois)
pnpm add -g vercel        # ou: npx vercel
vercel login
vercel link               # lie le dossier local au projet Vercel

# Preview deploy (branche)
vercel

# Production deploy
vercel --prod
```

> **Recommandé KALGA** : déploiement **Git-driven** (push sur `main` = prod, autres branches = preview). Pas de `vercel --prod` manuel en routine. Voir §6 (build off-prod).

### 1.5 Convention nommage routeur (piège fréquent)

`src/router.tsx` DOIT exporter `getRouter` (PAS `createRouter`), sinon le build/SSR plante :
```
TypeError: entries.routerEntry.getRouter is not a function
```

```ts
// src/router.tsx
import { createRouter as createTanStackRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen'

export function getRouter() {            // ← nom obligatoire
  return createTanStackRouter({ routeTree, defaultPreload: 'intent' })
}
declare module '@tanstack/react-router' {
  interface Register { router: ReturnType<typeof getRouter> }
}
```

---

## 2. Domaine wildcard `*.kalga.app` + apex + `app.`

### 2.1 Architecture domaine cible

| Hostname | Rôle | Type DNS / Vercel |
|---|---|---|
| `kalga.app` | apex → landing | A record `76.76.21.21` OU nameservers Vercel |
| `www.kalga.app` | redirect/landing | CNAME `cname.vercel-dns.com` |
| `app.kalga.app` | dashboard marchand + admin | CNAME `cname.vercel-dns.com` |
| `*.kalga.app` | storefront tenant `{slug}.kalga.app` | **wildcard — nameservers Vercel OBLIGATOIRES** |

> **CONTRAINTE CRITIQUE** : pour qu'un **wildcard `*.kalga.app`** obtienne des certificats SSL auto-générés, le domaine **DOIT utiliser les nameservers de Vercel** (`ns1.vercel-dns.com`, `ns2.vercel-dns.com`). Un wildcard via simple CNAME ne permet PAS à Vercel d'émettre les certificats par sous-domaine.
> (ctx7 : « To generate wildcard SSL certificates, projects must use Vercel's nameservers. »)

### 2.2 Méthode recommandée — Nameservers Vercel (gère apex + www + app + wildcard d'un coup)

**Étape A — Ajouter les domaines au projet Vercel** (Dashboard → Project → Settings → Domains, ou CLI) :

```bash
vercel domains add kalga.app                 # apex
vercel domains add app.kalga.app             # dashboard
vercel domains add "*.kalga.app"             # wildcard storefront
# www généralement ajouté + redirigé vers apex automatiquement
```

**Étape B — Pointer le registrar vers les nameservers Vercel** :
Chez le registrar (Namecheap, Gandi, etc.), remplacer les nameservers par :
```
ns1.vercel-dns.com
ns2.vercel-dns.com
```

> ⚠ Quand on bascule vers les nameservers Vercel, **tous les enregistrements DNS existants** (MX email, TXT SPF/DKIM, etc.) doivent être **re-créés dans Vercel** (Dashboard → Domains → DNS Records), sinon l'email casse. (ctx7 : « If using Vercel Nameservers for a wildcard domain, you must add any existing DNS records to Vercel. »)

```bash
# Re-créer les enregistrements email/TXT existants côté Vercel
vercel dns add kalga.app '@' MX mail.example.com 10
vercel dns add kalga.app '@' TXT "v=spf1 include:..."
```

**Étape C — Vérification + SSL** : Vercel émet automatiquement les certificats (apex, www, app, et un certificat par sous-domaine wildcard à la volée). Vérifier :
```bash
vercel domains inspect kalga.app
vercel certs ls
```

### 2.3 Méthode alternative — DNS externe (registrar garde les nameservers)

Acceptable pour `kalga.app` + `www` + `app` (PAS idéal pour le wildcard, voir contrainte SSL §2.1).

```bash
# Apex : A record vers l'IP Vercel
vercel dns add kalga.app '@' A 76.76.21.21
# Sous-domaines : CNAME vers Vercel
vercel dns add kalga.app www CNAME cname.vercel-dns.com
vercel dns add kalga.app app CNAME cname.vercel-dns.com
# Wildcard : CNAME (mais SSL wildcard NON garanti sans nameservers Vercel)
vercel dns add kalga.app '*' CNAME cname.vercel-dns.com
```

Si on reste sur DNS externe pour le wildcard, **pré-générer le certificat** via challenge DNS :
```bash
# Émet un challenge TXT à placer chez le registrar, puis :
vercel certs issue "*.kalga.app" kalga.app --challenge-only
# ... ajouter le TXT _acme-challenge chez le registrar, attendre propagation ...
vercel certs issue "*.kalga.app" kalga.app
```
> Conclusion KALGA : **utiliser les nameservers Vercel** (§2.2) pour éviter la gestion manuelle des certs wildcard.

### 2.4 Routage par hostname (UNE app, 3 surfaces)

Toutes les surfaces sont la **même app TanStack Start** déployée une seule fois. Aucun `vercel.json` `rewrites` nécessaire pour distinguer les sous-domaines : le hostname est lu côté serveur (§4) et la même app sert landing / dashboard / storefront selon `host`.

> Pas besoin de Vercel Middleware (`middleware.ts`) pour ça — TanStack Start a son propre global request middleware (§4.2). Le `middleware.ts` Vercel reste possible mais ajoute une couche edge superflue ici.

---

## 3. Variables d'environnement

### 3.1 Règle Vite — préfixe `VITE_` pour exposition client

Toute variable lue côté **navigateur** (bundle client) DOIT être préfixée `VITE_`. Sans préfixe = accessible uniquement côté serveur (SSR / server functions). C'est une règle Vite, héritée par TanStack Start.

| Variable | Préfixe | Exposée client ? | Rôle KALGA |
|---|---|---|---|
| `VITE_CONVEX_URL` | `VITE_` | OUI | URL deployment Convex (client React useQuery) |
| `VITE_CONVEX_SITE_URL` | `VITE_` | OUI | URL site Convex (Better Auth / HTTP actions) |
| `VITE_ROOT_DOMAIN` | `VITE_` | OUI | `kalga.app` — pour construire les liens `{slug}.kalga.app` |
| `CONVEX_DEPLOY_KEY` | — | NON | clé build pour `npx convex deploy` (server/CI seulement) |
| `BETTER_AUTH_SECRET` | — | NON | secret session (server only) |
| `SITE_URL` | — | NON | `https://app.kalga.app` (Better Auth baseURL server) |

> ⚠ NE JAMAIS préfixer un secret (`BETTER_AUTH_SECRET`, `CONVEX_DEPLOY_KEY`, clés API) avec `VITE_` — il finirait dans le bundle JS public.

### 3.2 Déclarer les variables sur Vercel

Via Dashboard (**Project → Settings → Environment Variables**) ou CLI :

```bash
# Production
vercel env add VITE_CONVEX_URL production
vercel env add VITE_CONVEX_SITE_URL production
vercel env add VITE_ROOT_DOMAIN production
vercel env add CONVEX_DEPLOY_KEY production

# Preview / Development : répéter avec preview / development
vercel env add VITE_CONVEX_URL preview

# Récupérer en local (génère .env.local)
vercel env pull .env.local
```

> Chaque variable est scopée par **environnement** : `production`, `preview`, `development`. Déclarer `VITE_CONVEX_URL` séparément pour prod (Convex prod) et preview (Convex dev/preview).
> ⚠ Une variable `VITE_*` est **figée au build** (inlined dans le bundle). Changer sa valeur exige un **rebuild** — pas un simple restart.

### 3.3 Variables système Vercel utiles

```bash
VERCEL=1                          # présent en CI Vercel (Nitro auto-détecte)
VERCEL_ENV=production|preview|development
VERCEL_GIT_COMMIT_REF=main        # branche du commit déployé
VERCEL_URL=...vercel.app          # URL du déploiement (sans protocole)
```
Pour les exposer au client, créer un alias préfixé `VITE_` dans Project Settings (ex. `VITE_VERCEL_ENV` = `$VERCEL_ENV`).

### 3.4 Accès dans le code

```ts
// Client (composants React) — uniquement VITE_*
const convexUrl = import.meta.env.VITE_CONVEX_URL

// Server (server functions, SSR, middleware) — toutes les vars
const secret = process.env.BETTER_AUTH_SECRET
```

---

## 4. Résolution du tenant par hostname en SSR (Vercel)

Objectif : sur `{slug}.kalga.app`, extraire `slug`, résoudre le marchand dans Convex, rendre le storefront en SSR. Le hostname est lu via les **headers de la requête serveur**.

### 4.1 Lire le hostname dans une server function / SSR

TanStack Start expose les helpers serveur depuis `@tanstack/react-start/server` :
- `getRequest()` → l'objet `Request` complet
- `getRequestHeader(name)` → un header précis

```ts
// src/lib/tenant.server.ts
import { getRequestHeader } from '@tanstack/react-start/server'

const ROOT = 'kalga.app'

/** Renvoie le slug du tenant depuis le hostname, ou null si apex/app/www. */
export function resolveTenantSlug(): string | null {
  // Sur Vercel, préférer x-forwarded-host (host réel client) ; fallback host.
  const host =
    getRequestHeader('x-forwarded-host') ??
    getRequestHeader('host') ??
    ''
  const hostname = host.split(':')[0].toLowerCase()  // retire le port éventuel

  if (
    hostname === ROOT ||
    hostname === `www.${ROOT}` ||
    hostname === `app.${ROOT}` ||
    hostname.endsWith('.vercel.app')   // déploiements preview
  ) {
    return null
  }
  if (hostname.endsWith(`.${ROOT}`)) {
    return hostname.slice(0, -(`.${ROOT}`.length))  // "boutique-x.kalga.app" → "boutique-x"
  }
  return null
}
```

> ⚠ Sur Vercel, derrière le proxy, le header pertinent est **`x-forwarded-host`** (identique à `host` côté client). Toujours essayer `x-forwarded-host` d'abord, fallback `host`.
> ⚠ Les déploiements **preview** servent sur `*.vercel.app` (pas `*.kalga.app`) — prévoir le cas (retourner `null` ou un slug de démo).

### 4.2 Global request middleware (résolution sur CHAQUE requête)

Pour injecter le tenant dans le contexte de toutes les requêtes (SSR + server routes + server functions), créer `src/start.ts` :

```ts
// src/start.ts
import { createStart, createMiddleware } from '@tanstack/react-start'
import { resolveTenantSlug } from './lib/tenant.server'

const tenantMiddleware = createMiddleware().server(({ next }) => {
  const slug = resolveTenantSlug()
  // dispo en aval via le contexte
  return next({ context: { tenantSlug: slug } })
})

export const startInstance = createStart(() => ({
  requestMiddleware: [tenantMiddleware],  // s'exécute sur TOUTE requête
}))
```

> `requestMiddleware` (≠ `functionMiddleware`) couvre SSR + server routes + server functions.
> Si `src/start.ts` est créé, le CSRF middleware par défaut n'est plus auto-installé — le ré-ajouter si besoin (cf. `createCsrfMiddleware`).

### 4.3 Charger le catalogue tenant en SSR depuis Convex

```ts
// src/routes/index.tsx  (storefront racine, rendu selon le tenant)
import { createFileRoute } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { ConvexHttpClient } from 'convex/browser'
import { api } from '../../convex/_generated/api'
import { resolveTenantSlug } from '../lib/tenant.server'

const loadStorefront = createServerFn({ method: 'GET' }).handler(async () => {
  const slug = resolveTenantSlug()
  if (!slug) return { kind: 'landing' as const }

  const convex = new ConvexHttpClient(process.env.VITE_CONVEX_URL!)
  const merchant = await convex.query(api.merchants.getBySlug, { slug })
  if (!merchant) return { kind: 'not_found' as const, slug }

  const products = await convex.query(api.products.listByMerchant, {
    merchantId: merchant._id,
  })
  return { kind: 'storefront' as const, merchant, products }
})

export const Route = createFileRoute('/')({
  loader: () => loadStorefront(),
  component: StorefrontOrLanding,
})
```

> ⚠ En SSR Vercel, instancier `ConvexHttpClient` PAR requête (pas de singleton global réutilisé entre requêtes — risque de fuite de contexte tenant entre invocations de la function).
> ⚠ Cache : une réponse SSR dépendant du tenant NE DOIT PAS être `Cache-Control: public` partagée. Si caching, varier par hostname ou rester `private`/`no-store`.

### 4.4 Construire les liens cross-subdomain côté client

```ts
const ROOT = import.meta.env.VITE_ROOT_DOMAIN   // "kalga.app"
const storefrontUrl = (slug: string) => `https://${slug}.${ROOT}`
const dashboardUrl = `https://app.${ROOT}`
```

---

## 5. Pièges Vercel + TanStack Start (checklist)

- [ ] `nitro` installé + dans `vite.config.ts` ; ordre `tanstackStart()` → `nitro()` → `viteReact()`.
- [ ] `src/router.tsx` exporte **`getRouter`** (pas `createRouter`).
- [ ] **Root Directory** = `kalga-web` si front en sous-dossier du repo.
- [ ] **Output Directory** laissé vide (Nitro → `.vercel/output/`).
- [ ] Domaine sur **nameservers Vercel** pour le wildcard `*.kalga.app` (SSL auto).
- [ ] Enregistrements **MX/TXT email** re-créés dans Vercel DNS après bascule nameservers.
- [ ] Secrets **jamais** préfixés `VITE_`.
- [ ] `VITE_CONVEX_URL` déclarée pour `production` ET `preview` (deployments séparés).
- [ ] Lecture hostname via **`x-forwarded-host`** (fallback `host`) côté serveur.
- [ ] `ConvexHttpClient` instancié par requête en SSR.
- [ ] Libs browser-only (jspdf, file-saver) en `ssr.external` du `vite.config.ts` (sinon crash SSR).

---

## 6. Build off-prod (règle absolue : NE JAMAIS build sur un serveur de prod)

Sur Vercel, le build s'exécute **par défaut dans l'infra CI éphémère de Vercel** — c'est déjà off-prod, conforme à la règle `never-build-on-prod-server.md`. Aucune machine KALGA ne build le front.

### 6.1 Pipeline correct (Git-driven, recommandé)

```
git push origin main
   → Vercel build dans son CI éphémère (VERCEL=1)
   → Nitro produit .vercel/output/
   → Vercel publie : SSR function + static CDN (atomique, <1s de bascule)
```
- Push sur `main` = **production**.
- Push sur autres branches / PR = **preview** (URL `*.vercel.app` dédiée).
- Désactiver le deploy de branches inutiles via `vercel.json` `git.deploymentEnabled` (cf. §1.3).

### 6.2 Convex — déployer le backend AVANT/PENDANT le build front

Le build front a besoin du codegen Convex à jour. Sur Vercel, faire le `convex deploy` dans le **build command** :

```json
// vercel.json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": "npx convex deploy --cmd 'pnpm build'"
}
```
> `npx convex deploy --cmd 'pnpm build'` : déploie les functions Convex puis lance le build front avec `VITE_CONVEX_URL` injectée automatiquement. Nécessite `CONVEX_DEPLOY_KEY` en env Vercel (production).

### 6.3 Anti-patterns à bloquer

- ❌ `ssh user@prod "pnpm build"` ou tout build sur EC2/Oracle/VPS KALGA — le front build sur Vercel CI uniquement.
- ❌ `nice -n 19 ionice ... pnpm build` sur une machine qui sert du trafic.
- ❌ `vercel build && vercel deploy --prebuilt` exécuté sur un serveur de prod — utiliser le Git-driven.
- ❌ Override `outputDirectory` qui casse le SSR Nitro.

### 6.4 Deploy CLI manuel (cas exceptionnel, depuis machine dev/CI)

```bash
# Depuis une machine dev (jamais un serveur prod)
vercel pull --yes --environment=production   # récupère config + env
vercel build --prod                          # build local, off-prod
vercel deploy --prebuilt --prod              # upload artefact pré-buildé
```

---

## 7. Références

- TanStack Start hosting : `tanstack.com/start/latest/docs/framework/react/guide/hosting`
- TanStack Start middleware : `tanstack.com/start/latest/docs/framework/react/guide/middleware`
- TanStack Start server functions / headers : `.../guide/server-functions`
- Vercel multi-tenant domains : `vercel.com/docs/multi-tenant/domain-management`
- Vercel custom domain / DNS : `vercel.com/docs/domains/set-up-custom-domain`
- Vercel wildcard SSL pre-gen : `vercel.com/docs/domains/pre-generating-ssl-certs`
- Vercel Vite framework + env : `vercel.com/docs/frameworks/frontend/vite`
- Vercel request headers (`host` / `x-forwarded-host`) : `vercel.com/docs/headers/request-headers`
- Vercel `vercel.json` : `vercel.com/docs/project-configuration/vercel-json`
- Convex + Vercel deploy : `docs.convex.dev/production/hosting/vercel`
- Règle globale : `~/.claude/rules/never-build-on-prod-server.md`, `tanstack-start-vite-gotchas.md`, `convex-better-auth-setup.md`
