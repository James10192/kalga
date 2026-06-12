# KALGA — Data-flow Python (référence pour réécriture Convex)

> Fichier de référence pour agents exécuteurs sans contexte. Source : `kalga-api/app/`.
> Objectif : cartographier toute la persistance + le hot-path chat pour réimplémenter en
> fonctions Convex grossières (peu de mutations/queries, gros payloads), **moteur v2 only**.
> Stack actuelle : FastAPI + SQLite async (`aiosqlite`), pas de migration tool.

---

## État implémenté (2026-06-12)

Plan 004 **PARTIAL** : tranches sûres et vérifiables livrées ; STOP honnête avant les parties
destructives/aveugles (conditions STOP du plan respectées). Aucune opération destructive, rien
committé/pushé, diff laissé dans le working tree.

### LIVRÉ (vérifié bout-en-bout)
- **Fonctions Convex grossières** (gardées par arg-secret `internalKey` validé via
  `assertInternalKey` dans `convex/internal/guard.ts` contre `process.env.INTERNAL_API_KEY` —
  PAS `internalQuery`/`internalMutation`, voir `convex-core.md` État implémenté pour la raison) :
  - `convex/internal/chat.ts` : `getContext` (query — read grossier : marchand+produit+conversation
    +historique+stock+faits LTM en 1 round-trip) ; `commitTurn` (mutation ATOMIQUE — upsert
    conversation + messages + statut/offre + stats jour).
  - `convex/internal/inventory.ts` : `checkProduct`, `listProductsForTools`, `decrementStock`
    (+ append `stockEvents`).
  - `convex/internal/memory.ts` : `upsertMemory`, `saveKnowledgeEntry`.
  - `convex/internal/followups.ts` : `scheduleFollowup` (dédup ATOMIQUE — résout la race
    SELECT-puis-INSERT §4.2), `cancelFollowups`, `prepareFollowup`/`finalizeFollowup`
    (internalMutation), `sendFollowup` (internalAction → bridge `X-Internal-Key`, chaîne le step
    suivant via `ctx.scheduler.runAfter`). **Plus aucun `sleep(60)` côté Convex.**
- **Client Python** : `kalga-api/app/infrastructure/convex_client.py` (`ConvexBackendClient`
  singleton WS, `asyncio.to_thread`, injection auto `internalKey`, `set_admin_auth` si clé).
  `convex_url`/`convex_admin_key` ajoutés à `core/config.py` (+ warning non bloquant).
  `convex>=0.7.0` dans `requirements.txt`.
- **Verrou `/incoming` + `/incoming-media`** : `verify_internal_key` dans `dependencies.py`
  (parité dev : pass si clé vide), attaché en `Depends` sur `routers/chat.py`. Le bridge
  `kalga-whatsapp/src/services/kalga-api.service.js` envoie `X-Internal-Key` sur ses 2 appels
  sortants. 401 sans header confirmé.
