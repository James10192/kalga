# Référence — @convex-dev/better-auth en LOCAL INSTALL (KALGA, single-store)

> Fichier de référence pour agents exécuteurs sans contexte. Code exact, chemins, commandes.
> Cible : KALGA = TanStack Start (front) + Convex (backend unique, single-store). Auth par
> téléphone (OTP envoyé via le bridge WhatsApp), multi-tenant (organisations = boutiques),
> admin global (back-office).

---

## État implémenté (2026-06-12)

Le plan 003 a réalisé le Local Install **intégralement côté code** (statut PARTIAL : seul le
test OTP live = Step 8 reste bloqué par GATE-2). Déviations vs ce fichier de référence :

- **VERSIONS RÉELLES (drift)** : le fichier décrivait `@convex-dev/better-auth ^0.10.x` +
  `better-auth@1.5.3`. La réalité installée :
  - `@convex-dev/better-auth@^0.12.3` (le composant résout en 0.12.x, pas 0.10.x)
  - `better-auth@1.6.16` (**le 1.5.3 du fichier est INCOMPATIBLE** avec le composant 0.12 qui exige
    `>=1.6.11 <1.7.0`). Pin maintenu, pas `--save-exact`.
  - `convex@^1.41.0`, `@convex-dev/react-query@^0.1.0`.
  - L'API structurelle reste identique (`createClient` + `authComponent.adapter`,
    `better-auth/minimal`, `registerRoutes`, `convex({})` en dernier, `definePayload`).
  - 0.12 exige en plus, pour le Local Install : `createAuthOptions` + `convex/betterAuth/adapter.ts`
    (`createApi(schema, createAuthOptions)`). Implémentés selon ctx7 à jour.
  - `reactStartHandler` standalone n'est plus exporté par react-start → la route proxy
    `src/routes/api/auth.$.ts` utilise uniquement le `handler` de `auth-server.ts`.
- **SENDER OTP RÉEL** (résolution du sous-gate "conflit endpoint" de REFERENCE §4) : le code cible
  bien le **vrai** endpoint du bridge, **PAS** l'exemple `/api/send-otp` `{to, text}` `x-kalga-internal`
  de la §11 ci-dessous :
  - `POST {KALGA_WHATSAPP_URL}/send` (racine), payload `{ merchant_phone, to, message }`,
    header **`X-Internal-Key`** (= `process.env.INTERNAL_API_KEY`).
  - Lève une erreur explicite si le bridge répond 503 (session pas `ready`) / 401 (clé invalide)
    / injoignable. **Pas d'échec silencieux.**
- **Env vars Convex réellement posées** : `BETTER_AUTH_SECRET`, `SITE_URL` (`http://localhost:3000`),
  `KALGA_WHATSAPP_URL` (`http://localhost:3001`), `INTERNAL_API_KEY`. **NON posée** :
  `KALGA_OTP_SENDER_PHONE` (numéro système émetteur, volontairement absent en dev = GATE-2).
- **Fichiers réellement créés** : `convex/convex.config.ts`, `convex/auth.config.ts`, `convex/auth.ts`
  (plugins `organization`/`admin`/`phoneNumber`/`emailAndPassword` + `convex({})` en dernier,
  `definePayload` → `activeOrganizationId`, sender OTP via bridge `/send`), `convex/http.ts`
  (`registerRoutes(..., {cors:true})`), composant local `convex/betterAuth/` (`convex.config.ts`,
  `auth.ts`, `adapter.ts`, `generatedSchema.ts`, `schema.ts`, `_generated/`), `convex/lib/withOrg.ts`
  (résout `activeOrganizationId` → doc `merchants` → `merchantId`), `convex/merchants.ts` ajoute
  `slugify`/`uniqueSlug`/`provisionMerchantOrg` (org Better Auth + doc merchant + slug unique
  suffixe `-2`/`-3`) + query `current` scopée `withOrg`. Front : `src/lib/auth-client.ts`,
  `src/lib/auth-server.ts` (`convexSiteUrl` en `.site`), `src/routes/api/auth.$.ts`,
  `src/router.tsx` (`expectAuth: true` + TanStack Query SSR), `src/routes/__root.tsx`
  (`ConvexBetterAuthProvider` + token SSR). Page de test jetable `src/routes/login-test.tsx`.
  `vite.config.ts` : `@convex-dev/better-auth` dans `ssr.noExternal`.
