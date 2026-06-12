# KALGA — Référence schéma SQLite (17 tables métier)

> ## État implémenté (2026-06-12)
>
> Le plan 002 a transposé ces 17 tables en `kalga-web/convex/schema.ts` (déploiement dev
> `dev:rugged-albatross-514`, 38 index, schéma validé). Correspondance SQLite → Convex :
>
> - **Noms de tables = camelCase** : `client_history` → `clientHistory`, `knowledge_base` →
>   `knowledgeBase`, `follow_ups` → `followUps`, `conversation_feedback` → `conversationFeedback`,
>   `product_waitlist` → `productWaitlist`, `stock_events` → `stockEvents`, `daily_stats` →
>   `dailyStats`, `analytics_events` → `analyticsEvents`, `activation_codes` → `activationCodes`,
>   `admin_audit_logs` → `adminAuditLogs`, `storefront_orders` → `storefrontOrders`. Les 6 autres
>   gardent leur nom (`merchants`, `products`, `categories`, `conversations`, `messages`,
>   `subscriptions`). **17 tables, `users`/`active_sessions` exclues** (Better Auth, plan 003).
> - **FK** = `v.id("<table>")` (pas INTEGER). PK auto `_id`. `created_at`/`updated_at` SQLite ≈
>   `_creationTime` Convex (auto) — les colonnes `created_at` ne sont PAS redéclarées.
> - **Enums** = `v.union(v.literal(...))` aux VALEURS RÉELLES du tableau récap ci-dessous.
>   Exceptions laissées en `v.string()` (pas de whitelist backend) : `storefrontOrders.status`.
> - **`products.embedding` (BLOB)** → champ `imageEmbedding: v.optional(v.array(v.float64()))`
>   (PAS de BLOB, PAS encore de `.vectorIndex()`). `stock_quantity = -1` = illimité conservé.
> - **`merchants`** a en plus : `slug` (index `by_slug`, unique au niveau applicatif via
>   `provisionMerchantOrg`), `organizationId` optionnel (index `by_organization`), `phone`
>   (index `by_phone`). Lien Better Auth = `organizationId`.
> - **Index** : `by_merchant` sur toutes les tables scopées + index composites reproduits depuis
>   `connection.py` (38 index au total). Drift check `connection.py` vs `1e28bf5` : aucun diff.
> - **Queries de lecture seedées** (002) : `merchants.ts` (`getBySlug`, `getByPhone`, `get`),
>   `products.ts` (`listByMerchant`, `getByCode`), `conversations.ts` (`listByMerchant`,
>   `messagesByConversation`). **Seed** : `convex/seed.ts` (`run`, internalMutation idempotente :
>   purge + recrée 1 marchand demo, 2 catégories, 4 produits stock -1/2/0/40, 2 conversations,
>   1 subscription trial, 1 activationCode `DEMO2026` pending).

Source: `kalga-api/app/database/connection.py` (`init_database()`, lignes 39-551) + repos `kalga-api/app/database/repositories/`.

**Moteur**: SQLite via `aiosqlite`. **DB**: `kalga-api/app/database/kalga.db`.
**Pas de migration tool**: les `ALTER TABLE ADD COLUMN` sont exécutés conditionnellement (try/except pass) dans `connection.py` au démarrage. Les colonnes ajoutées par migration sont marquées `[MIGR]` ci-dessous.
**Toutes les FK** pointent vers `INTEGER PRIMARY KEY AUTOINCREMENT`.
**`users` et `active_sessions` sont EXCLUES** (gérées par Better Auth dans la cible).

Types SQLite: `INTEGER`, `REAL`, `TEXT`, `BLOB`, `TIMESTAMP`/`DATE` (stockés en TEXT/ISO), `BOOLEAN` (stocké INTEGER 0/1), `VARCHAR(n)` (= TEXT, longueur indicative).

---

