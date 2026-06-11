# 🏛️ ARCHITECTURE FRONTEND KALGA

> **Document de référence officiel.** À consulter pour valider tout choix d'implémentation.
> Toute déviation de ce document doit être justifiée et documentée.

**Version** : 1.1
**Statut** : Référence active
**Dernière mise à jour** : Juin 2026

> **Changelog v1.1** : retrait de Pinia (état global → composables + TanStack
> Query, cf. déviation §2) ; suppression des dossiers `stores/` ; correction
> `tailwind.config.ts` → `@theme inline` (Tailwind v4).

---

## 📑 Sommaire

1. [Objectif du document](#1-objectif-du-document)
2. [Stack technique validée](#2-stack-technique-validée)
3. [Vue d'ensemble](#3-vue-densemble)
4. [Structure des dossiers](#4-structure-des-dossiers)
5. [Principes de design](#5-principes-de-design)
6. [Conventions de nommage](#6-conventions-de-nommage)
7. [Patterns appliqués](#7-patterns-appliqués)
8. [Aliases & imports](#8-aliases--imports)
9. [Workflows standards](#9-workflows-standards)
10. [Anti-patterns à éviter](#10-anti-patterns-à-éviter)
11. [Checklist de validation](#11-checklist-de-validation)
12. [Sources & références](#12-sources--références)

---

## 1. Objectif du document

Ce document est la **source unique de vérité** sur l'architecture frontend de KALGA.

### À quoi il sert
- **Pour le dev (toi)** : référence à consulter pour ne pas dériver
- **Pour valider le code livré** : checklist pour vérifier la conformité
- **Pour les futurs collaborateurs** : onboarding rapide sur l'architecture
- **Pour les revues** : critère objectif (« cette PR respecte-t-elle l'archi ? »)

### Comment l'utiliser
1. **Avant chaque nouvelle feature** : relire la section 7 (patterns) et 9 (workflows)
2. **Avant chaque commit** : vérifier la section 11 (checklist)
3. **En cas de doute sur où mettre un fichier** : section 4 (structure)
4. **Si tu vois Claude (moi) dévier** : me pointer la section concernée

---

## 2. Stack technique validée

### Le cœur

| Couche | Techno | Version cible | Pourquoi |
|---|---|---|---|
| Framework full-stack | **Nuxt** | 4.x | Hybrid rendering (SSG + SSR), conventions strong, écosystème mature |
| UI Library | **Vue** | 3.5+ | Composition API + Vapor mode optionnel |
| Langage | **TypeScript** | 5.6+ strict | Type safety bloque les bugs avant prod |
| Style | **Tailwind CSS** | v4 | Utility-first, build ultra rapide |
| Composants UI | **shadcn-vue** (via module **shadcn-nuxt**) | latest | Accessibles par défaut, copy-paste, customisables — `shadcn-nuxt` encapsule l'intégration Nuxt |
| Composables UI | **VueUse** | latest | Hooks Vue standardisés |

### Data & State

| Couche | Techno | Pourquoi |
|---|---|---|
| Data fetching | **TanStack Query Vue** | Cache, refetch auto, optimistic mutations |
| État serveur | **TanStack Query Vue** | Le cache de queries EST le state des données distantes |
| État global UI | **Composables Vue** (`ref`/`computed` partagés) | Suffisant pour modal/sidebar/theme ; pas de dépendance supplémentaire |
| Validation runtime | **Zod** | Schémas partagés client/serveur |

> **⚠️ Déviation documentée — Pinia retiré (Juin 2026).**
> La v1.0 de ce document imposait **Pinia** comme store global. Pinia a été
> **désinstallé** pour deux raisons : (1) un crash SSR dû à un peer-mismatch
> `pinia` ↔ `@nuxtjs/i18n` 10.x, et (2) le code n'a **aucun** `defineStore` —
> tout l'état distant passe par TanStack Query et l'état UI local par des
> composables. Réintroduire Pinia ramènerait le bug sans bénéfice.
> **Conséquence** : plus de dossiers `stores/` (ni transverse, ni par feature).
> Si un vrai besoin d'état global complexe émerge, réévaluer Pinia **et**
> mettre à jour ce document avant de l'ajouter.

### Auth & sécurité

| Couche | Techno | Pourquoi |
|---|---|---|
| Auth client | **Nuxt Auth Utils** (`nuxt-auth-utils`) | Intégré, sessions cookies HttpOnly natif. À installer : `pnpm add nuxt-auth-utils` |
| Tokens | **HttpOnly cookies** | Inaccessibles depuis JS = pas de vol XSS |
| CSRF protection | Nitro built-in | Couvert par Nuxt out of the box |
| Sanitization | Vue auto-escape | Pas de `v-html` sauf cas validé |

### i18n & accessibilité

| Couche | Techno | Pourquoi |
|---|---|---|
| Internationalisation | **@nuxtjs/i18n** | Le plus mature, RTL natif (arabe) |
| Langues cibles V1 | FR (défaut), EN, AR | Côte d'Ivoire + expansion régionale |
| A11y | shadcn-vue + axe-core | WCAG AA par défaut |

### PWA & mobile

| Couche | Techno | Pourquoi |
|---|---|---|
| PWA | **@vite-pwa/nuxt** | Service worker, manifest, offline cache |
| Wrap natif (optionnel V2) | **Capacitor** | Si Play Store / App Store |

### Tests & qualité

| Couche | Techno | Couverture cible |
|---|---|---|
| Tests unitaires | **Vitest** | ≥80% sur composables et utils |
| Tests composants | **@vue/test-utils** + Vitest | Composants critiques de chaque feature |
| Tests E2E | **Playwright** | Flux critiques (login, vente, activation) |
| Linting | **ESLint 9** + plugin Vue | 0 erreur autorisée |
| Formatting | **Prettier** | Auto sur save |
| Type checking | `vue-tsc` strict | 0 erreur autorisée |

### Observabilité & hosting

| Couche | Techno | Pourquoi |
|---|---|---|
| Error tracking | **Sentry** | 5k events/mois gratuits, source maps |
| Hosting | **Cloudflare Pages** | Free, edge global, builds illimités |
| Analytics | Cloudflare Web Analytics | Privacy-first, gratuit |

---

## 3. Vue d'ensemble

### Approche : Feature-Based avec inspirations FSD

**Pourquoi pas FSD strict** : sur-dimensionné pour solo dev.
**Pourquoi pas structure plate** : devient ingérable à 50+ composants.
**Compromis choisi** : organisation par **feature métier** + couches transverses claires.

### Les 3 zones de l'application (1 seul projet Nuxt)

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   ZONE PUBLIQUE              ZONE MARCHAND      ZONE ADMIN  │
│   (storefront)               (dashboard)        (admin)     │
│                                                             │
│   /                          /dashboard/*       /admin/*    │
│   /boutique/[phone]                                         │
│   /produit/[code]                                           │
│   /commander/[code]                                         │
│                                                             │
│   Rendu : SSG (statique)    Rendu : SSR        Rendu : SSR  │
│   Auth  : non                Auth  : marchand   Auth : admin│
│   Cache : CDN Cloudflare     Cache : per-req   Cache : non  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Flow de données général

```
[ Browser ]
    │
    │ HTTP/HTTPS
    ▼
[ Cloudflare Pages CDN ] ──── pages statiques SSG
    │
    │ (pour routes SSR)
    ▼
[ Nuxt Nitro Server ]
    │
    ├─→ /server/api/auth/*       (auth interne, HttpOnly cookies)
    ├─→ /server/api/proxy/*      (proxy vers FastAPI Python)
    │
    ▼
[ FastAPI Python ] ──── kalga-api existant
```

---

## 4. Structure des dossiers

### Arborescence complète

```
kalga-frontend/
│
├── app/                              # 📁 Code applicatif Nuxt 4
│   │
│   ├── assets/                       # Sources non-publiques (CSS, fonts)
│   │   ├── css/
│   │   │   └── tailwind.css         # Tailwind v4 + tokens shadcn
│   │   └── fonts/
│   │
│   ├── components/                   # 🧩 Composants UI
│   │   ├── ui/                       # shadcn-vue (généré par CLI)
│   │   ├── layout/                   # Headers, sidebars, footers
│   │   └── shared/                   # Génériques (Card, EmptyState, ...)
│   │
│   ├── features/                     # 🎯 ORGANISATION PAR FEATURE
│   │   ├── auth/
│   │   │   ├── components/           # Spécifiques à la feature
│   │   │   ├── composables/          # Hooks Vue (état + data fetching)
│   │   │   ├── api.ts                # Appels API de la feature
│   │   │   ├── types.ts              # Types TypeScript
│   │   │   └── schemas.ts            # Schémas Zod
│   │   │
│   │   ├── products/
│   │   ├── conversations/
│   │   ├── merchants/
│   │   ├── activations/
│   │   ├── stock/
│   │   ├── stats/
│   │   └── storefront/
│   │
│   ├── composables/                  # 🔧 Composables transverses
│   │   ├── useApi.ts
│   │   ├── useToast.ts
│   │   └── useTheme.ts
│   │
│   ├── layouts/                      # 🎨 Layouts Nuxt
│   │   ├── default.vue               # Public storefront
│   │   ├── dashboard.vue             # Marchand
│   │   ├── admin.vue                 # Admin
│   │   └── empty.vue                 # Auth/login
│   │
│   ├── middleware/                   # 🛡️ Auth & permissions
│   │   ├── auth.global.ts
│   │   ├── merchant.ts
│   │   └── admin.ts
│   │
│   ├── pages/                        # 🚦 Routes (file-based)
│   │   ├── index.vue
│   │   ├── login.vue
│   │   │
│   │   ├── boutique/
│   │   │   ├── [phone].vue
│   │   │   └── produit/[code].vue
│   │   │
│   │   ├── dashboard/
│   │   │   ├── index.vue
│   │   │   ├── produits/
│   │   │   ├── conversations/
│   │   │   ├── stats/
│   │   │   └── parametres/
│   │   │
│   │   └── admin/
│   │       ├── index.vue
│   │       ├── marchands/
│   │       ├── activations/
│   │       └── audit-logs/
│   │
│   ├── plugins/                      # 🔌 Plugins Nuxt
│   │   ├── sentry.client.ts
│   │   └── pwa.client.ts
│   │
│   ├── types/                        # 🏷️ Types globaux
│   │   ├── api.ts
│   │   ├── domain.ts
│   │   └── env.d.ts
│   │
│   ├── utils/                        # 🛠️ Helpers purs (sans état)
│   │   ├── format.ts
│   │   ├── validation.ts
│   │   └── constants.ts
│   │
│   ├── error.vue                     # Page erreur globale
│   └── app.vue                       # Root component
│
├── public/                           # 📦 Assets publics statiques
│   ├── favicon.svg
│   └── icons/                        # PWA icons multiple sizes
│                                     # ⚠️ Le manifest.webmanifest est généré
│                                     # automatiquement par @vite-pwa/nuxt depuis
│                                     # nuxt.config.ts (pas de fichier statique)
│
├── server/                           # 🖥️ API server-side Nuxt
│   ├── api/
│   │   ├── auth/
│   │   │   ├── login.post.ts
│   │   │   ├── logout.post.ts
│   │   │   └── me.get.ts
│   │   └── proxy/
│   │       └── [...path].ts
│   ├── middleware/
│   │   └── ratelimit.ts
│   └── utils/
│       └── auth.ts
│
├── tests/                            # 🧪 Tests
│   ├── unit/
│   │   ├── features/
│   │   └── utils/
│   └── e2e/
│       ├── login.spec.ts
│       └── product-flow.spec.ts
│
├── i18n/                             # 🌍 Traductions
│   ├── locales/
│   │   ├── fr.json
│   │   ├── ar.json
│   │   └── en.json
│   └── i18n.config.ts
│
├── .env.example                      # Template
├── .gitignore
├── eslint.config.mjs                 # ESLint 9 flat config (remplace .eslintrc.cjs)
├── .prettierrc
├── components.json                   # Config shadcn-vue CLI
├── nuxt.config.ts                    # Config Nuxt
├── package.json
├── README.md
└── tsconfig.json                     # strict: true obligatoire
```

> **Note Tailwind v4** : pas de `tailwind.config.ts`. La configuration et les
> tokens design vivent dans `app/assets/css/tailwind.css` via la directive
> `@theme inline` (nouveau modèle CSS-first de Tailwind v4).

### Description rôle de chaque dossier

#### `app/components/`
**Règle d'or** : un composant ici est UTILISABLE PAR PLUSIEURS FEATURES.

- **`ui/`** : composants shadcn-vue purs (Button, Dialog, Input, ...). Générés via `pnpm dlx shadcn-vue@latest add button`. Ne JAMAIS modifier ces fichiers manuellement après génération sauf cas exceptionnel documenté.
- **`layout/`** : composants de mise en page (header, sidebar, footer). Spécifiques à une zone (public/marchand/admin) mais réutilisés à travers les pages.
- **`shared/`** : composants génériques liés au métier KALGA (logo, états vides, loaders), réutilisés dans plusieurs features.

#### `app/features/<feature-name>/`
**Règle d'or** : tout ce qui concerne UNE seule feature métier vit ici.

Structure standard d'une feature (les 2 sous-dossiers `components/` et `composables/` sont **toujours présents** pour la cohérence du scaffold, même si vides au démarrage — un `.gitkeep` les versionne) :
```
features/products/
├── components/           # Composants UI spécifiques à cette feature
├── composables/          # Logique réactive : état (ref/computed) + data fetching (TanStack Query)
├── api.ts                # Fonctions appelant l'API backend
├── types.ts              # Interfaces TypeScript de la feature
└── schemas.ts            # Schémas Zod pour validation
```

**Quand créer une feature** : dès qu'un domaine métier a >2 composants OU >3 endpoints API.

#### `app/composables/`
Composables **transverses**, pas liés à une feature métier (`useApi`, `useToast`, `useTheme`).
C'est aussi ici (ou dans `features/<x>/composables/`) que vit l'**état global UI**
(modal, sidebar, theme) via des `ref`/`computed` partagés — pas de store dédié.

#### `app/middleware/`
Vérifications avant qu'une route soit affichée. **Auth = ici**.

#### `app/pages/`
Routing file-based de Nuxt. **Une page = un composant orchestrateur** qui appelle les composants de features. Pas de logique métier dans les pages.

#### `app/types/`
- `domain.ts` : types du métier KALGA (Merchant, Product, Conversation, ...). **Source unique de vérité**.
- `api.ts` : types génériques d'API (ApiResponse, ApiError, Pagination).
- `env.d.ts` : variables d'env typées.

#### `app/utils/`
**Fonctions pures sans état** uniquement. `formatPrice`, `formatDate`, `escapeHtml`, etc.
**Test obligatoire** : 100% des fonctions de `utils/` doivent être testées.

#### `server/api/`
Endpoints server-side de Nuxt (côté Nitro). Servent à :
- Auth interne (poser/lire HttpOnly cookies)
- Proxy vers le backend FastAPI Python (cache la clé API interne)
- Rate limiting

#### `server/api/proxy/[...path].ts`
**Proxy unique** vers l'API FastAPI Python. Toutes les requêtes vers `/api/proxy/products` sont relayées vers `http://kalga-api:8001/api/products`. La clé `INTERNAL_API_KEY` est injectée serveur-side, jamais exposée au browser.

---

## 5. Principes de design

### 5.1. Separation of Concerns (SoC)

Chaque dossier a **UN rôle** :
| Dossier | Rôle |
|---|---|
| `components/ui/` | Présentation pure (pas de logique métier) |
| `composables/` | Logique réutilisable + état (local et global UI) |
| `utils/` | Fonctions pures |
| `server/api/` | Endpoints serveur |
| `middleware/` | Gardes de route |

### 5.2. Feature Cohesion

**Tout ce qui concerne une feature métier dans UN dossier.**
Avantages :
- Suppression d'une feature = suppression d'un dossier (zéro fichier orphelin)
- Onboarding rapide : « tu touches aux produits ? ouvre `features/products/` »
- Tests groupés par feature

### 5.3. Dependency Direction

**Flux unidirectionnel** :
```
pages/  ──→  features/  ──→  composables/  ──→  utils/
              │
              ↓
        components/ui/
```

**Règles strictes** :
- `utils/` ne dépend de RIEN d'autre que de packages npm
- `composables/` peut utiliser `utils/` et `types/` uniquement
- `features/` peut utiliser `composables/`, `utils/`, `types/`, `components/`
- `pages/` peut tout utiliser
- **Aucune dépendance circulaire autorisée**

### 5.4. Single Source of Truth (SSOT)

| Donnée | Source unique |
|---|---|
| Types domaine | `app/types/domain.ts` |
| Constantes magiques | `app/utils/constants.ts` |
| Tokens design | `assets/css/tailwind.css` (`@theme inline`, Tailwind v4) |
| Config API URL | `runtimeConfig` dans `nuxt.config.ts` |
| Traductions | `i18n/locales/<lang>.json` |

### 5.5. Convention over Configuration

On exploite les conventions Nuxt 4 :
- Auto-import : `components/`, `composables/`, `utils/`
- File-based routing : `pages/`
- File-based middleware : `middleware/`
- File-based API : `server/api/`

→ **Jamais d'`import` manuel pour ces dossiers.**

### 5.6. Composition over Inheritance

- **Pas d'héritage de classes Vue** (mixins, extends)
- **Composition API uniquement** (`<script setup>`)
- **Composables = unité de réutilisation** de logique
- **Composants = unité de réutilisation** d'UI

### 5.7. Type Safety First

- `tsconfig.json` : `strict: true` + `noUncheckedIndexedAccess: true` obligatoires
- **Zéro `any` autorisé** sauf cas documenté avec `// @ts-expect-error: reason`
- Tous les params API typés via Zod
- Toutes les props de composants typées

---

## 6. Conventions de nommage

### Fichiers

| Type | Convention | Exemple |
|---|---|---|
| Composants Vue | `PascalCase.vue` | `ProductCard.vue` |
| Composables | `useNom.ts` (camelCase) | `useProducts.ts` |
| Pages | `kebab-case.vue` | `mes-produits.vue` |
| Routes dynamiques | `[param].vue` | `[code].vue` |
| Utils | `camelCase.ts` | `format.ts` |
| Types | `camelCase.ts` | `domain.ts` |
| Tests | `<source>.test.ts` ou `.spec.ts` | `format.test.ts` |
| Server routes | `<verb>.ts` | `login.post.ts` |

### Code

| Type | Convention | Exemple |
|---|---|---|
| Variables/fonctions | camelCase | `formatPrice` |
| Constantes | UPPER_SNAKE_CASE | `MAX_PRODUCT_NAME_LEN` |
| Types/interfaces | PascalCase | `interface Product` |
| Enums | PascalCase + valeurs UPPER | `enum Role { ADMIN, MERCHANT }` |
| Composants dans templates | PascalCase | `<ProductCard />` |
| Props events | kebab-case | `@product-selected` |
| CSS classes Tailwind | utility classes | `flex items-center gap-2` |
| Composable d'état partagé | `useXxx` | `useAuth`, `useToast` |

### Commit messages

Format **Conventional Commits** :
```
<type>(<scope>): <description>

type  : feat | fix | refactor | docs | test | chore | style | perf
scope : storefront | dashboard | admin | auth | products | ...
```

Exemples :
```
feat(products): add variant management UI
fix(auth): handle expired token refresh
refactor(auth): split useAuth into useAuth + useSession
test(utils): cover formatPrice edge cases
```

---

## 7. Patterns appliqués

### 7.1. Auth & permissions

**Auth flow** :
1. User soumet login form → POST `/api/auth/login` (server route Nuxt)
2. Server route appelle FastAPI → reçoit JWT
3. Server route pose le JWT en **HttpOnly cookie** + retourne user info
4. Browser n'a JAMAIS accès au token JS-side
5. Requêtes suivantes : cookie auto-envoyé, server route lit/proxy

**Middleware** :
```typescript
// app/middleware/merchant.ts
export default defineNuxtRouteMiddleware(() => {
  const { user } = useAuth()
  if (!user.value) return navigateTo('/login')
})

// app/middleware/admin.ts
export default defineNuxtRouteMiddleware(() => {
  const { user } = useAuth()
  if (user.value?.role !== 'admin') return navigateTo('/dashboard')
})
```

**Application** :
```typescript
// nuxt.config.ts
routeRules: {
  '/dashboard/**': { ssr: true, appMiddleware: ['merchant'] },
  '/admin/**': { ssr: true, appMiddleware: ['merchant', 'admin'] }
}
```

### 7.2. Data fetching

**Pattern obligatoire : TanStack Query Vue**

```typescript
// app/features/products/composables/useProducts.ts
import { useQuery } from '@tanstack/vue-query'
import { productsApi } from '../api'

export function useProducts() {
  return useQuery({
    queryKey: ['products'],
    queryFn: productsApi.list,
    staleTime: 60_000  // 1 min
  })
}
```

**Pourquoi** :
- Cache automatique
- Refetch on focus
- Retry exponentiel
- Optimistic updates
- DevTools intégré

**À NE PAS faire** : `fetch()` direct dans un composant.

### 7.3. State management

**Décision par cas** :

| Type d'état | Outil |
|---|---|
| État local d'un composant | `ref()` / `reactive()` |
| État partagé entre 2-3 composants proches | `provide`/`inject` |
| État du serveur (API data) | TanStack Query |
| État global UI (modal, sidebar, theme) | Composable partagé (`ref`/`computed` au scope module) dans `app/composables/` |
| État global d'une feature | Composable partagé dans `features/<x>/composables/` |

> Pas de Pinia (cf. déviation documentée §2). Un composable qui déclare ses
> `ref` **hors** de la fonction (scope module) fournit un singleton réactif
> partagé — équivalent léger d'un store pour nos besoins.

**À NE PAS faire** : `localStorage` direct (sauf pour persistance theme/locale).

### 7.4. Validation runtime

**Pattern obligatoire : Zod sur les frontières**

```typescript
// app/features/products/schemas.ts
import { z } from 'zod'

export const productSchema = z.object({
  name: z.string().min(2).max(100),
  price: z.number().int().positive(),
  min_price: z.number().int().positive()
}).refine(d => d.min_price <= d.price, {
  message: 'Le prix minimum doit être <= prix de vente'
})

export type Product = z.infer<typeof productSchema>
```

**Où valider** :
- ✅ Formulaires utilisateur
- ✅ Réponses API entrantes (parse strict)
- ✅ Variables d'env au boot
- ❌ Pas dans la logique métier interne (trust internal code)

### 7.5. Organisation des composants

**3 niveaux** :

1. **shadcn primitives** (`components/ui/Button.vue`) — pure UI
2. **Composants de feature** (`features/products/components/ProductCard.vue`) — combinent les primitives + logique métier
3. **Pages** (`pages/dashboard/produits/index.vue`) — orchestrent les composants de features

**Règle** : un composant de page ne devrait jamais faire d'appel API direct. Délègue aux composables/features.

### 7.6. Tests

**Pyramide cible** :
```
      /\
     /E2E\         ~10% (flux critiques)
    /------\
   /Comps  \      ~30% (composants importants)
  /----------\
 / Unit (utils,\  ~60% (logique pure, composables)
/  composables) \
------------------
```

**Conventions** :
- Tests unitaires : à côté du fichier source (`format.ts` → `format.test.ts`) OU dans `tests/unit/` (au choix mais cohérent par feature)
- Tests E2E : toujours dans `tests/e2e/`
- Mock fetch via `vi.fn()`, jamais de vrai HTTP en unit
- Tests E2E utilisent l'API réelle locale via Docker

### 7.7. Internationalisation (i18n)

**Pattern** :
```vue
<template>
  <h1>{{ $t('products.title') }}</h1>
  <p>{{ $t('products.count', { n: total }) }}</p>
</template>
```

**Règles** :
- Toute chaîne visible utilisateur = traduite
- Clés en `kebab-case.nested.format`
- Traductions classées par feature : `products.*`, `auth.*`, `dashboard.*`
- Fallback : FR
- Arabe = RTL automatique via `dir="rtl"` sur `<html>`

### 7.8. PWA

**Manifest** :
```typescript
// nuxt.config.ts
pwa: {
  manifest: {
    name: 'KALGA',
    short_name: 'KALGA',
    theme_color: '#0E5E6F',
    background_color: '#ffffff',
    display: 'standalone',
    start_url: '/dashboard',
    icons: [
      { src: '/icons/192.png', sizes: '192x192', type: 'image/png' },
      { src: '/icons/512.png', sizes: '512x512', type: 'image/png' }
    ]
  }
}
```

**Stratégies de cache (Workbox)** :
- Assets (JS/CSS/images) : Cache First (offline-friendly)
- API GET : Network First avec fallback cache (max 5min)
- API POST/PUT/DELETE : Pas de cache

### 7.9. Error handling

**Errors handled at 3 levels** :

1. **Global** : `error.vue` capture les erreurs non-handled
2. **Per query** : TanStack Query `onError` → toast notification
3. **Per form** : Zod errors → affichage inline

**Reporting** : toutes les erreurs non-handled remontent à Sentry via plugin.

---

## 8. Aliases & imports

### Configuration TypeScript

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "paths": {
      "@/*":             ["./app/*"],
      "@/features/*":    ["./app/features/*"],
      "@/components/*":  ["./app/components/*"],
      "@/composables/*": ["./app/composables/*"],
      "@/types/*":       ["./app/types/*"],
      "@/utils/*":       ["./app/utils/*"],
      "~/*":             ["./*"]
    }
  }
}
```

### Règles d'import

| Source → Cible | Autorisé ? |
|---|---|
| `pages/` → `features/` | ✅ |
| `pages/` → `components/` | ✅ |
| `features/X/` → `features/Y/` | ❌ Une feature ne dépend pas d'une autre |
| `features/` → `composables/` (transverses) | ✅ |
| `features/` → `utils/` | ✅ |
| `components/ui/` → `utils/` | ❌ Les primitives shadcn restent pures |
| `utils/` → quoi que ce soit autre que npm | ❌ |
| `server/` ↔ `app/` | ❌ Ne JAMAIS importer côté server du code app/ |

### Auto-imports Nuxt

**Ces dossiers sont auto-importés** (PAS besoin d'`import`) :
- `app/components/**`
- `app/composables/**`
- `app/utils/**`

**Code propre attendu** :
```vue
<script setup lang="ts">
// ✅ Pas d'import nécessaire (auto)
const { user } = useAuth()
const { data: products } = useProducts()
const formatted = formatPrice(1500)
</script>
```

---

## 9. Workflows standards

### 9.1. Ajouter une nouvelle feature

1. **Créer le dossier** : `app/features/<nom>/`
2. **Squelette** :
   ```
   features/<nom>/
   ├── components/
   ├── composables/      # data fetching (TanStack Query) + état partagé éventuel
   ├── api.ts
   ├── schemas.ts
   └── types.ts
   ```
3. **Si la feature a des pages** : créer routes dans `app/pages/`
4. **Ajouter traductions** : `i18n/locales/*.json` sous la clé `<nom>.*`
5. **Tests** : `tests/unit/features/<nom>/`
6. **Commit** : `feat(<nom>): initial scaffolding`

> Note : l'état partagé d'une feature (s'il y en a) vit dans un composable de
> `composables/` qui déclare ses `ref` au scope module (singleton réactif).
> Pas de dossier `stores/` (cf. déviation Pinia §2).

### 9.2. Ajouter une page

1. **Créer le fichier** : `app/pages/<chemin>/<nom>.vue`
2. **Choisir le layout** : `<NuxtLayout name="dashboard">` etc.
3. **Définir le middleware si auth requise** :
   ```vue
   <script setup>
   definePageMeta({ middleware: 'merchant' })
   </script>
   ```
4. **Délégué la data à un composable** (pas de fetch direct)
5. **Délégué l'UI à des composants de feature**

### 9.3. Ajouter un composant shadcn

```bash
pnpm dlx shadcn-vue@latest add dialog
```

Le composant est généré dans `app/components/ui/dialog/`. Ne pas modifier directement, customiser via Tailwind dans l'usage.

### 9.4. Ajouter un appel API

1. **Créer la fonction** dans `features/<x>/api.ts` :
   ```typescript
   export const productsApi = {
     list: () => $fetch<Product[]>('/api/proxy/products'),
     create: (data: ProductInput) =>
       $fetch<Product>('/api/proxy/products', { method: 'POST', body: data })
   }
   ```
2. **Wrap dans un composable** :
   ```typescript
   export function useCreateProduct() {
     return useMutation({
       mutationFn: productsApi.create,
       onSuccess: () => queryClient.invalidateQueries(['products'])
     })
   }
   ```
3. **Schema Zod** pour valider la réponse si nécessaire

### 9.5. Ajouter une traduction

1. Ajouter la clé dans `i18n/locales/fr.json` (source)
2. Répliquer dans `en.json`, `ar.json`
3. Utiliser : `{{ $t('feature.key') }}`

---

## 10. Anti-patterns à éviter

### ❌ NE JAMAIS faire

| Anti-pattern | Pourquoi c'est mal | À la place |
|---|---|---|
| `localStorage.setItem('token', ...)` | XSS = vol immédiat | HttpOnly cookies via server route |
| `v-html="user.input"` | XSS direct | Vue auto-escape avec `{{ }}` |
| `fetch()` direct dans composant | Pas de cache, pas de retry, code dupliqué | TanStack Query via composable |
| `onclick="handler()"` inline | Code non testable, XSS surface | Event binding `@click="handler"` |
| `setInterval(...)` sans cleanup | Memory leak | `useIntervalFn` de VueUse |
| `console.log(token)` | Leak via extensions | Jamais. Sentry pour debug prod |
| URL hardcodée `http://localhost:8001` | Casse en prod | `useRuntimeConfig().public.apiUrl` |
| Fonction métier dans composant | Pas réutilisable, pas testable | Composable dans `features/` |
| Type `any` non documenté | Trou de type safety | Type précis ou `unknown` + narrowing |
| Composant > 200 lignes | Non maintenable | Split en sous-composants |
| Importer un truc d'une autre feature | Couplage fort | Extraire dans `composables/` transverses |
| `mixin` Vue | Code legacy, hard to trace | Composable |
| `Options API` (`data() { return... }`) | Style legacy Vue 2 | `<script setup>` |
| Logique dans le template | Difficile à lire/tester | Computed ou méthode |
| CSS inline avec `style="..."` | Pas de design system | Classes Tailwind |
| Magic numbers | Difficile à maintenir | Constantes dans `utils/constants.ts` |

### ⚠️ Réfléchir à deux fois avant de

- Créer un nouveau dossier de top-level dans `app/` (consulter ce doc)
- Importer un nouveau package npm (peser bundle size + maintenance)
- Modifier un composant `ui/` shadcn (préférer Tailwind override)
- Désactiver une règle ESLint (justifier en commentaire)
- Utiliser `// @ts-ignore` (préférer `// @ts-expect-error: reason`)

---

## 11. Checklist de validation

À utiliser **avant chaque commit** ou pour valider un code livré par moi (Claude).

### Code

- [ ] Fichier dans le bon dossier selon la section 4
- [ ] Convention de nommage respectée (section 6)
- [ ] Aucun anti-pattern de la section 10
- [ ] TypeScript sans erreur (`pnpm typecheck`)
- [ ] ESLint sans erreur (`pnpm lint`)
- [ ] Tests présents pour la logique non triviale
- [ ] Pas de `console.log` résiduel

### Sécurité

- [ ] Aucun token/secret dans le code client
- [ ] Pas de `v-html` non justifié
- [ ] Inputs utilisateur validés avec Zod
- [ ] Auth middleware appliqué sur `/dashboard/*` et `/admin/*`
- [ ] CORS configuré correctement

### Performance

- [ ] Pas de `setInterval`/`setTimeout` sans cleanup
- [ ] Images via `<NuxtImg>` (lazy + responsive auto)
- [ ] Composants lourds en `<LazyXyz>` si pas above-the-fold
- [ ] Pas de gros packages npm sans justification

### UX

- [ ] Texte visible utilisateur passé par `$t()`
- [ ] Loading state visible pendant les requêtes
- [ ] Erreurs affichées clairement (toast ou inline)
- [ ] Mobile testé (responsive Tailwind)
- [ ] A11y : composants shadcn utilisés correctement

### Tests

- [ ] Unit tests pour utils/composables modifiés
- [ ] E2E test pour nouveau flux critique
- [ ] Couverture utils ≥ 80%

---

## 12. Sources & références

### Documentation officielle

- [Nuxt 4 Documentation](https://nuxt.com/docs/4.x)
- [Vue 3 Documentation](https://vuejs.org/)
- [shadcn-vue Components](https://www.shadcn-vue.com/)
- [Tailwind CSS v4 Docs](https://tailwindcss.com/docs)
- [TanStack Query Vue](https://tanstack.com/query/latest/docs/framework/vue/overview)
- [Zod Validation](https://zod.dev/)
- [Nuxt i18n](https://i18n.nuxtjs.org/)
- [Vite PWA Nuxt](https://vite-pwa-org.netlify.app/frameworks/nuxt.html)

### Articles 2026 consultés pour cette architecture

- [Nuxt 4 in 2026: Complete Developer's Guide (Medium)](https://sadiqueali.medium.com/nuxt-4-in-2026-the-complete-developers-guide-1a6161462550)
- [A Better Way to Structure Large Nuxt Projects (DEV)](https://dev.to/orazch/a-better-way-to-structure-large-nuxt-projects-2j21)
- [Modular Architecture in Nuxt (DEV)](https://dev.to/jacobandrewsky/modular-architecture-in-nuxt-4jh9)
- [Building a Modular Monolith with Nuxt Layers](https://alexop.dev/posts/nuxt-layers-modular-monolith/)
- [Vue Best Practices in 2026: Architecting for Speed, Scale, and Sanity](https://onehorizon.ai/blog/vue-best-practices-in-2026-architecting-for-speed-scale-and-sanity)
- [Feature-Sliced Design — Vue Application Architecture](https://feature-sliced.design/blog/vue-application-architecture)
- [Nuxt 4 Performance Optimization 2026](https://masteringnuxt.com/blog/nuxt-4-performance-optimization-complete-guide-to-faster-apps-in-2026)
- [Authentication in Nuxt 4 Without Third-Party Modules](https://medium.com/@testjokerqwerty/authentication-in-nuxt-4-without-third-party-modules-a-complete-guide-677999744ecf)

### Principes de design appliqués

- **SOLID** — Single Responsibility (séparation par feature), Open/Closed (composables réutilisables)
- **DRY** — Don't Repeat Yourself (SSOT, composables, utils)
- **YAGNI** — You Aren't Gonna Need It (pas de Nuxt Layers tant qu'il n'y a qu'un produit)
- **Convention over Configuration** — Conventions Nuxt 4
- **Composition over Inheritance** — Composables, pas mixins

---

## 📌 Note de maintenance

Ce document **DOIT** être mis à jour quand :
- Un nouveau pattern est introduit
- Une convention change
- Un nouvel anti-pattern est identifié
- La stack technique évolue

**Toute modification** de ce document doit être commitée avec message :
```
docs(architecture): <description précise du changement>
```

---

*Document écrit pour KALGA — Frontend v1.0 — Juin 2026*