- **GATE-2 (Step 8) NON réalisé** : l'OTP signup exige (a) bridge `ready` et (b) une SESSION
  WhatsApp CENTRALE KALGA émettrice. Variables à poser AVANT test live : `KALGA_OTP_SENDER_PHONE`
  (numéro système, doit être `ready` côté bridge) — `INTERNAL_API_KEY` est déjà posée. Décision
  proprio requise : quel numéro/session centrale KALGA émet les OTP signup.
- **TODO documenté** (différé) : fallback email OTP quand le bridge est down ; UI d'ajout
  email+mot de passe dans les settings (plan 006).

---

## 0. Versions (vérifiées via ctx7 — juin 2026)

| Package | Version | Note |
|---|---|---|
| `@convex-dev/better-auth` | `^0.10.x` (composant 0.10+) | API actuelle = `createClient` + `authComponent.adapter(ctx)` |
| `better-auth` | `1.5.3` (**pin exact**) | `npm i better-auth@1.5.3 --save-exact` — le composant est sensible à la version |
| `convex` | `>= 1.25.0` | requis par le composant |
| `@convex-dev/react-query` | latest | SSR auth via `ConvexQueryClient(url, { expectAuth: true })` |
| `@tanstack/react-start` | 1.120+ (v1 stable) | voir rule `tanstack-start-vite-gotchas.md` |

### ⚠ Divergence vs l'ancien pattern (rule `convex-better-auth-setup.md`)

L'ancienne rule globale décrit `convexAdapter(ctx, components.betterAuth)`, `betterAuth` (pas
`/minimal`), et un mount HTTP manuel via `http.route({ pathPrefix: '/api/auth/' })`. **C'est
périmé.** L'API 0.10+ utilise :
- `createClient<DataModel>(components.betterAuth)` → expose `authComponent`
- `authComponent.adapter(ctx)` comme `database`
- `import { betterAuth } from "better-auth/minimal"`
- `authComponent.registerRoutes(http, createAuth, { cors: true })` au lieu du `http.route` manuel
- côté react-start : `reactStartHandler(request)` + `convexBetterAuthReactStart({...})`

Suivre **ce fichier**, pas l'ancienne rule, pour le code.

---

## 1. Pourquoi LOCAL INSTALL est obligatoire pour KALGA

Le composant NPM par défaut a un **schéma figé** qui ne supporte QUE cette liste de plugins
(https://labs.convex.dev/better-auth/supported-plugins) :

> Anonymous, Email OTP, Generic OAuth, JWT, Magic Link, One Tap, **Phone Number**, Two Factor, Username.

**`organization` et `admin` n'y sont PAS.** Les activer sur l'install par défaut →
`ArgumentValidationError: Path: .model Value: "organization"` (l'adapter par défaut n'a pas les
tables `organization` / `member` / `invitation`).

KALGA a besoin de :
- `organization` (chaque boutique = une org, multi-tenant)
- `admin` (back-office global, impersonation)
- `phoneNumber` (login par numéro WhatsApp + OTP)

→ **Local Install dès le jour 1.** Le Local Install donne le contrôle total du schéma Better Auth,
permet la génération de schéma via la CLI Better Auth, débloque les plugins non-supportés, et
permet d'écrire des fonctions Convex qui lisent directement les tables du composant.

> Note : `phoneNumber` EST supporté par l'install par défaut, mais comme `organization` + `admin`
> ne le sont pas, on passe en Local Install de toute façon.

---

## 2. Installation + structure de fichiers

### 2.1 Packages

```bash
npm install @convex-dev/better-auth @convex-dev/react-query
npm install better-auth@1.5.3 --save-exact
# convex doit être >= 1.25.0
npm install convex@latest
npx convex dev --once   # provisionne le déploiement, crée .env.local
```

### 2.2 Secret + env

```bash
# secret Better Auth (côté Convex, PAS dans le front)
npx convex env set BETTER_AUTH_SECRET=$(openssl rand -base64 32)
# URL publique du site (prod) — en dev, fallback http://localhost:3000
npx convex env set SITE_URL http://localhost:3000
```

`.env.local` (généré par `npx convex dev`, lu par Vite) :

```dotenv
CONVEX_DEPLOYMENT=dev:adjective-animal-123
VITE_CONVEX_URL=https://adjective-animal-123.convex.cloud
# IMPORTANT : même valeur que VITE_CONVEX_URL mais en .site
VITE_CONVEX_SITE_URL=https://adjective-animal-123.convex.site
VITE_SITE_URL=http://localhost:3000
```

### 2.3 Arborescence Local Install

```
convex/
├── convex.config.ts            # app.use(betterAuth) → pointe sur le composant LOCAL
├── auth.config.ts              # providers Convex (getAuthConfigProvider)
├── auth.ts                     # createClient + createAuth (plugins org/admin/phone)
├── http.ts                     # authComponent.registerRoutes(...)
├── lib/withOrg.ts              # helper scoping multi-tenant
└── betterAuth/                 # ← le composant LOCAL
    ├── convex.config.ts        # defineComponent("betterAuth")
    ├── auth.ts                 # export STATIQUE pour la génération de schéma
    ├── generatedSchema.ts      # généré par la CLI (ne pas éditer à la main)
    └── schema.ts               # ré-export du schéma généré
src/
├── lib/auth-server.ts          # convexBetterAuthReactStart(...)
├── lib/auth-client.ts          # createAuthClient(...) plugins client
└── routes/api/auth.$.ts        # proxy /api/auth/* → reactStartHandler
```

### 2.4 Génération du schéma (étape SPÉCIFIQUE au Local Install)

`convex/betterAuth/auth.ts` — **ne doit contenir QUE l'export `auth`** (sinon erreurs runtime
liées aux env vars manquantes au moment de la génération) :