## 1. `merchants` (conn.py L39-53 + migrations L57-99, 420, 507-521)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| name | TEXT | NOT NULL |
| phone | TEXT | UNIQUE NOT NULL |
| business_name | TEXT | |
| address | TEXT | |
| latitude | REAL | |
| longitude | REAL | |
| away_mode_enabled | BOOLEAN | DEFAULT 0 |
| working_hours | TEXT | (JSON) |
| away_message | TEXT | |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| logo_path | TEXT | [MIGR] storefront |
| about | TEXT | [MIGR] storefront |
| tagline | TEXT | [MIGR] storefront |
| banner_path | TEXT | [MIGR] storefront |
| bot_tone | TEXT | [MIGR] DEFAULT 'casual' |
| bot_style | TEXT | [MIGR] DEFAULT 'flexible' |
| bot_catchphrase | TEXT | [MIGR] |
| payment_methods | TEXT | [MIGR] (JSON, C2 send_payment_info) |
| stock_alert_days | INTEGER | [MIGR] DEFAULT 3 |
| stock_alerts_enabled | BOOLEAN | [MIGR] DEFAULT 1 |
| waitlist_enabled | BOOLEAN | [MIGR] DEFAULT 1 |
| low_stock_alert_global | INTEGER | [MIGR] DEFAULT 5 |

**Enums** (validés dans `routers/merchants.py` L266-267):
- `bot_tone` ∈ `{casual, formal, friendly, professional}` (default `casual`)
- `bot_style` ∈ `{flexible, firm, playful}` (default `flexible`)

---

## 2. `products` (conn.py L108-124 + migrations L103, 485-501)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| merchant_id | INTEGER | NOT NULL → FK merchants(id) |
| name | TEXT | NOT NULL |
| code | TEXT | UNIQUE NOT NULL |
| price | REAL | NOT NULL |
| min_price | REAL | NOT NULL (prix plancher négo) |
| description | TEXT | |
| image_path | TEXT | |
| group_id | TEXT | (regroupement variantes) |
| variant_name | TEXT | |
| is_active | BOOLEAN | DEFAULT 1 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| **embedding** | **BLOB** | **[MIGR] vecteur CLIP recherche visuelle par photo** |
| out_of_stock_mode | TEXT | [MIGR] DEFAULT 'waitlist' |
| last_stock_alert_at | TIMESTAMP | [MIGR] |
| stock_quantity | INTEGER | [MIGR] DEFAULT -1 |
| low_stock_threshold | INTEGER | [MIGR] DEFAULT 5 |
| is_available | BOOLEAN | [MIGR] DEFAULT 1 |

**FK**: `merchant_id → merchants(id)`

**`embedding` BLOB**: vecteur CLIP pour matching photo→produit. Sérialisé via numpy `.tobytes()`. **DOIT être EXCLU de la sérialisation JSON** (cf. commit `699b071`). Lu seulement par le pipeline vision (`product_repo.get_products_with_embeddings()` L245).

**Stock — sémantique (`stock_quantity`)** (product_repo L316-361):
- `stock_quantity = -1` → **illimité** (`is_unlimited`). Pas de décrément.
- `stock_quantity = 0` → **rupture** (`is_out_of_stock`).
- `0 < stock_quantity <= low_stock_threshold` → **stock bas** (`is_low`).
- `stock_quantity > low_stock_threshold` → **ok**.

**Statut stock dérivé** (`routers/stock.py` L92, ordre de tri L101) — **valeurs exactes**:
`"out_of_stock"` | `"low_stock"` | `"ok"` | `"unlimited"` (priorité tri: out_of_stock=0, low_stock=1, ok=2, unlimited=3).

**`out_of_stock_mode`** ∈ `{waitlist, alert, suspend, preorder}` (validé `routers/stock.py` L199, default `waitlist`).

---

## 3. `categories` (conn.py L205-216)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| merchant_id | INTEGER | NOT NULL → FK merchants(id) |
| name | TEXT | NOT NULL |
| icon | TEXT | DEFAULT '📦' |
| color | TEXT | DEFAULT '#667eea' |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**FK**: `merchant_id → merchants(id)`. **UNIQUE(merchant_id, name)**.

---

## 4. `conversations` (conn.py L127-140)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| merchant_id | INTEGER | NOT NULL → FK merchants(id) |
| product_id | INTEGER | NOT NULL → FK products(id) |
| client_phone | TEXT | NOT NULL |
| status | TEXT | DEFAULT 'active' |
| current_offer | REAL | (dernière offre prix en cours) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**FK**: `merchant_id → merchants(id)`, `product_id → products(id)`.

