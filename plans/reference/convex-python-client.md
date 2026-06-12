# Référence — Client Python Convex (`convex-py`)

> Source : Context7 `/get-convex/convex-py` (README officiel + llms.txt) — fetché 2026-06-12.
> Usage dans KALGA : le backend **FastAPI** (`kalga-api/`, port 8001) appelle un déploiement Convex
> côté serveur (server-to-server, sans session utilisateur navigateur).

---

## 1. Installation

Le package PyPI s'appelle simplement **`convex`** (pas `convex-py`).

```bash
pip install convex
```

Dans `kalga-api/requirements.txt`, ajouter :

```
convex
```

**Pré-requis** : Python 3.8+. Le client est synchrone par défaut et basé sur **WebSocket**
(pas HTTP REST) — il maintient une connexion et fait des **retries automatiques sur erreurs réseau**.
C'est robuste pour les process longue durée (serveur FastAPI, monitoring temps réel).

---

## 2. Initialisation `ConvexClient(url)`

```python
from convex import ConvexClient

# URL du déploiement Convex (.convex.cloud) — PAS l'URL .convex.site (qui est pour HTTP actions)
client = ConvexClient('https://example-lion-123.convex.cloud')
```

### Pattern recommandé : URL depuis l'environnement (KALGA)

Ne jamais hardcoder l'URL. Suivre le pattern Settings de KALGA
(`from app.core.config import settings`, jamais `os.environ` direct dans la logique métier).

```python
# kalga-api/app/core/config.py — ajouter aux Settings Pydantic
class Settings(BaseSettings):
    convex_url: str            # CONVEX_URL=https://example-lion-123.convex.cloud
    convex_admin_key: str | None = None  # clé de déploiement (voir §4)
```

```python
# Construction du client (singleton recommandé — réutiliser la connexion WebSocket)
from convex import ConvexClient
from app.core.config import settings

client = ConvexClient(settings.convex_url)
if settings.convex_admin_key:
    client.set_admin_auth(settings.convex_admin_key)
```