```typescript
// convex/betterAuth/auth.ts
import { createAuth } from '../auth'

// Instance statique UNIQUEMENT pour la génération de schéma Better Auth CLI.
// Ne rien ajouter d'autre dans ce fichier.
export const auth = createAuth({} as any)
```

Puis générer :

```bash
cd convex/betterAuth
npx auth generate --output generatedSchema.ts
```

`convex/betterAuth/schema.ts` ré-exporte le schéma généré :

```typescript
// convex/betterAuth/schema.ts
export { default } from './generatedSchema'
```

> Re-générer le schéma à CHAQUE ajout/retrait de plugin (organization, admin, phoneNumber ajoutent
> leurs tables : `organization`, `member`, `invitation`, `verification` OTP, etc.).

---

## 3. `convex/betterAuth/convex.config.ts` (définit le composant local)

```typescript
// convex/betterAuth/convex.config.ts
import { defineComponent } from "convex/server";

const component = defineComponent("betterAuth");

export default component;
```

## 4. `convex/convex.config.ts` (enregistre le composant local)

```typescript
// convex/convex.config.ts
import { defineApp } from "convex/server";
// ⚠ import depuis le composant LOCAL, PAS depuis "@convex-dev/better-auth/convex.config"
import betterAuth from "./betterAuth/convex.config";

const app = defineApp();
app.use(betterAuth);

export default app;
```

## 5. `convex/auth.config.ts` (provider Convex)

```typescript
// convex/auth.config.ts
import { getAuthConfigProvider } from "@convex-dev/better-auth/auth-config";
import type { AuthConfig } from "convex/server";

export default {
  providers: [getAuthConfigProvider()],
} satisfies AuthConfig;
```

---

## 6. `convex/auth.ts` — `createAuth` (organization + admin + phoneNumber + emailAndPassword)