**`status` — VALEURS RÉELLES** (collectées dans `chat_service.py`, `conversation_ai.py`, `conversation_repo.py`, `merchant_commands`):
- `active` (default, initial)
- `negotiating` (négo prix en cours — chat_service L738/757, conversation_ai L511)
- `agreed` (accord trouvé — chat_service L747)
- `pending_delivery` (vente conclue, livraison à venir — état VIVANT — chat_service L741/780)
- `pending_pickup` (vente conclue, retrait en boutique — état VIVANT — chat_service L744)
- `completed` (vente finalisée — chat_service L564, chat.py L209, sales_management L36)
- `abandoned` (abandonnée par marchand — sales_management L65)
- `ended` (clôturée par le bot — chat_service L761)
- `expired` (cleanup auto après 7j — conversation_repo L266, `cleanup_expired` passe `active`/`negotiating` → `expired`)

États "VIVANTS" (négo non terminée): `active`, `negotiating`, `pending_pickup`, `pending_delivery` (conversation_repo L36 exclut `ended`/`completed`/`abandoned`).
États "clôturés positifs": `completed`, `ended` (conversation_repo L87).
Ventes (stats `sales_count`/`revenue`): `status = 'completed'` (stats_repo L191-192).

---

## 5. `messages` (conn.py L143-152)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| conversation_id | INTEGER | NOT NULL → FK conversations(id) |
| content | TEXT | NOT NULL |
| is_from_client | BOOLEAN | NOT NULL (1=client, 0=bot/marchand) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**FK**: `conversation_id → conversations(id)`.

---

## 6. `client_history` (conn.py L219-238 + migrations L426-438)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| merchant_id | INTEGER | NOT NULL → FK merchants(id) |
| client_phone | TEXT | NOT NULL |
| total_conversations | INTEGER | DEFAULT 0 |
| total_purchases | INTEGER | DEFAULT 0 |
| total_spent | REAL | DEFAULT 0 |
| avg_negotiation_discount | REAL | DEFAULT 0 |
| last_purchase_date | TIMESTAMP | |
| last_interaction_date | TIMESTAMP | |
| preferred_categories | TEXT | (JSON) |
| negotiation_style | TEXT | DEFAULT 'normal' |
| notes | TEXT | |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| memory_facts | TEXT | [MIGR] (JSON — LTM faits sémantiques) |
| last_session_summary | TEXT | [MIGR] (résumé dernière session) |
| preferences | TEXT | [MIGR] (JSON) |
| conversation_summaries | TEXT | [MIGR] (JSON — résumés épisodiques) |

**FK**: `merchant_id → merchants(id)`. **UNIQUE(merchant_id, client_phone)**.

**`negotiation_style`** (default `normal`) — calculé par `_determine_negotiation_style()` (client_history_repo L194). Valeurs observées dans le code: `normal` (default). Les autres valeurs sont dérivées dynamiquement de `avg_discount`/`purchase_count` (lire `client_history_repo.py:194` pour la table de décision exacte si besoin — non énumérées en littéraux fixes).
Les 4 colonnes `[MIGR]` implémentent la mémoire 3 couches (STM/LTM/épisodique) — cf. `.claude/rules/memory-injection.md`.

---

## 7. `knowledge_base` (conn.py L367-379)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| merchant_id | INTEGER | NOT NULL → FK merchants(id) |
| question | TEXT | NOT NULL |
| answer | TEXT | NOT NULL |
| keywords | TEXT | (mots-clés matching) |
| source | TEXT | DEFAULT 'human_reply' |
| usage_count | INTEGER | DEFAULT 0 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**FK**: `merchant_id → merchants(id)`.
**`source`** default `human_reply` (réponses marchands capturées pour apprentissage).

---

