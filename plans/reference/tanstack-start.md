# TanStack Start (React) — Référence d'exécution KALGA

> Fichier de référence pour agents exécuteurs. Patterns concrets, copiables.
> Source : ctx7 `/websites/tanstack_start_framework_react` (docs `tanstack.com/start/latest/.../react`).
> Stack cible KALGA : TanStack Start v1.x (out-of-beta mars 2026), React 19, Vite 6/8, Nitro, déploiement Vercel.

---

## 0. Versions & packages

```bash
# Quickstart à partir d'un exemple (recommandé)
npx gitpick TanStack/router/tree/main/examples/react/start-basic kalga-web
cd kalga-web && pnpm install && pnpm dev   # KALGA = pnpm exclusivement

# OU from scratch
pnpm add @tanstack/react-start @tanstack/react-router
pnpm add react react-dom
pnpm add -D vite @vitejs/plugin-react typescript @types/react @types/react-dom @types/node
```

Packages clés :
- `@tanstack/react-start` — framework + plugin Vite + helpers serveur
- `@tanstack/react-router` — routing, `createFileRoute`, `createRootRoute`, `Outlet`, `Link`, `HeadContent`, `Scripts`
- `nitro` + `nitro/vite` — couche déploiement agnostique (Vercel, Cloudflare, Netlify, Bun…)

`package.json` :
```json
{
  "type": "module",
  "scripts": { "dev": "vite dev", "build": "vite build" }
}
```

> ⚠ Convention de nommage de l'entrée routeur : TanStack Start attend `getRouter` (PAS `createRouter`) dans `src/router.tsx`. Sinon : `TypeError: entries.routerEntry.getRouter is not a function`.

---

## 1. `vite.config.ts` — plugin order (load-bearing)

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import viteReact from '@vitejs/plugin-react'
import { nitro } from 'nitro/vite'

export default defineConfig({
  server: { port: 3000 },
  resolve: { tsconfigPaths: true },
  plugins: [
    tanstackStart(),   // DOIT venir en premier
    nitro(),           // optionnel : ajoute la couche déploiement (Vercel etc.)
    viteReact(),       // le plugin react DOIT venir APRÈS tanstackStart()
  ],
})
```

L'ordre `tanstackStart()` → `viteReact()` est obligatoire. Inverser casse le build.

---

## 2. Routing fichier-based (`src/routes/`)

Le routing dérive de l'arborescence de `src/routes/`. Chaque fichier exporte `Route` via `createFileRoute('<path>')`.

| Fichier | Route URL | Notes |
|---|---|---|
| `src/routes/__root.tsx` | (racine, layout global) | `createRootRoute` / shell HTML |
| `src/routes/index.tsx` | `/` | index du segment |
| `src/routes/hello.tsx` | `/hello` | statique |
| `src/routes/users/$id.tsx` | `/users/:id` | param dynamique → `params.id` |
| `src/routes/file/$.tsx` | `/file/*` | wildcard → `params._splat` |
| `src/routes/_authed.tsx` | (pathless layout) | `_` préfixe = layout sans segment URL |
| `src/routes/app.tsx` + `src/routes/app/...` | `/app/*` | layout + enfants |

### Page route minimale
```tsx
// src/routes/hello.tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/hello')({
  component: HelloPage,
})

function HelloPage() {
  return <div>Hello</div>
}
```

### Param dynamique
```tsx
// src/routes/users/$id.tsx
export const Route = createFileRoute('/users/$id')({
  component: () => {
    const { id } = Route.useParams()
    return <div>User {id}</div>
  },
})
```

### `__root.tsx` — shell HTML complet (OBLIGATOIRE)

Le root rend tout le document `<html>`. `<HeadContent />` (head) + `<Scripts />` (hydration) sont obligatoires. Pattern moderne = `shellComponent`.

```tsx
// src/routes/__root.tsx
/// <reference types="vite/client" />
import type { ReactNode } from 'react'
import { Outlet, createRootRoute, HeadContent, Scripts } from '@tanstack/react-router'
import appCss from '~/styles/app.css?url'

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { title: 'KALGA' },
    ],
    links: [{ rel: 'stylesheet', href: appCss }],
  }),
  shellComponent: RootDocument,   // rend le document entier
})

function RootDocument({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="fr">
      <head><HeadContent /></head>
      <body>
        {children}
        <Scripts />   {/* sans ça : pas d'hydration */}
      </body>
    </html>
  )
}
```

> Variante héritée : `component: RootComponent` + un `RootDocument` interne wrappant `<Outlet />`. Préférer `shellComponent` (API actuelle).
> Le CSS s'importe en URL : `import appCss from '~/styles/app.css?url'` puis dans `head().links`.

---

## 3. Loaders + SSR

Chaque route peut définir `loader` (data fetch) + `beforeLoad` (garde/contexte). Données lues côté composant via `Route.useLoaderData()`.

```tsx
// src/routes/blog/posts/$postId.tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/blog/posts/$postId')({
  loader: async ({ params }) => {
    const post = await fetchPost(params.postId)
    return { post }
  },
  headers: () => ({                       // headers HTTP de la réponse SSR / ISR
    'Cache-Control': 'public, max-age=3600, s-maxage=3600, stale-while-revalidate=86400',
  }),
  component: BlogPost,
})