```typescript
// convex/auth.ts
import { createClient, type GenericCtx } from "@convex-dev/better-auth";
import { convex } from "@convex-dev/better-auth/plugins";
import { betterAuth } from "better-auth/minimal";          // ⚠ /minimal en 0.10+
import { organization, admin, phoneNumber } from "better-auth/plugins";
import { components } from "./_generated/api";
import type { DataModel } from "./_generated/dataModel";
import { query } from "./_generated/server";
import authConfig from "./auth.config";
import authSchema from "./betterAuth/schema";              // ⚠ schéma LOCAL

const siteUrl = process.env.SITE_URL ?? "http://localhost:3000";

// Client du composant. En LOCAL install on passe le schéma local en 2e generic + option `local`.
export const authComponent = createClient<DataModel, typeof authSchema>(
  components.betterAuth,
  {
    local: {
      schema: authSchema,
    },
  }
);

export const createAuth = (ctx: GenericCtx<DataModel>) =>
  betterAuth({
    baseURL: siteUrl,
    trustedOrigins: ["http://localhost:3000", siteUrl],
    database: authComponent.adapter(ctx),

    // Email/password (admin back-office, fallback)
    emailAndPassword: {
      enabled: true,
      requireEmailVerification: false,
      minPasswordLength: 8,
    },

    plugins: [
      // --- Multi-tenant : chaque boutique = une organization ---
      organization({
        allowUserToCreateOrganization: true,
        creatorRole: "owner",
        membershipLimit: 100,
        invitationExpiresIn: 60 * 60 * 24 * 7, // 7 jours
      }),

      // --- Back-office global + impersonation ---
      admin({
        defaultRole: "user",
        adminRoles: ["admin"],
      }),

      // --- Login par numéro WhatsApp + OTP (voir §11 pour le sender) ---
      phoneNumber({
        // crée un user à la première vérif réussie d'un numéro inconnu
        signUpOnVerification: {
          getTempEmail: (phone) => `${phone}@kalga.local`,
          getTempName: (phone) => phone,
        },
        sendOTP: async ({ phoneNumber, code }) => {
          // appel HTTP vers le bridge WhatsApp (voir §11)
          await fetch(`${process.env.WHATSAPP_BRIDGE_URL}/api/send-otp`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ to: phoneNumber, code }),
          });
        },
      }),

      // --- Plugin Convex : OBLIGATOIRE, doit être en DERNIER ---
      convex({
        authConfig,
        jwt: {
          // injecte activeOrganizationId dans le JWT pour le scoping multi-tenant
          definePayload: ({ user, session }) => ({
            email: user.email,
            name: user.name,
            phoneNumber: (user as { phoneNumber?: string }).phoneNumber ?? null,
            role: (user as { role?: string }).role ?? "user",
            // activeOrganizationId vit sur la SESSION (posé par le plugin organization)
            activeOrganizationId:
              (session as { activeOrganizationId?: string }).activeOrganizationId ?? null,
            // sessionId et iat sont ajoutés automatiquement par le plugin convex
          }),
        },
      }),
    ],
  });

// Utilitaire : user courant (valide la session)
export const getCurrentUser = query({
  args: {},
  handler: async (ctx) => authComponent.safeGetAuthUser(ctx),
});
```

### Notes critiques §6

- `convex({...})` doit être le **dernier** plugin de la liste.
- `definePayload` : `sessionId` et `iat` sont **toujours** ajoutés automatiquement, ne pas les
  redéfinir. Defaut = tous les champs user sauf `id` et `image` + `sessionId` + `iat`.
- `activeOrganizationId` est un champ de **session** (positionné par `organization.setActiveOrganization`),
  pas un champ user. D'où `session.activeOrganizationId`.
- Pour lire l'user validé dans une fonction : `await authComponent.getAuthUser(ctx)` (throw si
  absent) ou `safeGetAuthUser(ctx)` (retourne `null`). `.userId` = id table user Better Auth.
  `ctx.auth.getUserIdentity()` marche aussi : `.subject` = userId, et les claims custom du JWT
  (dont `activeOrganizationId`) sont accessibles sur l'objet identity.

---

## 7. `convex({ jwt: { definePayload } })` — injection de `activeOrganizationId`

Le JWT custom permet à Convex de scoper sans round-trip DB. Forme générale (extrait §6) :

```typescript
convex({
  authConfig,
  jwt: {
    expirationSeconds: 60 * 30, // optionnel
    definePayload: ({ user, session }) => ({
      email: user.email,
      name: user.name,
      role: user.role,
      activeOrganizationId: session.activeOrganizationId ?? null,
      // sessionId + iat auto-ajoutés
    }),
  },
});
```

Côté fonction Convex, le claim arrive sur l'identity :

```typescript
const identity = await ctx.auth.getUserIdentity();
const orgId = (identity as any).activeOrganizationId as string | undefined;
```

> Gotcha JWT cache : après `signIn`, `signOut`, ou changement d'org active, **recharger la page**
> (`window.location.href = ...`) pour propager le nouveau JWT à Convex.

---

## 8. `convex/http.ts` — mount `/api/auth/*`

```typescript
// convex/http.ts
import { httpRouter } from "convex/server";
import { authComponent, createAuth } from "./auth";

const http = httpRouter();

// CORS obligatoire pour les frameworks client-side (TanStack Start).
authComponent.registerRoutes(http, createAuth, { cors: true });

export default http;
```

