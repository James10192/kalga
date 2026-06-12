# Convex Core — Référence d'exécution (KALGA)

> Source : ctx7 `/llmstxt/convex_dev_llms_txt` (docs.convex.dev, benchmark 87.9). Vérifié 2026-06.
> Cible : agents exécuteurs sans contexte. Tout est copiable tel quel.
> Stack KALGA : `kalga-web` (TanStack Start) + backend Convex. Remplace l'ancien FastAPI/SQLite.

---

## État implémenté (2026-06-12)

Ce qui existe réellement dans `kalga-web/convex/` après exécution des plans 002/003/004 :

- **Versions réelles** : `convex@^1.41.0` (PAS le `>=1.25.0` indicatif). `_generated/` régénéré.
- **Déploiement dev** : `dev:rugged-albatross-514` (team `djedjelipatrick`, project `kalga`).
- **Env vars Convex réellement posées** (`npx convex env list`) :
  - `BETTER_AUTH_SECRET` (003)
  - `SITE_URL` = `http://localhost:3000` (003)
  - `KALGA_WHATSAPP_URL` = `http://localhost:3001` (003, sender OTP)
  - `INTERNAL_API_KEY` = `kalga-dev-internal-key-004` (004, garde des fonctions grossières + bridge)
  - **NON posées (gate humain)** : `KALGA_OTP_SENDER_PHONE` (numéro émetteur OTP) — bloque le test OTP live (GATE-2).