function BlogPost() {
  const { post } = Route.useLoaderData()
  return <article><h1>{post.title}</h1><div>{post.content}</div></article>
}
```

### SSR sélectif par route — option `ssr`
- `ssr: true` (défaut) — `beforeLoad` + `loader` + composant rendus côté serveur au 1er request.
- `ssr: 'data-only'` — `beforeLoad` + `loader` côté serveur, composant rendu UNIQUEMENT côté client (hybride).
- `ssr: false` — tout exécuté côté client à l'hydration (pas de SSR).

```tsx
export const Route = createFileRoute('/posts/$postId')({
  ssr: 'data-only',
  beforeLoad: () => { /* serveur au 1er request, client ensuite */ },
  loader: () => { /* idem */ },
  component: () => <div>rendu client seulement</div>,
})
```

> Utile KALGA : `ssr: false` ou `'data-only'` pour les segments `/app/*` lourds en providers (Convex, auth), tout en gardant les pages publiques en SSR complet.

### Server functions appelées dans un loader
```tsx
import { createServerFn } from '@tanstack/react-start'

const getServerPosts = createServerFn({ method: 'GET' }).handler(async () => {
  return db.posts.findMany()  // process.env accessible ici
})

export const Route = createFileRoute('/posts')({
  loader: () => getServerPosts(),
})

// Dans un composant : const getPosts = useServerFn(getServerPosts)
```

---

## 4. Server Routes / API (`Route` + `server.handlers`)

Une route fichier devient un endpoint HTTP en ajoutant `server.handlers`. Handlers = `GET`/`POST`/`PUT`/`DELETE`/`OPTIONS`, chacun `({ request, params }) => Response`.

```ts
// src/routes/hello.ts
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/hello')({
  server: {
    handlers: {
      GET: async ({ request }) => new Response('Hello, World! from ' + request.url),
      POST: async ({ request }) => {
        const body = await request.json()             // toujours await
        return Response.json({ message: `Hello, ${body.name}!` })  // set Content-Type auto
      },
    },
  },
})
```

### Params dynamiques + wildcard dans une API route
```ts
// src/routes/users/$id.ts → GET /users/123
GET: async ({ params }) => new Response(`User ID: ${params.id}`)

// src/routes/file/$.ts → GET /file/a/b.txt
GET: async ({ params }) => new Response(`File: ${params._splat}`)   // "a/b.txt"
```

### Middleware sur une server route
```tsx
import { createMiddleware } from '@tanstack/react-start'

const loggingMiddleware = createMiddleware().server(() => { /* ... */ })

export const Route = createFileRoute('/foo')({
  server: {
    middleware: [loggingMiddleware],
    handlers: { GET: () => { /* ... */ }, POST: () => { /* ... */ } },
  },
})
```

> ⚠ Si le fichier route n'exporte pas `Route` (mauvais nom d'export), le router-plugin l'IGNORE silencieusement avec un warning `does not export a Route. This file will not be included in the route tree.`
> KALGA : héberger ici le proxy vers `kalga-api` (FastAPI :8001) ou le webhook WhatsApp via `server.handlers`.

---

## 5. Lire le Host header en SSR → résoudre le tenant par sous-domaine (`{slug}.kalga.app`)

Côté serveur, accès au `Request` via les helpers de `@tanstack/react-start/server`. C'est LE pattern pour le multi-tenant storefront KALGA.

Helpers disponibles (import depuis `@tanstack/react-start/server`) :
- `getRequest()` — l'objet `Request` complet (`request.url`, `request.headers`)
- `getRequestHeader(name)` — lit un header précis (ex. `'host'`, `'x-forwarded-host'`)
- `setResponseHeaders(headers)` / `setResponseHeader(name, value)`
- `setResponseStatus(code)`

### Server function qui résout le tenant depuis le Host
```tsx
// src/server/tenant.ts
import { createServerFn } from '@tanstack/react-start'
import { getRequestHeader } from '@tanstack/react-start/server'