> **Important** : un `ConvexClient` ouvre une connexion WebSocket persistante. Instancier **une seule fois**
> (au lifespan de l'app FastAPI), pas par requête. Stocker dans un module / dependency injectée.

`.env` (`kalga-api/.env`) :

```
CONVEX_URL=https://example-lion-123.convex.cloud
CONVEX_ADMIN_KEY=...   # ne jamais committer
```

---

## 3. Appeler query / mutation / action par nom + args

Le **nom de fonction** suit la convention `"fichier:export"` (le `:` sépare le module du nom de fonction
Convex). Ex : une fonction `list` exportée dans `convex/messages.ts` → `"messages:list"`.
Les args sont un **dict Python unique** (objet), ou omis.

### query — lecture seule (retry auto réseau)

```python
# Sans arguments
users = client.query("users:list")

# Avec arguments (dict unique)
user = client.query("users:get", {"userId": "abc123"})

# Avec pagination Convex (paginationOpts)
result = client.query("messages:list", {
    "paginationOpts": {"numItems": 10, "cursor": None}
})
print(f"Got {len(result['page'])} messages")
print(f"Has more: {not result['isDone']}")
```

### mutation — écriture (create/update/delete)

```python
# Create — renvoie ce que la mutation Convex retourne (souvent l'_id ou le doc)
result = client.mutation("messages:send", {"author": "Alice", "body": "Hello, World!"})

# Update
client.mutation("users:update", {"userId": "abc123", "name": "Alice Smith"})

# Delete
client.mutation("messages:delete", {"messageId": "msg_456"})
```

### action — effets de bord / appels tiers / non-déterministe

```python
result = client.action("emails:sendWelcome", {"userId": "abc123", "template": "onboarding"})
summary = client.action("ai:summarize", {"documentId": "doc_789", "maxLength": 500})
```

> Les trois méthodes sont **synchrones** (bloquantes). Dans du code FastAPI `async`, les wrapper avec
> `await asyncio.to_thread(client.query, "users:list", {...})` pour ne pas bloquer l'event loop.

```python
import asyncio
users = await asyncio.to_thread(client.query, "users:list")
```

---

## 4. Auth server-to-server (fonctions privilégiées sans session utilisateur)

C'est le point clé pour KALGA : le FastAPI appelle Convex **sans utilisateur navigateur**. Deux niveaux :

### A. `set_admin_auth(deploy_key)` — accès privilégié (RECOMMANDÉ pour backend)

Permet d'exécuter des **fonctions internes** (`internalQuery` / `internalMutation` / `internalAction`)
non exposées publiquement, et de bypasser l'auth utilisateur. La clé vient du **dashboard Convex**
(Settings → Deploy Key / Admin Key).

```python
from convex import ConvexClient

client = ConvexClient(settings.convex_url)

# Clé admin = "deploy key" du dashboard. NE JAMAIS hardcoder ni committer — env var only.
client.set_admin_auth(settings.convex_admin_key)

# Désormais le client peut appeler des fonctions internes/privilégiées
internal_data = client.query("internal:adminStats")
```

> **set_admin_auth** = la bonne approche pour un backend de confiance (server-to-server). La clé de
> déploiement (deploy/admin key) joue le rôle de secret partagé : le serveur FastAPI la détient,
> aucune session utilisateur n'est nécessaire.

### B. `set_auth(jwt_token)` — se faire passer pour un utilisateur précis

À utiliser seulement si le backend doit exécuter une fonction **en tant qu'un utilisateur donné**
(token JWT issu du provider d'auth). Pas le cas d'usage server-to-server standard.

```python
client.set_auth("eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...")  # JWT du provider
user_data = client.query("users:getCurrentUser")            # tourne comme cet utilisateur
client.mutation("messages:send", {"body": "Authenticated message"})

client.clear_auth()  # logout / retour à anonyme
```

### Résumé décisionnel

| Besoin                                               | Méthode                          | Secret                         |
|------------------------------------------------------|----------------------------------|--------------------------------|
| Backend appelle fonctions internes/privilégiées      | `set_admin_auth(key)`            | Deploy/admin key (dashboard)   |
| Backend agit pour le compte d'un user identifié      | `set_auth(jwt)`                  | JWT du provider d'auth         |
| Appel public anonyme                                 | rien                             | —                              |
| Logout / clear                                       | `clear_auth()`                   | —                              |

---

## 5. Gestion d'erreurs

### `ConvexError` — erreurs applicatives levées par les fonctions Convex

Quand une fonction Convex fait `throw new ConvexError(data)`, le client Python lève `ConvexError`.
Le champ **`err.data`** porte la charge utile (dict ou str selon ce que la fonction a thrown).

```python
from convex import ConvexClient, ConvexError

try:
    client.mutation("messages:send", {"body": "Hello", "author": "test_user"})
except ConvexError as err:
    # err.data = ce que la fonction Convex a passé à `new ConvexError(...)`
    if isinstance(err.data, dict):
        code = err.data.get("code")
        if code == "RATE_LIMITED":
            print("Too many requests, please wait")
        elif code == "INVALID_INPUT":
            print(f"Invalid input: {err.data.get('message')}")
    elif isinstance(err.data, str):
        print(f"Error: {err.data}")
except Exception as err:
    # Réseau, serveur, erreurs non applicatives. Le client retry déjà le réseau automatiquement ;
    # ce bloc attrape les échecs définitifs / erreurs serveur.
    print(f"Unexpected error: {err}")
```

**Distinction importante** :
- `ConvexError` = erreur **métier voulue** (validation, rate limit, règle business). `err.data` est exploitable.
- `Exception` générique = erreur technique (réseau définitif, fonction inexistante, serveur). Les erreurs
  réseau transitoires sont **retry automatiquement** par le client avant de remonter.

---

## 6. Conversion de types Python ↔ Convex (pièges)

Quand on passe des args ou lit des résultats, conversions automatiques :

```python
from convex import ConvexInt64

client.mutation("examples:typeDemo", {
    "nullValue":   None,                # → null
    "boolValue":   True,                # → boolean
    "stringValue": "hello",             # → string
    "floatValue":  3.14,                # → number (Float64)
    "intValue":    42,                  # → number (Float64) ⚠ les int Python deviennent des Float64 !
    "bigIntValue": ConvexInt64(2**60),  # → bigint (pour vrais entiers 64-bit / précision)
    "bytesValue":  b"binary",           # → ArrayBuffer
    "arrayValue":  [1, 2, 3],           # → Array
    "tupleValue":  (1, 2, 3),           # → Array (les tuples sont coercés en arrays)
    "objectValue": {"key": "val"},      # → object
})
```

**Pièges** :
- Un `int` Python est envoyé comme **Float64**, pas comme entier Convex. Pour un vrai `bigint`
  (ID, timestamp microseconde, précision > 2^53), utiliser `ConvexInt64(...)`.
- Les `bigint` renvoyés par Convex arrivent comme `ConvexInt64` côté Python (tester via `isinstance`).
- Documents Convex renvoyés : dicts avec `_id` (str) et `_creationTime` (float ms).

---

## 7. Souscriptions temps réel (optionnel — `subscribe`)

Le client supporte les subscriptions WebSocket live (résultats re-poussés quand la donnée change).
Utile si le FastAPI veut réagir aux changements, mais **bloquant** — réserver à un worker dédié,
pas au chemin requête/réponse HTTP.

```python
subscription = client.subscribe("messages:list", {})

# Itération synchrone (boucle infinie — prévoir un break / thread dédié)
for messages in subscription:
    print(f"Count: {len(messages)}")
    if len(messages) >= 10:
        break
subscription.unsubscribe()

# Itération asynchrone
async def watch_messages():
    sub = client.subscribe("messages:list", {})
    async for messages in sub:
        print(f"Got {len(messages)} messages")
        break
    sub.unsubscribe()
```

---

## 8. Checklist d'intégration KALGA (FastAPI → Convex)

1. `pip install convex` + ajouter `convex` à `kalga-api/requirements.txt`.
2. Ajouter `CONVEX_URL` (et `CONVEX_ADMIN_KEY` si fonctions internes) aux `Settings` Pydantic
   (`app/core/config.py`), jamais lire `os.environ` directement dans la logique métier.
3. Instancier **un seul** `ConvexClient(settings.convex_url)` au lifespan de l'app (connexion WS persistante).
4. `client.set_admin_auth(settings.convex_admin_key)` pour l'accès server-to-server privilégié.
5. Wrapper les appels bloquants en `await asyncio.to_thread(client.query, ...)` dans le code `async`.
6. Toujours encapsuler les appels dans `try/except ConvexError` (métier) + `except Exception` (technique).
7. Noms de fonctions = `"module:export"` (ex : `"products:list"`, `"chat:incoming"`).
8. Args = un dict unique ; attention `int` Python → Float64 (utiliser `ConvexInt64` pour les vrais bigint).