Variante "lazy" (recommandée pour grosses apps — évite des OOM au deploy en n'initialisant pas
Better Auth pendant l'enregistrement des routes) :

```typescript
authComponent.registerRoutesLazy(http, createAuth, {
  basePath: "/api/auth",     // défaut
  cors: true,
  trustedOrigins: [process.env.SITE_URL!],
});
```

> Plus de `http.route({ pathPrefix: '/api/auth/' })` manuel : `registerRoutes` s'en charge.

---

## 9. Proxy front (TanStack Start)

### 9.1 `src/lib/auth-server.ts` — helpers SSR/serveur

```typescript
// src/lib/auth-server.ts
import { convexBetterAuthReactStart } from '@convex-dev/better-auth/react-start'

export const {
  handler,            // handler serveur des routes /api/auth/*
  getToken,           // récupère le token depuis les cookies (SSR)
  fetchAuthQuery,
  fetchAuthMutation,
  fetchAuthAction,
} = convexBetterAuthReactStart({
  convexUrl: process.env.VITE_CONVEX_URL!,
  convexSiteUrl: process.env.VITE_CONVEX_SITE_URL!,  // ⚠ .site, pas .cloud
  // basePath: "/api/auth",  // défaut
})
```

### 9.2 `src/routes/api/auth.$.ts` — route proxy

```typescript
// src/routes/api/auth.$.ts
import { createFileRoute } from '@tanstack/react-router'
import { reactStartHandler } from '@convex-dev/better-auth/react-start'
import { handler } from '~/lib/auth-server'

export const Route = createFileRoute('/api/auth/$')({
  server: {
    handlers: {
      // reactStartHandler gère les routes client-side ; handler gère le serveur.
      GET: ({ request }) => handler(request),
      POST: ({ request }) => handler(request),
    },
  },
})
```

> ⚠ Si le fichier n'exporte pas `Route`, le router-plugin l'**ignore silencieusement**
> (warning « does not export a Route »). Toujours exporter `Route`.

### 9.3 Vite SSR config

```typescript
// vite.config.ts
export default defineConfig({
  ssr: {
    noExternal: ['@convex-dev/better-auth'],
  },
  // ... tanstackStart() plugin, etc.
});
```

### 9.4 Router context (SSR auth) — `src/router.tsx`

```typescript
const convexQueryClient = new ConvexQueryClient(convexUrl, { expectAuth: true })
```

### 9.5 Root route — provider + token SSR (extrait)

```typescript
// src/routes/__root.tsx
import { createServerFn } from '@tanstack/react-start'
import { ConvexBetterAuthProvider } from '@convex-dev/better-auth/react'
import { getToken } from '~/lib/auth-server'
import { authClient } from '~/lib/auth-client'

const getAuth = createServerFn({ method: 'GET' }).handler(async () => getToken())

// dans beforeLoad :
//   const token = await getAuth()
//   if (token) ctx.context.convexQueryClient.serverHttpClient?.setAuth(token)
//   return { isAuthenticated: !!token, token }

function RootComponent() {
  const context = useRouteContext({ from: Route.id })
  return (
    <ConvexBetterAuthProvider
      client={context.convexQueryClient.convexClient}
      authClient={authClient}
      initialToken={context.token}
    >
      <RootDocument><Outlet /></RootDocument>
    </ConvexBetterAuthProvider>
  )
}
```

> Rappel rule TanStack : éviter de wrapper les pages publiques (storefront, login) dans le
> provider si elles n'ont pas besoin d'auth — scoper le provider à `/app/*` quand c'est possible.

---

## 10. `src/lib/auth-client.ts` — client (organizationClient + adminClient + phoneNumberClient + convexClient)

```typescript
// src/lib/auth-client.ts
import { createAuthClient } from 'better-auth/react'
import {
  organizationClient,
  adminClient,
  phoneNumberClient,
} from 'better-auth/client/plugins'
import { convexClient } from '@convex-dev/better-auth/client/plugins'

export const authClient = createAuthClient({
  // baseURL non requis si le proxy /api/auth/* est sur la même origine
  plugins: [
    organizationClient(),
    adminClient(),
    phoneNumberClient(),
    convexClient(),     // toujours présent côté client
  ],
})

export const {
  signIn,
  signOut,
  useSession,
  organization,    // organization.create, .setActive, .inviteMember, ...
  admin,           // admin.impersonateUser, .listUsers, ...
  phoneNumber,     // phoneNumber.sendOtp, .verify, ...
} = authClient
```

### Flux login OTP côté client (KALGA)

```typescript
// 1. demander l'OTP (déclenche sendOTP serveur → bridge WhatsApp)
await authClient.phoneNumber.sendOtp({ phoneNumber: "+2250141540178" })

// 2. vérifier le code reçu sur WhatsApp
const { error } = await authClient.phoneNumber.verify({
  phoneNumber: "+2250141540178",
  code: "123456",
})
if (!error) window.location.href = "/app"   // reload → propage le JWT à Convex
```

### Sélection de l'organisation active (scoping)

```typescript
await authClient.organization.setActive({ organizationId: orgId })
window.location.href = "/app"   // reload pour re-générer le JWT avec activeOrganizationId
```

---

## 11. Sender OTP custom → bridge WhatsApp (endpoint HTTP externe)

Le plugin `phoneNumber` appelle `sendOTP({ phoneNumber, code })` côté serveur Convex. KALGA y
branche un `fetch` vers le **bridge WhatsApp** (Node/Baileys, port 3001 en dev).

### 11.1 Côté Convex (`createAuth`, déjà dans §6)

```typescript
phoneNumber({
  signUpOnVerification: {
    getTempEmail: (phone) => `${phone}@kalga.local`,
    getTempName: (phone) => phone,
  },
  sendOTP: async ({ phoneNumber, code }) => {
    const bridge = process.env.WHATSAPP_BRIDGE_URL; // ex: http://localhost:3001 (dev)
    const res = await fetch(`${bridge}/api/send-otp`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // secret partagé pour que le bridge n'accepte que Convex
        "x-kalga-internal": process.env.WA_BRIDGE_SECRET ?? "",
      },
      body: JSON.stringify({
        to: phoneNumber,            // format E.164, ex: +2250141540178
        text: `Votre code KALGA : ${code}. Valable 5 minutes.`,
      }),
    });
    if (!res.ok) {
      throw new Error(`Bridge WhatsApp OTP failed: ${res.status}`);
    }
  },
})
```

### 11.2 Env vars Convex requises pour le sender

```bash
npx convex env set WHATSAPP_BRIDGE_URL http://localhost:3001
npx convex env set WA_BRIDGE_SECRET <secret-partagé>
```

> En PROD : le bridge n'est PAS exposé publiquement (port 3001 localhost-only).
> Comme `sendOTP` tourne sur Convex (cloud), il faut une URL atteignable depuis Convex :
> exposer un endpoint dédié `/api/send-otp` derrière l'API publique (proxy déjà en place côté
> kalga-api : pattern `/api/wa`), protégé par `WA_BRIDGE_SECRET`. Ne JAMAIS ouvrir le 3001 brut.