export const resolveTenant = createServerFn({ method: 'GET' }).handler(async () => {
  // Derrière Vercel, le host réel est dans x-forwarded-host
  const host =
    getRequestHeader('x-forwarded-host') ?? getRequestHeader('host') ?? ''
  // host = "boutique-fatou.kalga.app"  ou  "kalga.app" / "localhost:3000"
  const hostname = host.split(':')[0]                  // retire le port
  const parts = hostname.split('.')
  const isApex = hostname === 'kalga.app' || hostname === 'localhost'
  const slug = !isApex && parts.length >= 3 ? parts[0] : null  // "boutique-fatou"

  if (!slug) return null
  return await getMerchantBySlug(slug)   // appel DB / kalga-api
})
```

### Utilisation dans le loader du storefront (résolu côté serveur au 1er request)
```tsx
// src/routes/index.tsx  (ou un layout dédié storefront)
import { createFileRoute, notFound } from '@tanstack/react-router'
import { resolveTenant } from '~/server/tenant'

export const Route = createFileRoute('/')({
  loader: async () => {
    const tenant = await resolveTenant()
    if (!tenant) throw notFound()
    return { tenant }
  },
  component: () => {
    const { tenant } = Route.useLoaderData()
    return <Storefront merchant={tenant} />
  },
})
```

> Alternative : lire le host directement dans un `server.handlers` via `({ request }) => request.headers.get('host')`.
> ⚠ En local, `{slug}.localhost:3000` fonctionne dans Chrome/Firefox sans config /etc/hosts. Sinon mapper `*.kalga.test` dans hosts.
> ⚠ Sur Vercel, configurer le wildcard domaine `*.kalga.app` et lire `x-forwarded-host` (le `host` peut être l'interne Vercel).

---

## 6. Scoper des providers à un segment (`/app/*`) sans casser l'hydration des pages publiques

NE PAS wrapper Convex/Auth/QueryClient dans `__root.tsx` (`shellComponent`) : ça englobe les pages publiques (landing, storefront, login) qui n'en ont pas besoin et peut casser l'hydration SSR.

Pattern correct : un **layout route** `/app` qui wrappe ses enfants. Soit un segment réel (`src/routes/app.tsx`), soit un **pathless layout** (`src/routes/_authed.tsx`, préfixe `_` = pas de segment URL).

### Provider scopé au segment `/app`
```tsx
// src/routes/app.tsx  →  layout pour toutes les routes /app/*
import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'
import { ConvexBetterAuthProvider } from '@convex-dev/better-auth/react'
import { convex } from '~/lib/convex'
import { authClient } from '~/lib/auth-client'
import { getCurrentUserFn } from '~/server/auth'

export const Route = createFileRoute('/app')({
  beforeLoad: async ({ location }) => {
    const user = await getCurrentUserFn()
    if (!user) throw redirect({ to: '/login', search: { redirect: location.href } })
    return { user }            // dispo via Route.useRouteContext() dans les enfants
  },
  component: AppRoot,
})

function AppRoot() {
  return (
    <ConvexBetterAuthProvider client={convex} authClient={authClient}>
      <Outlet />               {/* SEULES les routes /app/* sont wrappées */}
    </ConvexBetterAuthProvider>
  )
}
```

### Pathless layout (garde d'auth sans changer l'URL)
```tsx
// src/routes/_authed.tsx  →  protège src/routes/_authed/dashboard.tsx (URL = /dashboard)
import { createFileRoute, redirect } from '@tanstack/react-router'
import { getCurrentUserFn } from '~/server/auth'