- **Scheduler** : implémenté tel que décrit en §4 (`ctx.scheduler.runAfter` + chaînage), PAS de `crons.ts` — voir `convex/internal/followups.ts` (`scheduleFollowup` → `sendFollowup` action → re-`prepareFollowup`). Plus aucun `sleep(60)` côté Convex.
- **Vector index** : `products.imageEmbedding` existe en `v.optional(v.array(v.float64()))` SANS `.vectorIndex()` (réservé à un plan ultérieur, pas 002). Recherche image CLIP pas encore branchée.
- **Garde server-to-server (déviation §3.4)** : les fonctions appelées par le client Python NE sont PAS des `internalQuery`/`internalMutation`. Ce sont des `query`/`mutation`/`action` **publiques** gardées par un argument-secret `internalKey` (validé via `assertInternalKey` dans `convex/internal/guard.ts` contre `process.env.INTERNAL_API_KEY`). Raison vérifiée : sans `CONVEX_DEPLOY_KEY`, le client Python ne peut pas appeler des fonctions visibilité `internal` (l'appel hang sans `set_admin_auth`). Le contrat du plan 004 dit que la garde EST l'argument `internalKey` → public+secret-arg est la lecture retenue. Les fichiers sous `convex/internal/` portent ce nom par convention de domaine, pas par visibilité Convex.

---

## 0. Versions & conventions (training data périmé — lire ceci)

- Package : `convex` (latest). Install : `pnpm add convex@latest` (PAS npm — règle Marcel).
- Le dossier backend est **`convex/`** à la racine du projet. Fichiers `.ts`.
- Code généré dans **`convex/_generated/`** (`api`, `server`, `dataModel`). Régénéré à chaque `convex dev`. Ne JAMAIS éditer à la main.
- Validators : `import { v } from "convex/values"`.
- Schéma + functions : `import { ... } from "convex/server"` ou depuis `./_generated/server`.
- Une **action** qui utilise des modules Node.js natifs DOIT avoir `"use node";` en première ligne du fichier.
- `ctx.db` n'existe PAS dans les actions — utiliser `ctx.runQuery` / `ctx.runMutation`.
- Chaque document a automatiquement `_id` (type `v.id("table")`) et `_creationTime` (number, ms epoch). Ne PAS les déclarer dans le schéma.

---

## 1. Schéma : `defineSchema` / `defineTable` + validators `v.*`

Fichier : **`convex/schema.ts`**

```typescript
// convex/schema.ts
import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  users: defineTable({
    name: v.string(),
    email: v.string(),
  }).index("by_email", ["email"]),

  messages: defineTable({
    body: v.string(),
    userId: v.id("users"),       // FK vers la table users
    channelId: v.id("channels"),
  }).index("by_channel", ["channelId"]),

  channels: defineTable({
    name: v.string(),
  }),

  // Table en union discriminée (status, kind, etc.)
  results: defineTable(
    v.union(
      v.object({ kind: v.literal("error"), message: v.string() }),
      v.object({ kind: v.literal("success"), value: v.number() }),
    ),
  ),
});
```

### Catalogue des validators `v.*`

```typescript
v.string()
v.number()        // float64
v.float64()       // alias number
v.int64()         // BigInt (entiers 64 bits)
v.boolean()
v.null()
v.id("tableName") // référence vers _id d'une autre table
v.bytes()         // ArrayBuffer (ex: BLOB embedding — mais préférer v.array(v.float64()) pour CLIP)
v.any()           // accepte n'importe quoi (à éviter)

// Conteneurs
v.array(v.string())
v.object({ a: v.string(), b: v.number() })
v.record(v.string(), v.number())   // dictionnaire clés/valeurs

// Modificateurs
v.optional(v.string())             // champ optionnel (peut être absent)
v.union(v.literal("a"), v.literal("b"))   // enum / variants
v.literal("exact_value")           // valeur exacte (string, number, bool)
```

### Exemple champ optionnel + enum (pattern KALGA produit/commande)

```typescript
products: defineTable({
  merchantId: v.id("merchants"),
  code: v.string(),
  name: v.string(),
  price: v.number(),
  stock: v.optional(v.number()),
  status: v.union(v.literal("ok"), v.literal("low_stock"), v.literal("out_of_stock")),
  // Embedding CLIP pour recherche d'image (1.4 — vector index)
  embedding: v.optional(v.array(v.float64())),
}).index("by_merchant", ["merchantId"]),
```

---

## 2. Index : `.index()`, `.searchIndex()`, `.vectorIndex()`

### 2.1 Index standard (`.index()`)

Chaîné après `defineTable({...})`. Premier arg = nom de l'index, second = tableau ordonné de champs.

```typescript
defineTable({ merchantId: v.id("merchants"), code: v.string() })
  .index("by_merchant", ["merchantId"])
  .index("by_merchant_code", ["merchantId", "code"]); // index composite multi-champ
```

Requête via `withIndex` (voir §3.5).

### 2.2 Search index (full-text) — `.searchIndex()`

Recherche textuelle full-text. Un seul `searchField`, plusieurs `filterFields` (égalité).

```typescript
messages: defineTable({
  body: v.string(),
  channel: v.string(),
}).searchIndex("search_body", {
  searchField: "body",
  filterFields: ["channel"],
}),
```

### 2.3 Vector index (recherche sémantique / image CLIP) — `.vectorIndex()`

**C'est l'index pour la recherche d'image produit CLIP de KALGA.**

```typescript
products: defineTable({
  description: v.string(),
  merchantId: v.id("merchants"),
  embedding: v.array(v.float64()),    // le vecteur CLIP
}).vectorIndex("by_embedding", {
  vectorField: "embedding",
  dimensions: 512,                    // DOIT matcher la taille du vecteur CLIP (ex CLIP ViT-B/32 = 512 ; ViT-L/14 = 768). Adapter au modèle réel.
  filterFields: ["merchantId"],       // pour filtrer par marchand pendant la recherche
}),
```

Contraintes vector index :
- `dimensions` doit être EXACTEMENT la dimension du modèle d'embedding.
- Jusqu'à 64 expressions de filtre, jusqu'à 256 résultats (défaut 10).
- La recherche vectorielle se fait UNIQUEMENT dans une **action** (pas query/mutation) via `ctx.vectorSearch` (§3.6).

---

## 3. Functions : query / mutation / action (+ variantes internal)

Toutes définies avec `args` (validators), `handler`, optionnellement `returns`.

### 3.1 `query` (lecture, réactive, publique)

```typescript
// convex/products.ts
import { query } from "./_generated/server";
import { v } from "convex/values";

export const listByMerchant = query({
  args: { merchantId: v.id("merchants") },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("products")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
  },
});
```

### 3.2 `mutation` (écriture transactionnelle, publique)

```typescript
import { mutation } from "./_generated/server";
import { v } from "convex/values";

export const create = mutation({
  args: { merchantId: v.id("merchants"), name: v.string(), price: v.number() },
  handler: async (ctx, args) => {
    const id = await ctx.db.insert("products", {
      merchantId: args.merchantId,
      name: args.name,
      price: args.price,
      status: "ok",
    });
    return id;
  },
});
```

Opérations `ctx.db` dans mutation : `insert(table, doc)`, `patch(id, partial)`, `replace(id, doc)`, `delete(id)`, `get(id)`, `query(table)`.

### 3.3 `action` (effets de bord : fetch externe, LLM, vector search)

`ctx.db` indisponible. Lire/écrire via `ctx.runQuery` / `ctx.runMutation`.

```typescript
// convex/ai.ts
import { action } from "./_generated/server";
import { v } from "convex/values";
import { internal } from "./_generated/api";

export const generateSummary = action({
  args: { text: v.string() },
  returns: v.string(),
  handler: async (ctx, args) => {
    const response = await fetch("https://api.deepseek.com/v1/...", {
      method: "POST",
      body: JSON.stringify({ text: args.text }),
    });
    const { summary } = await response.json();
    // Écrire via une internal mutation :
    await ctx.runMutation(internal.ai.saveSummary, { text: args.text, summary });
    return summary;
  },
});
```

### 3.4 Variantes `internal*` (non appelables par le client)

Définies avec `internalQuery` / `internalMutation` / `internalAction`. Appelables uniquement depuis d'autres functions Convex via `internal.<module>.<name>`.

```typescript
import { internalQuery, internalMutation, internalAction } from "./_generated/server";
import { v } from "convex/values";

export const readData = internalQuery({
  args: { a: v.number() },
  handler: async (ctx, args) => {
    // lecture via ctx.db
  },
});

export const writeData = internalMutation({
  args: { a: v.number() },
  handler: async (ctx, args) => {
    // écriture via ctx.db
  },
});
```

### 3.5 Appels croisés : `ctx.runQuery` / `ctx.runMutation`

- Référence **publique** : `api.<module>.<fn>` (depuis `./_generated/api`).
- Référence **internal** : `internal.<module>.<fn>` (depuis `./_generated/api`).

```typescript
import { api, internal } from "./_generated/api";

// Dans une action :
const data = await ctx.runQuery(internal.products.readData, { a: 1 });
const id = await ctx.runMutation(internal.products.writeData, { a: 2 });

// runQuery depuis une mutation = même snapshot transactionnel :
const user = await ctx.runQuery(internal.users.getUser, { userId });
```

Règle : exposer en `query/mutation` (public) ce que le client appelle ; tout le reste en `internal*`. Les actions appellent typiquement des `internalMutation` pour écrire (évite l'accès direct client).

### 3.6 Requête avec index / search index / vector search

```typescript
// Index standard
await ctx.db.query("products")
  .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
  .collect();

// Search index full-text (dans une query)
await ctx.db.query("messages")
  .withSearchIndex("search_body", (q) =>
    q.search("body", args.text).eq("channel", args.channel))
  .take(10);

// Vector search (UNIQUEMENT dans une action) — recherche image CLIP KALGA
export const similarProducts = action({
  args: { merchantId: v.id("merchants"), embedding: v.array(v.float64()) },
  handler: async (ctx, args) => {
    const results = await ctx.vectorSearch("products", "by_embedding", {
      vector: args.embedding,
      limit: 16,                                  // 1..256, défaut 10
      filter: (q) => q.eq("merchantId", args.merchantId),
      // OR multi-valeurs : filter: (q) => q.or(q.eq("cuisine","French"), q.eq("cuisine","Indonesian"))
    });
    // results = [{ _id, _score }, ...]. Charger les docs via internalQuery :
    const docs = await ctx.runQuery(internal.products.fetchByIds, {
      ids: results.map((r) => r._id),
    });
    return docs;
  },
});
```

`ctx.vectorSearch(table, indexName, { vector, limit?, filter? })` renvoie `{ _id, _score }[]` triés par similarité. Les `filterFields` utilisés doivent figurer dans la définition `.vectorIndex(...)`.

---

## 4. Scheduler : `ctx.scheduler.runAfter` / `runAt`

> **Remplace l'ancien scheduler 60s Python (`followup_service.py`).** Pas de boucle `while True` : on planifie une fonction qui se re-planifie elle-même, ou on utilise un cron (`convex/crons.ts`).

Disponible dans **mutations et actions** via `ctx.scheduler`. Délais en **millisecondes**.

```typescript
import { mutation, internalMutation } from "./_generated/server";
import { internal } from "./_generated/api";
import { v } from "convex/values";

export const sendExpiringMessage = mutation({
  args: { body: v.string(), author: v.string() },
  handler: async (ctx, args) => {
    const id = await ctx.db.insert("messages", { body: args.body, author: args.author });
    // runAfter(delaiMs, ref, args) — s'exécute APRÈS commit de cette mutation
    await ctx.scheduler.runAfter(5000, internal.messages.destruct, { messageId: id });
  },
});

export const destruct = internalMutation({
  args: { messageId: v.id("messages") },
  handler: async (ctx, args) => {
    await ctx.db.delete(args.messageId);
  },
});
```

Patterns de délai :

```typescript
await ctx.scheduler.runAfter(0, internal.tasks.process, { taskId });            // ASAP (après commit)
await ctx.scheduler.runAfter(5000, internal.tasks.process, { taskId });         // 5 s
await ctx.scheduler.runAfter(60 * 60 * 1000, internal.cleanup.run, {});         // 1 h
await ctx.scheduler.runAfter(24 * 60 * 60 * 1000, internal.tasks.cleanup, {});  // 24 h

// runAt(date|timestamp, ref, args)
await ctx.scheduler.runAt(new Date("2030-01-01T00:00:00Z"), internal.events.trigger, {});
await ctx.scheduler.runAt(Date.now() + 60000, internal.tasks.process, { taskId });
```

**Pattern follow-up KALGA (remplacement du polling 60s)** : depuis la mutation qui crée une conversation/commande en attente, faire `ctx.scheduler.runAfter(delayMs, internal.followups.checkAndSend, { conversationId })`. La fonction planifiée vérifie l'état ; si toujours en attente, elle re-planifie le prochain check avec un nouveau `runAfter`. Plus de scheduler global 60s.

Cron récurrent (alternative) : fichier `convex/crons.ts` :

```typescript
import { cronJobs } from "convex/server";
import { internal } from "./_generated/api";

const crons = cronJobs();
crons.interval("cleanup", { minutes: 5 }, internal.tasks.cleanup, {});
export default crons;
```

---

## 5. Variables d'environnement Convex

> Les env vars vivent **côté déploiement Convex** (pas dans `.env.local` de l'app). Accès dans les functions via `process.env.NAME`.

### CLI

```bash
npx convex env list
npx convex env get DEEPSEEK_API_KEY
npx convex env set DEEPSEEK_API_KEY 'sk-xxxxx'
npx convex env set --from-file .env.convex      # set en masse depuis un fichier
npx convex env remove DEEPSEEK_API_KEY

# Cibler la production :
npx convex env set --prod DEEPSEEK_API_KEY 'sk-xxxxx'
```

### Accès dans une function (string | undefined)

```javascript
const key = process.env.DEEPSEEK_API_KEY;   // string si défini, sinon undefined
const url =
  "https://api.deepseek.com/v1/...?api_key=" + process.env.DEEPSEEK_API_KEY;
```

Note : `CONVEX_DEPLOYMENT`, `VITE_CONVEX_URL`, `CONVEX_SITE_URL` sont gérés automatiquement et écrits dans `.env.local` à l'init (côté app, pas via `convex env set`).

---

## 6. Lancer `convex dev` en NON-interactif + exigences de login

### 6.1 Première fois (interactif requis sauf deploy key)

`npx convex dev` (1re exécution) demande de **se connecter (login device)** et **créer un projet**. Il crée :
- le dossier `convex/`,
- `.env.local` avec `CONVEX_DEPLOYMENT`.

Login = navigateur OAuth. **Sans authentification, impossible de créer un projet** (sauf mode anonyme, §6.3).

### 6.2 Non-interactif via deploy key (CI / agents avec compte)

Si un projet existe déjà et qu'on a une **deploy key** (générée dans le dashboard Convex → Settings → Deploy keys, ou via Platform API) :

```bash
CONVEX_DEPLOY_KEY="YOUR_DEPLOY_KEY" npx convex dev --once
```

- `--once` : push le code une fois, régénère `_generated/`, puis sort (pas de watch). Idéal scripts/agents.
- `CONVEX_DEPLOY_KEY` court-circuite le login interactif.

### 6.3 Mode agent / anonyme (PAS de compte Convex requis)

Pour agents/VM sans compte Convex, backend local isolé :

```bash
CONVEX_AGENT_MODE=anonymous npx convex dev --once
```

- Permissions limitées, codegen + test possibles, backend local sur la VM.
- À mettre dans `.env.local` ou l'environnement de l'agent.
- Convient pour scaffolder/itérer sans login OAuth.

### 6.4 Récap des modes

| Besoin | Commande | Login OAuth ? | Compte requis ? |
|---|---|---|---|
| Setup initial dev | `npx convex dev` | Oui (1re fois) | Oui |
| CI / push ponctuel | `CONVEX_DEPLOY_KEY="..." npx convex dev --once` | Non | Oui (key d'un projet existant) |
| Agent/VM isolée | `CONVEX_AGENT_MODE=anonymous npx convex dev --once` | Non | Non |
| Deploy prod | `CONVEX_DEPLOY_KEY="..." npx convex deploy` | Non | Oui |

### 6.5 Pièges

- `convex dev` (watch) ne sort jamais : pour un agent, TOUJOURS `--once`, sinon le process bloque.
- `_generated/` doit exister avant que l'app TypeScript compile (les imports `./_generated/api` échouent sinon). Lancer `convex dev --once` au moins une fois après chaque modif de schéma/functions.
- Ne pas committer `.env.local` (contient `CONVEX_DEPLOYMENT`). Committer le code `convex/*.ts`.
- `convex` est ESM ; côté Vite/TanStack Start SSR, mettre `convex` dans `ssr.noExternal` (cf. rule tanstack-start-vite-gotchas).