### 11.3 Côté bridge (Node/Express, à implémenter)

```javascript
// kalga-whatsapp/src/api/otp.js (exemple)
router.post('/api/send-otp', (req, res) => {
  if (req.headers['x-kalga-internal'] !== process.env.WA_BRIDGE_SECRET) {
    return res.status(401).json({ error: 'unauthorized' });
  }
  const { to, text } = req.body;
  // jid WhatsApp : <e164-sans-+>@s.whatsapp.net
  const jid = `${to.replace(/^\+/, '')}@s.whatsapp.net`;
  sock.sendMessage(jid, { text });
  res.json({ ok: true });
});
```

---

## 12. `convex/lib/withOrg.ts` — helper scoping multi-tenant

Empêche les fuites cross-tenant : toute query/mutation métier passe par `withOrg`.

```typescript
// convex/lib/withOrg.ts
import type { GenericMutationCtx, GenericQueryCtx } from "convex/server";
import type { DataModel } from "../_generated/dataModel";

type AnyCtx = GenericQueryCtx<DataModel> | GenericMutationCtx<DataModel>;
export type OrgContext<Ctx> = Ctx & {
  orgId: string;
  userId: string;
  role: string;
};

export async function withOrg<Ctx extends AnyCtx, T>(
  ctx: Ctx,
  fn: (octx: OrgContext<Ctx>) => Promise<T>,
): Promise<T> {
  const identity = await ctx.auth.getUserIdentity();
  if (!identity) throw new Error("Unauthenticated");

  const orgId = (identity as { activeOrganizationId?: string }).activeOrganizationId;
  if (!orgId) throw new Error("No active organization");

  return fn({
    ...ctx,
    orgId,
    userId: identity.subject,                    // userId Better Auth
    role: (identity as { role?: string }).role ?? "user",
  } as OrgContext<Ctx>);
}
```