## 8. `follow_ups` (conn.py L188-202)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| conversation_id | INTEGER | NOT NULL → FK conversations(id) |
| merchant_id | INTEGER | NOT NULL → FK merchants(id) |
| client_phone | TEXT | NOT NULL |
| scheduled_at | TIMESTAMP | NOT NULL |
| message | TEXT | NOT NULL |
| status | TEXT | DEFAULT 'pending' |
| sent_at | TIMESTAMP | |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**FK**: `conversation_id → conversations(id)`, `merchant_id → merchants(id)`.

**`status` — VALEURS RÉELLES** (`followup_service.py`):
- `pending` (default — en attente d'envoi, L93/130/153)
- `sent` (envoyée — L201/249)
- `cancelled` (annulée car conv reprise — L129/181)
- `failed` (échec envoi — L230)

Scheduler background interval 60s (`followup_service.py`).

---

## 9. `conversation_feedback` (conn.py L382-397)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| conversation_id | INTEGER | NOT NULL → FK conversations(id) |
| merchant_id | INTEGER | NOT NULL → FK merchants(id) |
| client_phone | TEXT | NOT NULL |
| client_message | TEXT | NOT NULL |
| bot_response | TEXT | NOT NULL |
| feedback_type | TEXT | DEFAULT 'bad_response' |
| notes | TEXT | |
| kb_entry_id | INTEGER | (lien vers knowledge_base.id si corrigé) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**FK**: `conversation_id → conversations(id)`, `merchant_id → merchants(id)`.

**`feedback_type` — VALEURS RÉELLES** (`routers/chat.py` L486-489, `knowledge_repo.py` L270):
- `bad_response` (default — mauvaise réponse signalée)
- `good_response`
- `auto_flagged` (détecté automatiquement — knowledge_repo L270, chat_service L1156)

---

## 10. `product_waitlist` (conn.py L447-464)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| merchant_id | INTEGER | NOT NULL → FK merchants(id) |
| product_id | INTEGER | NOT NULL → FK products(id) |
| client_phone | TEXT | NOT NULL |
| client_name | TEXT | |
| status | TEXT | DEFAULT 'waiting' |
| conversation_id | INTEGER | |
| offered_price | REAL | |
| notified_at | TIMESTAMP | |
| expires_at | TIMESTAMP | |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**FK**: `merchant_id → merchants(id)`, `product_id → products(id)`.

**`status` — VALEURS RÉELLES** (`waitlist_repo.py`):
- `waiting` (default — en file d'attente, L35/46/79/104/138/153)
- `notified` (client notifié du restock — L123/136)

---

## 11. `stock_events` (conn.py L467-481) — journal append-only

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| merchant_id | INTEGER | NOT NULL → FK merchants(id) |
| product_id | INTEGER | NOT NULL → FK products(id) |
| event_type | TEXT | NOT NULL |
| quantity_delta | INTEGER | NOT NULL (variation signée) |
| quantity_after | INTEGER | NOT NULL (stock résultant) |
| conversation_id | INTEGER | |
| notes | TEXT | |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**FK**: `merchant_id → merchants(id)`, `product_id → products(id)`.

**`event_type` — VALEURS RÉELLES** (collectées dans services/handlers):
- `restock` (réappro — stock.py L159, merchant_commands/service.py L365)
- `out_of_stock` (passage rupture — service.py L434, chat_service L865, waitlist_repo L258)
- `sale` (vente — chat_service L828/856)

---

## 12. `daily_stats` (conn.py L155-170)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| merchant_id | INTEGER | NOT NULL → FK merchants(id) |
| date | DATE | NOT NULL |
| conversations_count | INTEGER | DEFAULT 0 |
| messages_count | INTEGER | DEFAULT 0 |
| sales_count | INTEGER | DEFAULT 0 |
| revenue | REAL | DEFAULT 0 |
| unique_clients | INTEGER | DEFAULT 0 |
| avg_response_time | REAL | |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**FK**: `merchant_id → merchants(id)`. **UNIQUE(merchant_id, date)**.

---

## 13. `analytics_events` (conn.py L173-185)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| merchant_id | INTEGER | NOT NULL → FK merchants(id) |
| event_type | TEXT | NOT NULL |
| product_id | INTEGER | (pas de FK déclarée) |
| conversation_id | INTEGER | (pas de FK déclarée) |
| client_phone | TEXT | |
| data | TEXT | (JSON payload) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**FK**: `merchant_id → merchants(id)` (seule FK; product_id/conversation_id non contraints).

**`event_type` — VALEURS observées** (services):
`new_conversation` (chat_service L580), `sale` (L828/856), `out_of_stock` (L865), `out_of_stock_inquiry` (L160). Champ libre (NOT NULL), pas de whitelist stricte.

---

## 14. `subscriptions` (conn.py L265-282 + migrations L348-356)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| merchant_id | INTEGER | NOT NULL **UNIQUE** → FK merchants(id) |
| plan | TEXT | DEFAULT 'trial' |
| status | TEXT | DEFAULT 'active' |
| start_date | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| end_date | TIMESTAMP | |
| trial_ends_at | TIMESTAMP | |
| messages_limit | INTEGER | DEFAULT 500 |
| messages_used | INTEGER | DEFAULT 0 |
| products_limit | INTEGER | DEFAULT 10 |
| features | TEXT | (JSON) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| payment_method | VARCHAR(50) | [MIGR] |
| payment_reference | VARCHAR(100) | [MIGR] |
| activated_by | INTEGER | [MIGR] (user id ayant activé) |

**FK**: `merchant_id → merchants(id)` (1:1, UNIQUE).

**`plan` — VALEURS RÉELLES** (`subscription_repo.py` L257-260): `trial` (default) | `starter` | `pro` | `enterprise`.
**`status` — VALEURS RÉELLES** (`subscription_repo.py` L255-256, L228/238): `active` (default) | `expired`. (Cleanup auto: `trial` dont `trial_ends_at` passé OU non-trial dont `end_date` passé → `expired`.)

---

## 15. `activation_codes` (conn.py L315-328)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| merchant_id | INTEGER | NOT NULL → FK merchants(id) |
| code | VARCHAR(8) | NOT NULL **UNIQUE** |
| status | VARCHAR(20) | DEFAULT 'pending' |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| used_at | TIMESTAMP | |
| expires_at | TIMESTAMP | |
| created_by | INTEGER | → FK users(id) |

**FK**: `merchant_id → merchants(id)`, `created_by → users(id)` (Better Auth side).

**`status` — VALEURS RÉELLES** (`activation_repo.py`):
- `pending` (default — code émis, non utilisé, L39/89/152/197)
- `used` (consommé — L123, set `used_at`)
- `expired` (expiré ou remplacé par un nouveau code pending — L38/111/196)

---

## 16. `admin_audit_logs` (conn.py L300-312)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| admin_user_id | INTEGER | NOT NULL → FK users(id) |
| action | TEXT | NOT NULL |
| target_type | TEXT | (ex: 'merchant', 'subscription') |
| target_id | INTEGER | |
| details | TEXT | (JSON) |
| ip_address | TEXT | |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**FK**: `admin_user_id → users(id)` (Better Auth side). `action`/`target_type` = champs libres.

---

## 17. `storefront_orders` (conn.py L331-344)

| Colonne | Type | Contraintes / Default |
|---|---|---|
| id | INTEGER | PK AUTOINCREMENT |
| merchant_id | INTEGER | NOT NULL → FK merchants(id) |
| product_id | INTEGER | NOT NULL → FK products(id) |
| client_name | TEXT | NOT NULL |
| client_phone | TEXT | NOT NULL |
| message | TEXT | |
| status | TEXT | DEFAULT 'new' |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**FK**: `merchant_id → merchants(id)`, `product_id → products(id)`.

**`status`** default `'new'`. Seul `update_status(order_id, status)` libre existe (`storefront_order_repo.py` L67) — **pas de whitelist d'enum dans le code** (aucun littéral `confirmed`/`cancelled`/`processed` trouvé). Valeur garantie: `new` (insertion). Les autres statuts ne sont pas figés côté backend actuel.

---

## Index (conn.py L400-547)

**Métier (L400-416)**:
- `idx_merchants_phone` ON merchants(phone)
- `idx_products_merchant` ON products(merchant_id)
- `idx_products_code` ON products(code)
- `idx_products_group` ON products(group_id)
- `idx_conversations_merchant` ON conversations(merchant_id)
- `idx_conversations_client` ON conversations(client_phone)
- `idx_conversations_status` ON conversations(status)
- `idx_messages_conversation` ON messages(conversation_id)
- `idx_daily_stats_merchant_date` ON daily_stats(merchant_id, date)
- `idx_analytics_events_merchant` ON analytics_events(merchant_id)
- `idx_analytics_events_type` ON analytics_events(event_type)
- `idx_follow_ups_scheduled` ON follow_ups(scheduled_at, status)
- `idx_follow_ups_conversation` ON follow_ups(conversation_id)
- `idx_categories_merchant` ON categories(merchant_id)
- `idx_client_history_merchant` ON client_history(merchant_id)
- `idx_client_history_client` ON client_history(client_phone)
- `idx_client_history_merchant_client` ON client_history(merchant_id, client_phone)

**Stock (L524-528)**:
- `idx_waitlist_product_status` ON product_waitlist(product_id, status)
- `idx_waitlist_client` ON product_waitlist(client_phone)
- `idx_waitlist_merchant` ON product_waitlist(merchant_id)
- `idx_stock_events_product` ON stock_events(product_id, created_at)
- `idx_stock_events_merchant` ON stock_events(merchant_id, created_at)

**Auth / abonnements / admin (L531-547)** — (les index `users`/`active_sessions` sont listés pour info mais hors scope cible Better Auth):
- `idx_users_email`, `idx_users_merchant`, `idx_users_role` ON users(...) — *hors scope*
- `idx_subscriptions_merchant` ON subscriptions(merchant_id)
- `idx_subscriptions_status` ON subscriptions(status)
- `idx_active_sessions_user`, `idx_active_sessions_token` ON active_sessions(...) — *hors scope*
- `idx_admin_audit_admin` ON admin_audit_logs(admin_user_id)
- `idx_activation_codes_merchant` ON activation_codes(merchant_id)
- `idx_activation_codes_code` ON activation_codes(code)
- `idx_activation_codes_status` ON activation_codes(status)
- `idx_storefront_orders_merchant` ON storefront_orders(merchant_id)
- `idx_storefront_orders_status` ON storefront_orders(status)
- `idx_knowledge_base_merchant` ON knowledge_base(merchant_id)
- `idx_knowledge_base_created` ON knowledge_base(merchant_id, created_at)
- `idx_feedback_merchant` ON conversation_feedback(merchant_id)
- `idx_feedback_conversation` ON conversation_feedback(conversation_id)

---

## Récap enums (référence rapide)

| Table.colonne | Valeurs | Default |
|---|---|---|
| merchants.bot_tone | casual, formal, friendly, professional | casual |
| merchants.bot_style | flexible, firm, playful | flexible |
| products.out_of_stock_mode | waitlist, alert, suspend, preorder | waitlist |
| products (stock_status dérivé) | out_of_stock, low_stock, ok, unlimited | — |
| conversations.status | active, negotiating, agreed, pending_delivery, pending_pickup, completed, abandoned, ended, expired | active |
| follow_ups.status | pending, sent, cancelled, failed | pending |
| conversation_feedback.feedback_type | bad_response, good_response, auto_flagged | bad_response |
| product_waitlist.status | waiting, notified | waiting |
| stock_events.event_type | restock, out_of_stock, sale | (NOT NULL) |
| subscriptions.plan | trial, starter, pro, enterprise | trial |
| subscriptions.status | active, expired | active |
| activation_codes.status | pending, used, expired | pending |
| storefront_orders.status | new (+ champ libre, pas de whitelist) | new |
| analytics_events.event_type | new_conversation, sale, out_of_stock, out_of_stock_inquiry (champ libre) | (NOT NULL) |

**Pièges**:
- `products.embedding` (BLOB CLIP) → exclure de tout JSON (commit `699b071`).
- `stock_quantity = -1` = illimité, PAS rupture. Rupture = `0`.
- `pending_delivery`/`pending_pickup` sont des états VIVANTS (vente conclue mais conv active), pas des états terminaux.
- Vente comptabilisée: `conversations.status = 'completed'` (stats_repo L191).
