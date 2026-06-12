# Plan 002 — Schéma Convex (tables métier) + seed démo + queries de base

> **Executor instructions** : suivre étape par étape, vérifier chaque commande avant
> de continuer. STOP et reporter si une condition « STOP » survient. Mettre à jour la
> ligne 002 de `plans/README.md` à la fin.
>
> **Drift check** : `git diff --stat 1e28bf5..HEAD -- kalga-api/app/database/connection.py`
> Le schéma SQLite de `connection.py` est la **source de vérité** des colonnes. S'il a
> changé depuis `1e28bf5`, relire les blocs `CREATE TABLE` avant de modéliser.

## Status
- **Priority** : P1
- **Effort** : L
- **Risk** : MED (le schéma conditionne tout le reste ; erreurs de modélisation coûteuses à corriger après)
- **Depends on** : 001 (l'app `kalga-web/` + Convex initialisé doivent exister)
- **Category** : migration
- **Planned at** : commit `1e28bf5`, 2026-06-11

## Why this matters

Convex devient la source de vérité unique (décision D3). Ce plan transpose le schéma
SQLite métier en `convex/schema.ts` **typé**, avec les index nécessaires aux requêtes du
dashboard/storefront et du Python, plus un seed démo (D10 : pas de migration, on re-seed).
Un schéma propre ici évite des reprises douloureuses dans 003/004/006.

## Current state

**Source de vérité des colonnes** : `kalga-api/app/database/connection.py`, blocs
`CREATE TABLE` aux lignes ci-dessous (lire chaque bloc avant de modéliser la table) :

| Table SQLite | Ligne | Domaine | Convex en 002 ? |
|---|---|---|---|
| `merchants` | 40 | tenant/business | **Oui** (+ champ `organizationId` ajouté en 003) |
| `products` | 109 | catalogue | **Oui** (voir piège embedding) |
| `categories` | 206 | catalogue | Oui |
| `conversations` | 128 | chat | Oui |
| `messages` | 144 | chat | Oui |
| `client_history` | 220 | mémoire LTM | Oui |
| `knowledge_base` | 368 | mémoire | Oui |
| `follow_ups` | 189 | scheduler | Oui (réécrit en scheduler Convex en 004) |
| `conversation_feedback` | 383 | chat | Oui |
| `product_waitlist` | 448 | catalogue | Oui |
| `stock_events` | 468 | analytics | Oui |
| `daily_stats` | 156 | analytics | Oui |
| `analytics_events` | 174 | analytics | Oui |
| `subscriptions` | 266 | abonnement | Oui |
| `activation_codes` | 316 | abonnement | Oui |
| `admin_audit_logs` | 301 | admin | Oui |
| `storefront_orders` | 332 | storefront | Oui |
| `users` | 246 | **auth** | **NON** — géré par Better Auth (plan 003) |
| `active_sessions` | 286 | **auth** | **NON** — géré par Better Auth (plan 003) |

Index SQLite existants à reproduire en index Convex : voir `connection.py:400-547`
(ex. `idx_products_merchant`, `idx_conversations_status`, `idx_follow_ups_scheduled`,
`idx_activation_codes_code`, etc.).

Conventions Convex (lire la doc à jour via ctx7 — voir toolkit) :
- ID auto-increment SQLite → **`Id<"table">` Convex** (ne pas recréer d'`id` entier).
- FK `merchant_id` / `conversation_id` / `product_id` → **`v.id("merchants" | "conversations" | "products")`**.
- Enums de statut (ex. `conversations.status`, `products` stock, `activation_codes.status`,
  `storefront_orders.status`) → **`v.union(v.literal("…"), …)`** (lister les valeurs réelles
  trouvées dans les repos/services, pas inventées).
- Timestamps → `v.number()` (epoch ms). Booléens → `v.boolean()`. Champs optionnels → `v.optional(...)`.
- **Scoping tenant** : chaque table métier porte `merchantId: v.id("merchants")` et un index
  `by_merchant`. (Le pont `merchant ↔ organisation Better Auth` se fait en 003 via
  `merchants.organizationId`.)

## Commands you will need

| But | Commande (depuis `kalga-web/`) | Attendu |
|-----|------|---------|
| Push schéma + valider | `pnpm exec convex dev --once` | déploiement OK, types `_generated` régénérés, **aucune erreur de validation de schéma** |
| Lancer une fonction | `pnpm exec convex run seed:run` | seed exécuté sans erreur |
| Typecheck | `pnpm exec tsc --noEmit` | exit 0 |
| Inspecter données | `pnpm exec convex data <table>` | lignes seedées visibles |

## Suggested executor toolkit
- **ctx7 avant de coder** : `npx -y ctx7 library "convex" "schema defineTable v validators indexes vector search"`
  puis `ctx7 docs <id> "defineSchema, v.id references, search index, vector index, internalMutation"`.
- Skill `convex-migration-helper` si dispo (conventions de modélisation), `convex-cli` pour le non-interactif.

## Scope

**In scope** :
- `kalga-web/convex/schema.ts` — toutes les tables métier ci-dessus
- `kalga-web/convex/seed.ts` — mutation interne de seed démo
- `kalga-web/convex/merchants.ts`, `products.ts`, `conversations.ts` — **queries de lecture de base seulement** (list/get scopées `by_merchant`), juste de quoi valider le schéma et alimenter 006/007
- supprimer la table de fumée `_smoke` créée en 001 si présente

**Out of scope** :
- `users` / `active_sessions` / tables d'identité → **plan 003** (Better Auth les crée).
- Toute logique d'écriture chat/IA, fonctions grossières Python → **plan 004**.
- Better Auth, `organizationId` réellement peuplé → **plan 003**.
- L'index vectoriel CLIP **opérationnel** (recherche d'image) → **plan 004** ; ici on **prévoit
  seulement le champ** (voir piège).

## Pièges spécifiques (à traiter explicitement)

1. **Embedding CLIP des produits** : en SQLite c'est un BLOB exclu de la sérialisation JSON
   (cf. commit `699b071`). En Convex, **ne pas** stocker un blob binaire. Deux options —
   choisir l'option A pour 002 :
   - **A (002)** : champ `imageEmbedding: v.optional(v.array(v.float64()))` (vide pour l'instant),
     **sans** index vectoriel encore. Documenter que la recherche visuelle (plan 004) ajoutera
     un **vector index** Convex natif sur ce champ (remplace CLIP-en-Python à terme — gros gain).
   - B (différé) : Convex file storage. Non retenu pour 002.
2. **`merchants` ↔ org** : ajouter `organizationId: v.optional(v.string())` (peuplé en 003) +
   `slug: v.string()` **unique** (pour `{slug}.kalga.app`, D2) + index `by_slug`. Garder le
   `phone` WhatsApp (numéro du bot) en index `by_phone` (le bridge identifie le marchand par là).
3. **`subscriptions` vs Better Auth** : `subscriptions` reste une table **métier** (statut
   d'abonnement lié au code d'activation), distincte des sessions Better Auth. Ne pas la fusionner.
4. **Valeurs d'enums** : extraire les vraies valeurs depuis les repos
   (`kalga-api/app/database/repositories/*`) et services — ex. statut conversation, statut stock
   (`ok`/`low_stock`/`out_of_stock`), statut activation, statut commande. Ne pas deviner.

## Steps

### Step 1 — Lire le schéma source
Ouvrir `kalga-api/app/database/connection.py:40-547` et noter, par table métier, les colonnes,
types, NOT NULL/DEFAULT, et les valeurs d'enums (croiser avec les repos pour les littéraux).

**Verify** : (lecture) — lister mentalement les 17 tables métier + leurs index.

### Step 2 — Écrire `convex/schema.ts`
Définir chaque table métier avec `defineTable({...})`, les `v.id(...)` pour les FK, les
`v.union(v.literal(...))` pour les enums, et reproduire chaque index SQLite en `.index("by_xxx", [...])`.
Inclure les pièges 1/2/3. Supprimer la table `_smoke` de 001.

**Verify** : `pnpm exec convex dev --once` → push OK, **aucune erreur de validation** ;
`pnpm exec tsc --noEmit` → exit 0.

### Step 3 — Queries de lecture de base
Créer `convex/merchants.ts` (`getBySlug`, `getByPhone`), `convex/products.ts`
(`listByMerchant` via index `by_merchant`), `convex/conversations.ts`
(`listByMerchant`, `messagesByConversation`). **Lecture seule**, scopées par merchant.

**Verify** : `pnpm exec tsc --noEmit` → exit 0 ; `pnpm exec convex dev --once` → OK.

### Step 4 — Seed démo (`convex/seed.ts`)
`internalMutation` `run` qui crée : **1 marchand démo** (slug `demo`, phone factice, persona),
**~4 produits** (dont 1 `out_of_stock`, 1 `low_stock`), **2 catégories**, **2 conversations**
avec quelques **messages**, 1 `activation_code` `pending`, 1 `subscription` `trial`. Idempotent
(si le marchand `demo` existe, ne pas redoubler — supprimer/relancer proprement).

**Verify** : `pnpm exec convex run seed:run` → succès ;
`pnpm exec convex data merchants` → le marchand `demo` apparaît ;
`pnpm exec convex data products` → 4 produits.

### Step 5 — Smoke build
**Verify** : depuis `kalga-web/`, `pnpm build` → exit 0.

## Test plan
- Pas encore de tests applicatifs (le harnais arrive en 006). La validation = push de schéma
  sans erreur + seed exécutable + `convex data` montrant les lignes + `tsc --noEmit` vert.
- Quand 004 ajoutera l'écriture chat, des tests d'intégration couvriront ces tables.

## Done criteria (toutes)

- [ ] `convex/schema.ts` modélise les **17 tables métier** (PAS `users`/`active_sessions`), avec FK `v.id`, enums `v.union`, et les index de `connection.py:400-547` reproduits.
- [ ] `merchants` a `slug` (unique, index `by_slug`), `phone` (index `by_phone`), `organizationId` optionnel ; `products` a `imageEmbedding: v.optional(v.array(v.float64()))`.
- [ ] `pnpm exec convex dev --once` push sans erreur ; `pnpm exec tsc --noEmit` exit 0.
- [ ] `pnpm exec convex run seed:run` crée le marchand `demo` + ~4 produits + 2 conversations (vérifiable via `convex data`).
- [ ] Queries de lecture de base présentes et typées (`merchants`/`products`/`conversations`).
- [ ] `git status` : modifs limitées à `kalga-web/` et `plans/`.
- [ ] Ligne 002 de `plans/README.md` → DONE.

## STOP conditions
- `connection.py` a dérivé depuis `1e28bf5` (drift check) → relire avant de modéliser.
- Une valeur d'enum n'est pas déductible du code (ambiguïté réelle) → reporter la liste exacte à clarifier.
- Le push de schéma échoue pour une raison non liée à une faute de frappe corrigeable (ex. limite Convex) → reporter.
- Besoin de toucher `users`/`active_sessions` → STOP (c'est le plan 003).

## Maintenance notes
- **003** ajoutera `merchants.organizationId` réellement peuplé + le pont withOrg.
- **004** activera l'**index vectoriel** sur `products.imageEmbedding` (recherche visuelle
  Convex-native) et réécrira `follow_ups` en scheduler Convex.
- Tout nouvel attribut métier passe par `schema.ts` (Convex valide à l'écriture) — ne jamais
  écrire un champ non déclaré.
- Reviewer : vérifier que **chaque** table métier porte `merchantId` + index `by_merchant`
  (scoping tenant = base de la sécurité, remplace les findings IDOR SEC-01/03 de l'audit).
