# Plan 001 — Scaffolder `kalga-web` (TanStack Start) + initialiser Convex, prêt pour Vercel

> **Executor instructions** : suivre étape par étape. Lancer chaque commande de
> vérification et confirmer le résultat attendu avant de passer à la suite. En cas
> de « STOP conditions », s'arrêter et reporter — ne pas improviser. À la fin,
> mettre à jour la ligne de statut de ce plan dans `plans/README.md`.
>
> **Drift check (à lancer d'abord)** : `git diff --stat 1e28bf5..HEAD -- kalga-web/`
> Si `kalga-web/` existe déjà avec du contenu, comparer à l'état décrit ci-dessous ;
> en cas de divergence, traiter comme STOP condition.

## Status
- **Priority** : P1
- **Effort** : M
- **Risk** : LOW (création d'un nouveau dossier isolé ; ne touche aucun code existant)
- **Depends on** : none
- **Category** : migration / dx
- **Planned at** : commit `1e28bf5`, 2026-06-11

## Why this matters

Toute la migration (Convex, auth, dashboard, storefront) vit dans une nouvelle app
**TanStack Start** (React, SSR), déployée sur Vercel (décision D1/D2). Le dossier
`convex/` (schéma + fonctions backend) sera hébergé dans cette app et appelé à la fois
par le front (`useQuery`) et par le Python (client Python). Ce plan pose **uniquement**
les fondations : app qui démarre en SSR, Convex initialisé, config Vercel correcte, en
respectant les gotchas TanStack Start connus. Aucune feature ici — juste un socle vert.

## Current state

- Repo monorepo-ish, dossiers existants : `kalga-api/` (Python), `kalga-whatsapp/` (Node),
  `kalga-frontend/` (Nuxt — **référence visuelle, ne pas toucher**), `dashboard/`,
  `storefront/` (anciens statiques — ne pas toucher).
- **Aucun** dossier `kalga-web/` n'existe encore (le créer).
- Gestionnaire de paquets imposé : **pnpm exclusivement** (jamais npm).
- Règle proprio : commits sans `Co-Authored-By`.

Conventions TanStack Start à respecter (règle globale `tanstack-start-vite-gotchas.md`) :
- Exporter **`getRouter`** (pas `createRouter`) depuis `src/router.tsx`.
- `__root.tsx` avec **`shellComponent`** rendant le `<html>` complet + `<HeadContent />` + `<Scripts />`.
- `vite.config.ts` : `ssr.noExternal` pour `convex`, `@convex-dev/*`, `@convex-dev/react-query` ;
  `ssr.external` pour les libs browser-only (jspdf, file-saver…) si ajoutées plus tard.
- Providers lourds (Convex/auth) **PAS** dans `__root.tsx` — ils seront scopés à `/app/*` (plan 006).
- Routes API via `Route + server.handlers` (pas `createServerFileRoute`).

## Commands you will need

| But | Commande | Attendu |
|-----|----------|---------|
| Install | `pnpm install` | exit 0 |
| Dev | `pnpm dev` | serveur SSR up sur un port local, page rendue |
| Build | `pnpm build` | exit 0, sortie de build produite |
| Typecheck | `pnpm typecheck` (ou `pnpm exec tsc --noEmit`) | exit 0 |
| Convex dev | `pnpm exec convex dev --once` | déploiement créé, `convex/_generated/` produit |

## Suggested executor toolkit

- **ctx7 obligatoire avant de coder** (règle proprio « use ctx7 surtout ») pour les
  versions/API actuelles — training data périmé :
  - `npx -y ctx7 docs /websites/labs_convex_dev_better-auth "tanstack start setup convex"` (contexte intégration)
  - `npx -y ctx7 library "tanstack start" "project setup vite ssr vercel"` puis `ctx7 docs <id> "create project, getRouter, shellComponent, vercel deploy target"`
  - `npx -y ctx7 library "convex" "react setup vite environment variables"`
- Skill `vercel-react-best-practices` / `deploy-to-vercel` au moment du déploiement (plan 009, pas ici).

## Scope

**In scope** (créer uniquement sous ce dossier) :
- `kalga-web/` — toute la nouvelle app TanStack Start
- `kalga-web/convex/` — backend Convex (init seulement ici : `schema.ts` minimal, config)
- `kalga-web/.env.local`, `kalga-web/.env.example`
- `kalga-web/vercel.json` (si nécessaire au build target)

**Out of scope** (NE PAS toucher) :
- `kalga-frontend/` (Nuxt — référence visuelle conservée volontairement)
- `kalga-api/`, `kalga-whatsapp/`, `dashboard/`, `storefront/`
- Tout schéma métier Convex (les 21 tables) → c'est le plan **002**. Ici, `schema.ts` reste
  minimal (vide ou une table `_smoke` de fumée à supprimer en 002).
- Better Auth → plan **003**.

## Git workflow
- Branche : `migration/001-scaffold-kalga-web` (depuis la branche courante).
- Commits conventionnels (scopes du repo) : ex. `chore(web): scaffold TanStack Start app`,
  `feat(web): init convex`. **Pas de `Co-Authored-By`.**
- Ne pas push / ouvrir de PR sauf instruction.

## Steps

### Step 1 — Vérifier le terrain
Confirmer qu'aucun `kalga-web/` n'existe et que pnpm est dispo.
**Verify** : `ls kalga-web 2>/dev/null && echo EXISTS || echo OK` → `OK` ; `pnpm --version` → numéro ≥ 9.

### Step 2 — Créer l'app TanStack Start
Via ctx7, récupérer la commande de création officielle actuelle de TanStack Start, puis
scaffolder dans `kalga-web/`. Cible : **React 19, Vite, SSR, déployable Vercel**. Utiliser
**pnpm** pour l'install. Ne pas accepter de template qui crée `index.html` + `src/main.tsx`
en plus du shell (Start gère le document — supprimer ces fichiers s'ils apparaissent).

**Verify** : `cd kalga-web && pnpm install` → exit 0 ; `test -f src/router.tsx && test -f src/routes/__root.tsx && echo OK` → `OK`.

### Step 3 — Conformer au pattern TanStack Start
S'assurer que :
- `src/router.tsx` exporte **`getRouter()`** (renommer si le template a `createRouter`).
- `src/routes/__root.tsx` a un `shellComponent` rendant `<html>…<HeadContent/></head><body>{children}<Scripts/></body></html>`.
- Aucune `index.html` / `src/main.tsx` résiduelle.

**Verify** : `grep -q "export function getRouter" src/router.tsx && echo OK` → `OK` ;
`grep -q "shellComponent" src/routes/__root.tsx && echo OK` → `OK` ;
`ls index.html src/main.tsx 2>/dev/null && echo BAD || echo OK` → `OK`.

### Step 4 — Page d'accueil de fumée
Mettre une route `/` minimale (titre « KALGA » + un sous-titre) pour valider le rendu SSR.
Respecter les règles design de base (français à l'écran, pas d'em dash) — contenu jetable,
le vrai design vient en 005/006.

**Verify** : `pnpm build` → exit 0.

### Step 5 — Initialiser Convex dans l'app
Ajouter Convex (`pnpm add convex`) et initialiser le projet Convex **non-interactivement**
(cf. ctx7 `convex` + skill `convex-cli` si dispo). Cible : un déploiement Convex de dev créé,
`convex/_generated/` généré, `convex/schema.ts` minimal (table de fumée OU vide).
Renseigner `.env.local` avec `VITE_CONVEX_URL` (+ `VITE_CONVEX_SITE_URL`) produits par Convex,
et créer `.env.example` avec les **noms** des variables (jamais les valeurs).

**Verify** : `pnpm exec convex dev --once` → succès, pas d'erreur ;
`test -d convex/_generated && echo OK` → `OK` ;
`grep -q "VITE_CONVEX_URL" .env.example && echo OK` → `OK`.

### Step 6 — Garde-fous Vite SSR + secrets
- `vite.config.ts` : `ssr.noExternal: ['convex', '@convex-dev/react-query']` (ajouter les
  `@convex-dev/*` au fur et à mesure dans les plans suivants).
- Vérifier que `.env.local` est bien gitignoré (ne JAMAIS committer de secret).

**Verify** : `grep -q "noExternal" vite.config.ts && echo OK` → `OK` ;
`git check-ignore kalga-web/.env.local && echo IGNORED` → `IGNORED`.

### Step 7 — Smoke run final
**Verify** : `pnpm build` → exit 0 ; `pnpm dev` démarre sans erreur (Ctrl-C après confirmation
visuelle que `/` rend « KALGA »).

## Test plan

Pas de tests unitaires à ce stade (socle). La vérification = `pnpm build` vert + `pnpm dev`
qui sert `/` en SSR + `convex dev --once` qui réussit. Le harnais de tests (vitest/playwright)
sera posé avec les features (plan 006+).

## Done criteria (toutes doivent tenir)

- [ ] `kalga-web/` existe ; `kalga-frontend/`, `kalga-api/`, `kalga-whatsapp/`, `dashboard/`, `storefront/` **inchangés** (`git status` ne montre aucune modif hors `kalga-web/` et `plans/`).
- [ ] `cd kalga-web && pnpm build` exit 0.
- [ ] `src/router.tsx` exporte `getRouter` ; `__root.tsx` a `shellComponent` + `<Scripts/>`.
- [ ] `convex/_generated/` présent ; `pnpm exec convex dev --once` réussit.
- [ ] `.env.example` liste `VITE_CONVEX_URL` (+ siteUrl) ; `.env.local` gitignoré ; **aucun secret committé**.
- [ ] Ligne 001 de `plans/README.md` mise à jour (DONE).

## STOP conditions (s'arrêter et reporter)

- `kalga-web/` existe déjà avec du contenu non trivial (divergence vs ce plan).
- La commande de création TanStack Start officielle (via ctx7) diffère structurellement de
  l'hypothèse `getRouter`/`shellComponent` → reporter la nouvelle API observée avant de continuer.
- `convex dev` exige une étape interactive impossible à automatiser → reporter l'étape humaine exacte requise.
- Un quelconque fichier hors `kalga-web/` (sauf `plans/README.md`) doit être modifié.
- `pnpm build` échoue deux fois après correction raisonnable.

## Maintenance notes

- Le schéma métier (21 tables) **n'est pas** ici : plan 002. Garder `schema.ts` minimal.
- Better Auth ajoutera `@convex-dev/better-auth` aux `ssr.noExternal` (plan 003).
- Les providers Convex/auth seront scopés à `/app/*` (plan 006), **jamais** dans `__root.tsx`
  (sinon les pages publiques landing/storefront cassent à l'hydratation — règle TanStack).
- Le proprio garde `kalga-frontend/` (Nuxt) comme référence design tant que `kalga-web` ne couvre
  pas toutes les surfaces ; ne pas le supprimer dans ce plan.