- **Quick wins (#8)** : bcrypt dédupliqué (`requirements.txt`), `merchant_commands.py.backup`
  supprimé, `except Exception: pass` muet du hot-path (`chat_service.py`) → `logger.warning`.
- **Tests** : `kalga-api/tests/test_chat_convex.py` (7 tests d'intégration). Suite complète :
  310 passed, 0 régression.

### NON FAIT (STOP volontaire, gate humain)
- **Bascule des ÉCRITURES hot-path** de `chat_service.py` vers `commitTurn` : NON câblée. Raisons :
  (a) le schéma Convex `conversations` n'a PAS `selectedVariantId` ni les champs joints
  `productName`/`productCode`/`price` que le moteur v2 (`dialogue/engine.py`) consomme ;
  (b) v2 est le cerveau PROD par défaut, rewiring aveugle non smoke-testable ici (pas de DeepSeek
  key ni bridge). Reprise = ajouter les champs schéma manquants + reshaper les dicts + smoke chat réel.
- **Suppression v1** (`conversation_ai.py`/`conversation_engine.py`/tools/`_execute_tool`) : NON faite
  (conservée volontairement, même passe que le rewiring hot-path).
- **`followup_service.py` Python** : TOUJOURS en SQLite (`sleep 60` intact). La logique Convex de
  remplacement est livrée et testée côté Convex, mais le câblage Python (remplacer `self.followups.*`
  par des mutations Convex) fait partie du rewiring hot-path en gate.
- **Retrait SQLite/aiosqlite** : NON fait (dépend de la bascule complète du write-path).

### Env dev posés (gitignorés, NON committés — à reposer en prod des 2 côtés, même valeur API↔bridge)
- Convex : `INTERNAL_API_KEY` (`npx convex env set`).
- `kalga-api/.env` : `CONVEX_URL`, `INTERNAL_API_KEY`, `JWT_SECRET_KEY` (généré), `ADMIN_PASSWORD`
  (le `.env` manquait les secrets obligatoires que `config.py` exige au boot — ajout dev nécessaire).

---

## 1. Façade `db.py` + les 13 repositories

### 1.1 La façade `app/database/db.py`

Classe de **compat legacy** qui délègue à 3 repos seulement (`merchants`, `products`,
`conversations`). Le code moderne (chat_service, dialogue) importe les repos directement,
**pas** la façade. Points clés :

- `Database.__init__` instancie `MerchantRepository`, `ProductRepository`, `ConversationRepository`.
- `Database.init()` → `init_database()` (crée le schéma) puis `_run_migrations()`.
- `_run_migrations()` (lignes 39-72) = `ALTER TABLE ... ADD COLUMN` dans des `try/except: pass`
  + `CREATE INDEX IF NOT EXISTS`. **C'est le pattern « migration » de tout le projet** :
  pas d'outil, ALTER conditionnels au démarrage. → En Convex : remplacé par `schema.ts`
  (les colonnes deviennent des champs `v.optional(...)`).
- Singleton : `_db` global + `async def get_db()` (ligne 218) qui init au 1er appel.
- Méthodes notables qui font du **post-join manuel** (à reproduire côté Convex en enrichissant
  le retour) : `get_product_by_code` / `get_product_by_id` rattachent `merchant_phone` +
  `merchant_name` au dict produit (lignes 121-142).
- `generate_group_id()` → `f"GRP-{uuid4().hex[:8].upper()}"`.

> **Décision réécriture** : la façade `db.py` n'a pas d'équivalent Convex. On supprime la
> couche compat ; chaque repo devient un fichier `convex/<domain>.ts` avec `query`/`mutation`.

### 1.2 Connexion (`app/database/connection.py`)

- `get_connection()` = async context manager `aiosqlite` (row_factory = dict-like ; les rows
  s'accèdent par clé `row['x']` ET par index `row[0]`).
- `init_database()` crée le schéma.
- DB path : `kalga-api/app/database/kalga.db` (config `database_path`, défaut `"kalga.db"`).

### 1.3 Inventaire des repos (`app/database/repositories/`)

15 fichiers `.py` (13 repos métier + `base.py` + `__init__.py`). `__init__.py` n'exporte
que 10 classes ; `stats_repo`, `client_history_repo`, `waitlist_repo`, `knowledge_repo` sont
importés via leur factory `get_*` directement par les services.

| Repo (fichier) | Classe | Factory | Table(s) | Rôle |
|---|---|---|---|---|
| `base.py` | `BaseRepository` | — | générique | `get_by_id`, `delete`, `count` |
| `merchant_repo.py` | `MerchantRepository` | `get_merchant_repository` | `merchants` | marchand + mode absence |
| `product_repo.py` | `ProductRepository` | — | `products` | produits, variantes, stock, embeddings CLIP |
| `conversation_repo.py` | `ConversationRepository` | `get_conversation_repository` | `conversations`, `messages` | convs + messages |
| `stats_repo.py` | `StatsRepository` | `get_stats_repository` | `daily_stats`, `events` | analytics |
| `user_repo.py` | `UserRepository` | `get_user_repository` | `users` | auth JWT, admin merchant list |
| `subscription_repo.py` | `SubscriptionRepository` | `get_subscription_repository` | `subscriptions` | trial/plans/limits |
| `client_history_repo.py` | `ClientHistoryRepository` | `get_client_history_repository` | `client_history` + mémoire LTM/épisodique | négo + mémoire |
| `activation_repo.py` | `ActivationRepository` | `get_activation_repository` | `activation_codes` | codes d'activation |
| `storefront_order_repo.py` | `StorefrontOrderRepository` | `get_storefront_order_repository` | `storefront_orders` | commandes boutique |
| `knowledge_repo.py` | `KnowledgeBaseRepository` | — (instancié direct) | `knowledge_base` | KB FAQ + auto-learn |
| `waitlist_repo.py` | `WaitlistRepository` | `get_waitlist_repository` | `waitlist`, `stock_events` | liste d'attente rupture |
| `category_repo.py` | `CategoryRepository` | — | `categories` | catégories produits |

### 1.4 Méthodes par repo (signatures — `app/database/repositories/<file>:<line>`)

**MerchantRepository** (`merchant_repo.py`)
```
get_by_phone(phone) :17          create(name, phone, business_name=None) :27
update(merchant_id, **kwargs) :48     update_location(merchant_id, address, lat, lng) :66
get_all(page=1, limit=20) :84    get_total_count() :100
update_away_settings(...) :106   get_away_settings(merchant_id) :141
is_within_working_hours(working_hours) :168  (sync)
is_merchant_available(merchant_id) -> (bool, str) :200   get_by_id(merchant_id) :228
```

**ProductRepository** (`product_repo.py`) — `_row_to_dict` exclut le BLOB embedding CLIP du JSON
```
get_by_id(id) :22                get_by_code(code) :29
create(...) :39                  create_variants_batch(...) :86
update(product_id, **kwargs) :156    get_by_merchant(...) :173
get_other_variants(product_id, group_id) :193   get_all_in_group(group_id) :211
deactivate(product_id) :225      get_next_code() :229
get_all_with_embeddings(merchant_id) :241    save_embedding(product_id, blob: bytes) :251
update_stock(product_id, qty) :263   decrement_stock(product_id, qty=1) :267
check_stock_status(product_id) :302  -> {quantity, is_low, is_out_of_stock}
get_low_stock_products(merchant_id) :330    get_out_of_stock_products(merchant_id) :347
```

**ConversationRepository** (`conversation_repo.py`)
```
get_active(merchant_id, client_phone, product_id=None) :16
get_recent_closed(merchant_id, client_phone) :65   # ré-ouverture client de retour
create(merchant_id, product_id, client_phone) :97
update(conversation_id, **kwargs) :128            # status, current_offer, selected_variant_id
get_by_merchant(merchant_id, status) :148   get_pending(merchant_id) :192
add_message(conversation_id, content, is_from_client) :211
get_messages(conversation_id) :242         cleanup_expired(days=7) :258
```

**StatsRepository** (`stats_repo.py`)
```
get_or_create_daily_stats(merchant_id, date) :19    increment_conversations(merchant_id) :56
increment_messages(merchant_id, count=1) :71        record_sale(merchant_id, amount) :86
update_unique_clients(merchant_id, count) :103      get_stats_range(...) :120
get_summary_stats(...) :139     get_top_products(...) :177
get_conversion_rate(merchant_id, days=30) :205      get_hourly_activity(merchant_id, days=7) :237
log_event(merchant_id, event_type, product_id, conversation_id, client_phone, data=...) :261
get_recent_events(...) :290
```

**ClientHistoryRepository** (`client_history_repo.py`) — porte aussi la mémoire LTM/épisodique
```
get_client_history(...) :18          create_or_update(...) :50
record_conversation(...) :105        record_purchase(merchant_id, client_phone, amount, original_price, final_price, category) :130
_determine_negotiation_style(...) :194 (sync)
get_negotiation_context(merchant_id, client_phone, product_price, min_price) :215  # -> {recommendation, loyalty_discount, is_returning, ...}
get_top_clients(...) :293
get_memory_facts(merchant_id, client_phone) :318    save_memory_facts(...) :332     # LTM
save_session_summary(...) :345       get_conversation_summaries(...) :375        # épisodique
save_preferences(...) :389           get_preferences(merchant_id, client_phone) :418
```

**WaitlistRepository** (`waitlist_repo.py`)
```
add_to_waitlist(merchant_id, product_id, client_phone, client_name, conversation_id, offered_price) :14
get_waitlist_for_product(...) :59    get_waitlist_count(product_id) :75
get_merchant_waitlist_summary(...) :85   mark_notified(...) :112   clear_waitlist(product_id) :131
is_client_in_waitlist(product_id, client_phone) :144
log_stock_event(merchant_id, product_id, event_type, quantity_delta, quantity_after, conversation_id) :160  # append-only
get_stock_history(...) :185      get_lost_revenue_estimate(...) :202     get_products_out_of_stock_since(...) :234
```

**KnowledgeBaseRepository** (`knowledge_repo.py`) — `extract_keywords(text, max=8)` module-level
```
save_entry(merchant_id, question, answer, source) :94    search(...) :119
get_all(...) :181     delete_entry(entry_id, merchant_id) :202
seed_defaults(merchant_id) :212      get_insights(merchant_id) :240
```

**UserRepository** (`user_repo.py`) — auth (bcrypt + rehash legacy)
```
get_by_email :57   get_by_id :67   create_user :77   verify_credentials :112
update_password :142   verify_email(token) :161   create_reset_token(email) :187
reset_password_with_token :211   set_active :247   get_all_merchants :257   # admin list (gros join)
get_admin_users :330   ensure_admin_exists(...) :339   # créé au boot si absent
```

**SubscriptionRepository** : `get_by_merchant`, `create_trial`, `upgrade_plan`,
`increment_messages`, `check_limits`, `reactivate`, `get_expiring_soon`, `mark_expired`, `get_stats`.

**ActivationRepository** : `create_code`, `validate_code(code, merchant_phone)`, `get_by_code`,
`get_pending_for_merchant`, `get_pending_merchants`, `expire_old_codes`, `get_activation_history`.

**CategoryRepository** : `create`, `get_by_merchant`, `get_by_name`, `update`, `delete`.

**StorefrontOrderRepository** : `create`, `get_by_merchant`, `update_status`.

---

## 2. Hot-path `chat_service.handle_incoming_message`

Fichier : `app/services/chat_service.py:49-524`. Point d'entrée HTTP :
`app/routers/chat.py` (`POST /api/chat/incoming`, lignes 31/125/143) appelé par le bridge Node.
`ChatService.__init__` (l.33-47) câble : `merchants, products, conversations, notifications,
stats, followups, client_history, waitlist`.

### Étapes + appels DB (numérotation du code conservée)

| # | Ligne | Action | Appels DB / service |
|---|---|---|---|
| 1 | 66-74 | Identifier marchand (+ fallback n° ivoirien `225`→`2250`) | `merchants.get_by_phone` (×1-2) |
| 1.5 | 85 | Mode absence | `merchants.is_merchant_available(id)` |
| 2 | 96 | Trouver/créer conv → `_get_or_create_conversation` | voir détail ci-dessous |
| 3 | 114 | Enregistrer message client | `conversations.add_message(conv_id, msg, is_from_client=True)` |
| 3.5 | 122 | Stat messages | `stats.increment_messages(merchant_id, 1)` (try/except) |
| 4 | 127-185 | 1er message + stock : waitlist/suspend | `conversations.get_messages`, `products.check_stock_status`, `waitlist.get_waitlist_count`/`is_client_in_waitlist`, `conversations.add_message`, `stats.log_event` |
| 4.1 | 188-196 | Réponse OUI waitlist → `_check_waitlist_reply` | `conversations.get_messages`, `products.check_stock_status`, `waitlist.is_client_in_waitlist`/`add_to_waitlist`/`get_waitlist_count`, `conversations.add_message` |
| 4.5 | 201-206 | Mémoriser variante sélectionnée → `_find_and_save_selected_variant` | `products.get_all_in_group`, `conversations.update(selected_variant_id=...)` |
| 5 | 210-217 | Cas spéciaux catalogue → `_handle_special_requests` | `merchants.get_by_phone`, `products.get_by_merchant`, `conversations.add_message` |
| 6 | 220-228 | Charger historique + contexte négo | `conversations.get_messages`, `client_history.get_negotiation_context` (via `_get_negotiation_context`) |
| **TOGGLE** | 237-328 | **v1 vs v2** (voir §3) | v2 : `client_history.get_memory_facts` ; v1 : `generate_response(...)` |
| 6.1 | 339-374 | Dispatch tool_call (**v1 only**) → `_execute_tool` | `products.get_by_id`/`get_other_variants` ; LTM async `ltm.extract_and_save` si statut terminal |
| 6 | 377-380 | Update conv (status + current_offer) | `conversations.update(conv_id, status=, current_offer=)` |
| — | 392-396 | Enregistrer réponse bot | `conversations.add_message(..., is_from_client=False)` |
| 6.5 | 399-408 | Auto-flag question sans réponse → `_auto_flag_unanswered` | **SQL brut** sur `conversation_feedback` (SELECT COUNT puis INSERT, l.1150-1172) |
| 7 | 411-419 | Notifications marchand → `_handle_notifications` | voir détail ci-dessous |
| 7.5 | 423-451 | Préparer localisation (lat/lng/address marchand) | lecture dict `merchant` (pas de DB) |
| 7.6 | 454-480 | Goodbye fin transaction + auto-learn → `_auto_learn_from_deal` | `KnowledgeBaseRepository().save_entry(source="auto_learned_deal")` |
| 8 | 483-489 | Relances → `_handle_follow_ups` | `followups.cancel_follow_ups`, `followups.schedule_follow_up` |
| 9 | 492-511 | TTS OGG si `use_voice` | `tts_service.text_to_ogg` (pas de DB) |
| ret | 513-524 | `BotResponse(...)` renvoyé au bridge | — |

**`_get_or_create_conversation`** (l.526-607) : extrait code produit (`extract_product_code`),
`products.get_by_code`, `conversations.get_active`, fermeture+recréation si pending_* et code
re-mentionné (l.560-565), `conversations.create` + `stats.increment_conversations`+`log_event`,
sinon `conversations.get_active`/`get_recent_closed` + `products.get_by_id`.

**`_handle_notifications`** (l.795-921) : sur vente (`pending_delivery`/`pending_pickup`) →
`stats.record_sale`+`log_event`, `_record_client_purchase` (`client_history.record_purchase`),
`products.decrement_stock`+`check_stock_status`, `waitlist.log_stock_event` (sale + out_of_stock),
`notifications.notify_low_stock`/`notify_out_of_stock`/`notify_sale`.

> **Points d'appel DB à remplacer par des fonctions Convex grossières** : tout `self.<repo>.<m>(...)`
> et les 2 blocs SQL brut (`_auto_flag_unanswered` l.1150, `db.py.get_product_variants` l.155).
> Stratégie cible : 1 mutation Convex `chat.handleIncoming` qui fait tout le write-path en une
> transaction, + queries grossières `chat.getContext(merchantPhone, clientPhone, productCode)`
> renvoyant `{merchant, product, conversation, history, negotiationContext, memoryFacts}` en un
> seul round-trip (au lieu des ~10 appels DB séquentiels actuels).

---

## 3. TOGGLE moteur v1 vs v2 — comment supprimer v1 proprement

### 3.1 Le drapeau

`app/core/config.py:34` :
```python
dialogue_engine: str = "v2"   # "v2" = pipeline dialogue/ (DÉFAUT) ; "v1" = legacy
```

### 3.2 Le branchement dans `chat_service.py` (l.237-340)

```python
# l.241-243
engine_v2 = None
from ..core.config import settings as _settings
if _settings.dialogue_engine == "v2":
    from .dialogue.engine import respond as dialogue_respond
    # l.247-256 : geste fidélité → v2_floor (floor_override)
    # l.259-267 : LTM → v2_memory (memory_extra), via client_history.get_memory_facts
    engine_v2 = await dialogue_respond(client_message=..., conversation=..., product=...,
                                       merchant=..., history=..., floor_override=v2_floor,
                                       memory_extra=v2_memory)          # l.269-277

images_v2 = None ; human_takeover_v2 = False
if engine_v2 is not None:                                              # l.285-316  CHEMIN V2
    bot_response = engine_v2.message ; price_offer = engine_v2.new_offer
    new_status = engine_v2.new_status ; send_location = engine_v2.send_location
    use_voice = "[🎤 Vocal transcrit" in (message.message or "")
    images_v2 = engine_v2.images_to_send ; human_takeover_v2 = engine_v2.human_takeover
    # notify_reason == "delivery_address" → notify_sale ; "human_request" → send_message
else:                                                                  # l.317-328  CHEMIN V1
    bot_response, price_offer, deal_accepted, new_status, send_location, use_voice = \
        await generate_response(client_message=..., product=..., conversation_history=...,
            current_offer=..., conversation_status=..., negotiation_context=...,
            merchant_data=..., tracer=..., client_phone=...)
```

Et le **dispatch tool_call v1 uniquement** (l.339-340) :
```python
images_to_send = images_v2
if engine_v2 is None and bot_response and is_tool_call(bot_response):   # v1 only
    tool = parse_tool_call(bot_response)
    ... await self._execute_tool(...)   # l.343
```

### 3.3 Surface v1 à retirer (réécriture = v2 only, pas de fallback)

- **Façade v1** : `app/services/conversation_ai.py` (réexporte depuis `app/services/ai/`) — `generate_response`, `analyze_conversation_health`, `extract_product_code`, détecteurs.
- **Moteur v1** : `app/services/ai/conversation_ai.py` (33 KB), `ai/conversation_engine.py`, `ai/tools.py`, `ai/deepseek_client.py` (partagé avec v2 via adapter — **garder le client brut**), `ai/fallback_responses.py`, `ai/memory/*`.
- **Helpers tool_call v1** : `is_tool_call`, `parse_tool_call` (importés `from .ai.conversation_ai`, l.18) + méthode `_execute_tool` (l.651-793).

### 3.4 Suppression propre (étapes)

1. Dans `chat_service.py` : supprimer le bloc `if _settings.dialogue_engine == "v2"` (garder
   son contenu **inconditionnel**), supprimer la branche `else: generate_response(...)` (l.317-328),
   supprimer le bloc `if engine_v2 is None and is_tool_call(...)` (l.340-352) et la méthode
   `_execute_tool`. `engine_v2` devient toujours non-None (sinon erreur explicite / repli défini
   côté v2). `images_to_send = engine_v2.images_to_send`.
2. Conserver `_find_and_save_selected_variant`, `_handle_special_requests`, `_check_waitlist_reply`,
   `_auto_flag_unanswered`, `_auto_learn_from_deal`, `_handle_notifications`, `_handle_follow_ups` :
   ce sont l'**aval commun**, indépendant du moteur.
3. Retirer l'import l.18 `from .ai.conversation_ai import is_tool_call, parse_tool_call` et l.17
   `generate_response, extract_product_code, analyze_conversation_health` (garder seulement
   `extract_product_code`/`analyze_conversation_health` s'ils restent utilisés —
   `extract_product_code` est utilisé l.538, `analyze_conversation_health` l.1147 ; les déplacer
   vers `ai/detectors.py` si on supprime la façade).
4. Supprimer le champ `dialogue_engine` de `config.py` (plus de toggle).
5. Côté Convex : v1 n'est **pas porté du tout**. Seul `dialogue/` (pipeline v2) est réécrit.

### 3.5 Contrat v2 (ce que la réécriture doit reproduire)

`dialogue/engine.py:respond(...)` → `EngineResponse` (l.24-34) :
```
message, new_status, new_offer, send_location, images_to_send,
human_takeover, notify_reason, delivery_address, facts
```
Pipeline interne : `orchestrator.run_pipeline(client_message, db_status, history, product,
current_offer, llm, persona, memory_block, floor_override)` (l.104). Modules :
`understanding.py` (21 KB, NLU), `policy.py` (9 KB, règles), `negotiation.py`, `sale_state.py`,
`output_guard.py`, `sanitizer.py`, `speech.py`, `deepseek_adapter.py` (wrappe le client DeepSeek),
`llm_classifier.py`, `intents.py`, `actions.py` (`ActionType`). Les images + catalogue sont
**résolus depuis la BASE** dans `engine.py` (`_resolve_images` l.57, catalogue l.130-149) —
le LLM n'invente jamais la liste produits. **DÉFENSIF** : toute exception → `return None` (l.168).
En Convex, comme on garde v2 only, ce `None` doit devenir une réponse de secours déterministe.

---

## 4. Scheduler follow-up (boucle 60s + race condition)

Fichier : `app/services/followup_service.py`. Démarré dans `main.py:129-130`
(`await followup_service.start_scheduler(interval_seconds=60)`), arrêté l.146
(`followup_service.stop_scheduler()`). (Un 2e scheduler stock tourne à 300s, `main.py:135`.)

### 4.1 Boucle 60s (`start_scheduler` l.272-295)

```python
async def _scheduler_loop():
    while self._running:
        try:
            sent = await self.process_pending_follow_ups()   # l.287
        except Exception as e:
            logger.error(...)
        await asyncio.sleep(interval_seconds)                # l.293  (60s)
self._task = asyncio.create_task(_scheduler_loop())          # l.295
```
`process_pending_follow_ups` (l.256-270) : `get_pending_follow_ups()` puis `send_follow_up`
pour chacune avec `await asyncio.sleep(1)` anti-spam entre envois.

### 4.2 Race SELECT-puis-INSERT (`schedule_follow_up` l.88-115)

```python
async with get_connection() as db:
    cursor = await db.execute(
        "SELECT id FROM follow_ups WHERE conversation_id = ? AND status = 'pending'", (conv_id,))
    existing = await cursor.fetchone()        # l.97
    if existing:
        return None                           # l.99  (dédup)
    cursor = await db.execute(
        "INSERT INTO follow_ups (conversation_id, merchant_id, client_phone, scheduled_at, message, status) "
        "VALUES (?, ?, ?, ?, ?, 'pending')", (...))   # l.103-110
    await db.commit()
```
> **RACE** : SELECT-then-INSERT non atomique (l.97 → l.103). Deux appels concurrents (ex. client
> répond pendant que le scheduler 60s traite) peuvent tous deux voir `existing=None` et insérer
> 2 relances `pending` pour la même conversation. SQLite mono-fichier limite mais ne supprime
> pas le risque (tâches asyncio entrelacées). En Convex : la sérialisation des mutations
> (transactions optimistes + index unique logique) élimine la race — utiliser une query
> `by_conversation_status` + insert dans **la même mutation** (atomique côté Convex).

### 4.3 Autres méthodes (à porter en mutations/queries + crons Convex)

```
cancel_follow_ups(conv_id) :117      # UPDATE pending → cancelled (client a répondu)
get_pending_follow_ups() :141        # SELECT join merchants+conversations+products, scheduled_at<=now LIMIT 50
send_follow_up(followup) :162        # re-check conv status ∈ {active,negotiating,agreed} sinon cancel ;
                                     #   notifications.send_message ; UPDATE sent + INSERT messages ; schedule step+1
_get_current_step(conv_id) :243      # COUNT relances status='sent'
```
Délais : `{1:2h, 2:24h, 3:48h}` (l.43-47). Messages templates `{1,2,3}` (l.24-40), `.format(product=...)`.
Statuts `follow_ups` : `pending|cancelled|sent|failed`.

> **Cible Convex** : remplacer la boucle `asyncio.sleep(60)` par un **cron Convex** (`crons.ts`,
> intervalle 1 min) appelant une mutation `followups.processPending`. `scheduled_at` stocké en
> timestamp ms. `process` lit les `pending` échues, vérifie le statut conv, envoie via action
> (HTTP bridge), update + insert message + planifie le step suivant — le tout en transactions.

---

## 5. Settings (`app/core/config.py`) — ce qui migre vers Convex

Singleton Pydantic `Settings` (env_file `.env`). Variables **obligatoires** (sinon
`sys.exit(1)` l.115) : `jwt_secret_key` (≥32 car., validator l.80), `admin_password` (≥8 car., l.90).

| Setting | Défaut | Rôle | Réécriture Convex |
|---|---|---|---|
| `dialogue_engine` | `"v2"` | toggle moteur | **SUPPRIMÉ** (v2 only) |
| `deepseek_api_key` | `None` | clé LLM ; absent ⇒ fallback | `npx convex env set DEEPSEEK_API_KEY` (action) |
| `deepseek_base_url` | `https://api.deepseek.com/v1` | endpoint | env Convex |
| `deepseek_model` | `deepseek-chat` | modèle | env Convex |
| `deepseek_timeout` / `_max_retries` | `30` / `3` | client | const action |
| `whatsapp_bridge_url` | `http://localhost:3001` | bridge Node | env Convex (action HTTP) |
| `whatsapp_request_timeout` | `10` | timeout bridge | const |
| **`internal_api_key`** | `""` | header `X-Internal-Key` entre API↔bridge (`notification_service.py:23`, `wa_bridge.py:24`, `infrastructure/whatsapp/client.py:32`, `activation_service.py:96`) ; warning si vide (`validate_settings` l.133) | **À GARDER** : secret partagé bridge↔Convex HTTP action. `npx convex env set INTERNAL_API_KEY` |
| **`convex_url`** | *(n'existe pas)* | — | **À AJOUTER** : URL déploiement Convex (le bridge Node POST `/chat/incoming` doit pointer ici au lieu de `kalga-api:8001`) |
| `storefront_base_url` | `http://localhost:8001` | URL boutique (goodbye msg) | domaine wildcard `{slug}.kalga.app` |
| `allowed_origins` | localhost:8001 | CORS | config Convex/Vercel |
| `database_path` | `kalga.db` | SQLite | **SUPPRIMÉ** (Convex) |
| `conversation_expiry_days` | `7` | cleanup convs | cron Convex |
| `session_timeout_minutes` | `10` | STM | logique mémoire |
| `rate_limit_requests`/`_period` | `30`/`minute` | SlowAPI | rate-limit Convex/edge |
| `jwt_secret_key` (OBLIG.) | — | JWT | **remplacé par Better Auth** (Local Install) |
| `jwt_algorithm`/`_access`/`_refresh` | HS256/24h/30j | JWT | Better Auth sessions |
| `admin_email`/`admin_password` (OBLIG.) | `admin@kalga.com`/— | admin boot | seed admin Better Auth |
| `trial_duration_days`/`_messages_limit`/`_products_limit` | `14`/`500`/`10` | quotas trial | table `subscriptions` Convex |

Helpers : `get_settings()` (l.118), `validate_settings()` → warnings non-bloquants (l.123),
`print_startup_warnings()` exécuté au chargement (l.161).

> **À ajouter pour la réécriture** : `convex_url` (côté bridge Node — variable d'env du bridge,
> pas de Python), et conserver `internal_api_key` comme secret partagé bridge↔HTTP action Convex.
> Tout le bloc JWT/admin disparaît au profit de Better Auth (cf. task 003).

---

## 6. Synthèse — write-path à transactionnaliser en Convex

Le hot-path actuel fait ~10-15 appels DB séquentiels par message. Regrouper en **fonctions
grossières** :

- **Query** `chat.getContext(merchantPhone, clientPhone, productCode?)` → renvoie en un appel :
  `merchant` (+ availability), `product` (par code/id + variantes), `conversation` (active ou
  recent_closed), `history` (messages), `negotiationContext`, `memoryFacts`, `stockStatus`.
- **Mutation** `chat.commitTurn({...})` → en une transaction : `add_message(client)` +
  `add_message(bot)` + `update(conversation status/offer/variant)` + `stats.increment*`/`log_event`
  + `record_sale`/`decrement_stock`/`log_stock_event` (si vente) + `record_purchase` +
  `auto_flag`/`auto_learn` + `schedule_follow_up`/`cancel_follow_ups`.
- **Action** `chat.runDialogue(...)` (Node action) : appelle DeepSeek (pipeline v2 porté ou
  proxifié) + bridge WhatsApp HTTP (`X-Internal-Key`) ; ne touche pas la DB directement,
  appelle les query/mutation ci-dessus.
- **Cron** `followups.processPending` (1 min) remplace la boucle `asyncio.sleep(60)` + résout
  la race SELECT/INSERT par atomicité transactionnelle.

Le moteur **v1 entier n'est pas porté** ; seul `app/services/dialogue/` (v2) est réécrit, le
client DeepSeek brut (`ai/deepseek_client.py`) est conservé/proxifié.