### Usage (toujours indexer par org)

```typescript
// convex/products.ts
import { query } from "./_generated/server";
import { withOrg } from "./lib/withOrg";

export const list = query({
  args: {},
  handler: (ctx) =>
    withOrg(ctx, (octx) =>
      octx.db
        .query("products")
        .withIndex("by_org", (q) => q.eq("organizationId", octx.orgId))
        .collect()
    ),
});
```

> Schéma : chaque table métier doit avoir `organizationId: v.string()` + un index `by_org`.
> Le champ correspond à l'`organization.id` Better Auth (table du composant local).

---

## 13. Anti-patterns à bloquer (review)

1. ❌ Utiliser l'install par défaut avec `organization`/`admin` → `ArgumentValidationError .model "organization"`. Local Install obligatoire.
2. ❌ `import { betterAuth } from "better-auth"` au lieu de `"better-auth/minimal"` (API 0.10+).
3. ❌ `convexAdapter(...)` (ancien) au lieu de `authComponent.adapter(ctx)`.
4. ❌ Mount HTTP manuel `http.route({ pathPrefix })` au lieu de `registerRoutes`/`registerRoutesLazy`.
5. ❌ Plugin `convex({})` pas en dernier dans la liste `plugins`.
6. ❌ Oublier `definePayload.activeOrganizationId` → toutes les mutations `withOrg` échouent « No active organization ».
7. ❌ `ctx.db.query(...)` direct dans une fonction métier sans `withOrg` → fuite cross-tenant.
8. ❌ `signIn`/`signOut`/`setActive` sans reload → JWT périmé en cache, Convex garde l'ancienne session.
9. ❌ Exposer le bridge WhatsApp (3001) publiquement pour `sendOTP` → passer par l'API publique + secret partagé.
10. ❌ Oublier de re-générer `generatedSchema.ts` après ajout d'un plugin → tables manquantes.
11. ❌ `convexSiteUrl` en `.cloud` au lieu de `.site` dans `auth-server.ts`.
12. ❌ Route `api/auth.$.ts` qui n'exporte pas `Route` → ignorée silencieusement.
13. ❌ Mettre du code (autre que `export const auth`) dans `convex/betterAuth/auth.ts` → erreurs runtime à la génération.

---

## 14. Checklist d'install (ordre)

1. `npm i @convex-dev/better-auth @convex-dev/react-query better-auth@1.5.3 convex@latest`
2. `npx convex dev --once` (env générées)
3. `npx convex env set BETTER_AUTH_SECRET=$(openssl rand -base64 32)` + `SITE_URL` + `WHATSAPP_BRIDGE_URL` + `WA_BRIDGE_SECRET`
4. `convex/betterAuth/convex.config.ts` (`defineComponent`)
5. `convex/convex.config.ts` (`app.use` du composant local)
6. `convex/auth.config.ts` (provider)
7. `convex/auth.ts` (`createClient` + `createAuth` avec org/admin/phone, schéma local)
8. `convex/betterAuth/auth.ts` (export `auth` statique) → `cd convex/betterAuth && npx auth generate --output generatedSchema.ts`
9. `convex/betterAuth/schema.ts` (ré-export)
10. `convex/http.ts` (`registerRoutes(..., { cors: true })`)
11. `convex/lib/withOrg.ts`
12. Front : `src/lib/auth-server.ts`, `src/lib/auth-client.ts`, `src/routes/api/auth.$.ts`, `vite.config.ts` (ssr.noExternal), `__root.tsx` (provider + token SSR), `router.tsx` (`expectAuth: true`)
13. Bridge : endpoint `/api/send-otp` protégé par `WA_BRIDGE_SECRET`

---

## 15. Sources

- https://labs.convex.dev/better-auth/features/local-install
- https://labs.convex.dev/better-auth/local-install
- https://labs.convex.dev/better-auth/framework-guides/tanstack-start
- https://labs.convex.dev/better-auth/framework-guides/react
- https://labs.convex.dev/better-auth/api/convex-plugin (definePayload)
- https://labs.convex.dev/better-auth/api/component-client (registerRoutes/Lazy, getAuth)
- https://labs.convex.dev/better-auth/supported-plugins
- https://labs.convex.dev/better-auth/migrations/migrate-to-0-10 (reactStartHandler, getToken)
- https://labs.convex.dev/better-auth/basic-usage/authorization