export const Route = createFileRoute('/_authed')({
  beforeLoad: async ({ location }) => {
    const user = await getCurrentUserFn()
    if (!user) throw redirect({ to: '/login', search: { redirect: location.href } })
    return { user }
  },
})
```

Pour les pages lourdes en providers, combiner avec `ssr: false` ou `ssr: 'data-only'` sur les routes enfants pour éviter les soucis d'hydration de providers qui fetchent au mount.

---

## 7. Variables d'environnement (`import.meta.env`, `VITE_*`, `process.env`)

| Contexte | Accès | Préfixe |
|---|---|---|
| Composant / code client | `import.meta.env.VITE_X` | `VITE_` obligatoire (sinon `undefined` côté client) |
| Server function / loader / handler | `process.env.X` | aucun préfixe requis, tout accessible |

```typescript
// Client (composant) — seulement VITE_*
export function AppHeader() {
  return <h1>{import.meta.env.VITE_APP_NAME}</h1>          // ✅
}
const apiUrl = import.meta.env.VITE_API_URL                // ✅ public
// const secret = import.meta.env.DATABASE_URL             // ❌ undefined (sécurité)

// Serveur (createServerFn) — tout
const getUser = createServerFn().handler(async () => {
  const db = await connect(process.env.DATABASE_URL)       // ✅ server-only
  return db.user.findFirst()
})

// Feature flag client
const enableNew = import.meta.env.VITE_ENABLE_NEW_FEATURE === 'true'
```

Règle : variable destinée au navigateur → préfixe `VITE_`. Secret (clé API, DB URL) → JAMAIS de préfixe, lu uniquement côté serveur via `process.env`.

Fichier `.env` à la racine. Pour KALGA :
```
# Public (client)
VITE_CONVEX_URL=...
VITE_APP_NAME=KALGA
# Server-only
DEEPSEEK_API_KEY=sk-...
KALGA_API_URL=http://localhost:8001
```

---

## 8. Déploiement Vercel

TanStack Start déploie via **Nitro** (couche agnostique, pas de vendor lock-in). Vercel supporte le déploiement one-click en suivant les instructions Nitro.

```typescript
// vite.config.ts — activer Nitro
import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import { defineConfig } from 'vite'
import { nitro } from 'nitro/vite'
import viteReact from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [tanstackStart(), nitro(), viteReact()],
})
```

Étapes Vercel :
1. `pnpm add -D nitro` puis ajouter `nitro()` dans `vite.config.ts`.
2. Push sur le repo, importer le projet sur Vercel (Nitro auto-détecte le preset Vercel).
3. Build command : `pnpm build` (jamais build sur prod-server — voir règle `never-build-on-prod-server`). Vercel CI gère le build off-prod.
4. **Domaine wildcard** : ajouter `*.kalga.app` dans Vercel → Domains (requiert un domaine apex `kalga.app` vérifié). Permet `{slug}.kalga.app` pour le multi-tenant storefront.
5. Côté code, lire `x-forwarded-host` (cf. §5) — Vercel met le vrai host du visiteur dedans.

Autres presets Nitro (même mécanique, `nitro({ preset: '...' })`) : `vercel`, `cloudflare`, `netlify`, `bun`, `node-server`. Exemple Bun :
```typescript
plugins: [tanstackStart(), nitro({ preset: 'bun' }), viteReact()]
```

---

## 9. Pièges KALGA (checklist)

- [ ] `getRouter` (pas `createRouter`) exporté dans `src/router.tsx`.
- [ ] `__root.tsx` : `shellComponent` HTML complet avec `<HeadContent />` + `<Scripts />`.
- [ ] `tanstackStart()` AVANT `viteReact()` dans les plugins Vite.
- [ ] Server routes : export nommé `Route` (sinon ignoré silencieusement).
- [ ] `await request.json()` dans les POST handlers.
- [ ] Tenant resolve : lire `x-forwarded-host` en priorité (Vercel), fallback `host`, retirer le port, slug = `parts[0]` si `>= 3` segments.
- [ ] Providers Convex/Auth scopés à `/app` (layout route), JAMAIS dans `__root.tsx`.
- [ ] Secrets sans préfixe (`process.env`), public en `VITE_*` (`import.meta.env`).
- [ ] CSS importé via `?url` puis dans `head().links`.
- [ ] Build off-prod (Vercel CI), wildcard `*.kalga.app` configuré dans Vercel Domains.
