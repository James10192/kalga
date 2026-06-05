# KALGA Frontend

Frontend web de KALGA — commerce WhatsApp automatisé pour marchands.

> **Document de référence architecturale** : [`../ARCHITECTURE_FRONTEND.md`](../ARCHITECTURE_FRONTEND.md)
> Toute déviation de ce document doit être justifiée et documentée.

---

## Stack

| Couche | Techno | Version |
|---|---|---|
| Framework | Nuxt | 4.4.6 |
| UI | Vue 3 + Composition API | 3.5 |
| Langage | TypeScript strict | 5.7 |
| Style | Tailwind CSS v4 | 4.0 |
| Composants | shadcn-vue (via shadcn-nuxt) | 2.x |
| Data fetching | TanStack Query Vue | 5.x |
| State | Pinia | 2.x |
| Validation | Zod | 3.x |
| i18n | @nuxtjs/i18n (FR/EN/AR) | 10.x |
| PWA | @vite-pwa/nuxt | 1.x |
| Observabilité | Sentry | 9.x |
| Tests unit | Vitest + @vue/test-utils | 2.x |
| Tests E2E | Playwright | 1.x |

---

## Zones de l'application

```
ZONE PUBLIQUE          ZONE MARCHAND          ZONE ADMIN
(storefront SSG)       (dashboard SSR)        (admin SSR)
/                      /dashboard/*           /admin/*
/boutique/[phone]
/produit/[code]
```

---

## Démarrage local

> **A faire une seule fois (WiFi requis)** : installation des dépendances.

```bash
cd kalga-frontend
pnpm install
cp .env.example .env
# Éditer .env avec les vraies valeurs (clés API, secret session, etc.)
```

### Lancement

```bash
pnpm dev              # Serveur dev sur http://localhost:3000
pnpm build            # Build de production
pnpm preview          # Preview du build local
pnpm generate         # Génération statique (SSG) pour CDN
```

### Qualité

```bash
pnpm lint             # ESLint check
pnpm lint:fix         # ESLint + auto-fix
pnpm typecheck        # vue-tsc strict
pnpm format           # Prettier write
pnpm format:check     # Prettier check
```

### Tests

```bash
pnpm test             # Vitest run
pnpm test:watch       # Vitest watch
pnpm test:coverage    # Couverture (cible 80% sur utils & composables)
pnpm test:e2e         # Playwright (lance pnpm dev en background)
pnpm test:e2e:ui      # Playwright UI mode
```

---

## Structure (résumé)

Voir [`ARCHITECTURE_FRONTEND.md` section 4](../ARCHITECTURE_FRONTEND.md#4-structure-des-dossiers) pour la version complète.

```
kalga-frontend/
├── app/
│   ├── components/        # ui (shadcn) + layout + shared
│   ├── features/          # Organisation par feature métier
│   ├── composables/       # Composables transverses
│   ├── layouts/           # Nuxt layouts
│   ├── middleware/        # Gardes de route (auth)
│   ├── pages/             # Routing file-based
│   ├── plugins/           # Sentry, PWA
│   ├── stores/            # Pinia transverses
│   ├── types/             # Types globaux (domain, api)
│   └── utils/             # Fonctions pures
├── server/                # API server-side (auth, proxy FastAPI)
├── i18n/locales/          # fr.json, en.json, ar.json
├── tests/                 # unit/ + e2e/
└── public/                # Assets statiques + PWA manifest
```

---

## Conventions

- **TypeScript strict** + `noUncheckedIndexedAccess` — zéro `any` non documenté.
- **Composition API** (`<script setup>`) uniquement — pas d'Options API ni mixins.
- **Auto-imports** : composants, composables, stores, utils — pas d'`import` manuel.
- **i18n** : toute chaîne visible utilisateur passe par `$t()`.
- **Sécurité** : tokens en HttpOnly cookies, jamais en localStorage. Pas de `v-html`.

Voir [`ARCHITECTURE_FRONTEND.md` section 10](../ARCHITECTURE_FRONTEND.md#10-anti-patterns-à-éviter) pour la liste complète des anti-patterns.

---

## Backend connecté

Le frontend communique avec [`kalga-api`](../kalga-api/) (FastAPI Python sur port 8001) via un proxy server-side Nuxt (`/server/api/proxy/[...path].ts`) qui injecte la clé `NUXT_PROXY_INTERNAL_API_KEY` côté serveur. Le browser ne voit jamais l'URL ni la clé du backend Python.
