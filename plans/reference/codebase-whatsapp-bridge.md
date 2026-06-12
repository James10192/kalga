# Référence — Bridge WhatsApp & ingestion (envoi OTP + verrouillage /incoming)

But : (a) câbler l'envoi d'OTP via le bridge, (b) verrouiller `/api/chat/incoming` côté FastAPI.
État au **2026-06-12**. Bridge = Node.js Express + Baileys, port **3001**. API = FastAPI, port **8001**.

Fait CLÉ découvert : **le bridge protège DÉJÀ ses POST avec `X-Internal-Key`** (middleware existant).
Le maillon faible est **côté API** : `/api/chat/incoming` n'a **aucune** vérification de clé.

---

## 1. Endpoint d'ENVOI du bridge (pour envoyer l'OTP)

### Route exacte
`POST http://localhost:3001/send` — fichier `kalga-whatsapp/src/api/routes/send.routes.js` (lignes 13-35).
Montée à la racine `/` via `kalga-whatsapp/src/api/routes/index.js` (`router.use('/', sendRoutes)`), donc l'URL finale est `/send` (PAS `/api/send`).

### Payload JSON
```json
{
  "merchant_phone": "225141540178",
  "to": "225141540178",
  "message": "Votre code KALGA: 123456"
}
```
- Les 3 champs sont **requis** (sinon 400 `merchant_phone, to et message requis`).
- `merchant_phone` = la session WhatsApp qui ENVOIE (doit être connectée/`ready`, sinon 503 `Client WhatsApp non prêt`).
- `to` = destinataire. Pour un OTP envoyé au marchand lui-même : `to === merchant_phone`.
- Numéros = chiffres uniquement, format international sans `+` (ex `225...`).

### Réponse
```json
{ "success": true, "to": "225...", "message": "..." }   // 200
{ "error": "Client WhatsApp non prêt" }                  // 503 si session pas ready
{ "error": "Failed to send message" }                    // 500
```

### Auth interne du bridge (OBLIGATOIRE sur POST)
Middleware `internalAuthMiddleware` dans `kalga-whatsapp/src/loaders/express.js` (lignes 13-25) :
```js
function internalAuthMiddleware(req, res, next) {
    if (req.method === 'GET') return next();              // GET public (health/status/QR)
    if (!config.internalApiKey) return next();            // si clé vide → pas de protection (dev)
    const provided = req.headers['x-internal-key'];
    if (provided !== config.internalApiKey) {
        return res.status(401).json({ error: 'Unauthorized — invalid or missing X-Internal-Key header' });
    }
    next();
}
```
- Header attendu : **`X-Internal-Key`** (lu en lowercase `x-internal-key` par Express).
- Clé chargée depuis `config.internalApiKey` = `process.env.INTERNAL_API_KEY` (`kalga-whatsapp/src/config/index.js:43`).
- Si `INTERNAL_API_KEY` non défini → la protection est **désactivée** (mode dev). En prod il FAUT la définir des deux côtés.

### Pattern d'appel Python existant (à RÉUTILISER tel quel pour l'OTP)
Déjà implémenté dans `kalga-api/app/services/activation_service.py:92-108` (`_send_whatsapp_message`). C'est exactement un envoi d'OTP/code :
```python
async def _send_whatsapp_message(self, phone: str, message: str) -> dict:
    headers = {}
    if getattr(settings, 'internal_api_key', ''):
        headers["X-Internal-Key"] = settings.internal_api_key
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{self.whatsapp_url}/send",
            json={"merchant_phone": phone, "to": phone, "message": message},
            headers=headers,
        )
```
Le client canonique est `WhatsAppBridgeClient.send_message()` dans
`kalga-api/app/infrastructure/whatsapp/client.py:52-72`, qui injecte déjà `X-Internal-Key`
(lignes 32-33) et POST sur `/send`. **Préférer ce client** pour l'OTP :
```python
from app.infrastructure.whatsapp.client import whatsapp_client
ok = await whatsapp_client.send_message(
    merchant_phone="225141540178",  # session émettrice (doit être ready)
    to="225141540178",             # destinataire OTP
    message="Votre code KALGA: 123456",
)
```
`base_url` = `settings.whatsapp_bridge_url` (défaut `http://localhost:3001`, `config.py:37`).

### Autres routes d'envoi (contexte)
- `POST /send-image` — `{merchant_phone, to, image_path, caption?}`
- `POST /send-location` — `{merchant_phone, to, latitude, longitude, name?, address?}`
Mêmes règles d'auth + même check `isClientReady`.

---

## 2. Comment le bridge appelle `kalga-api` `/api/chat/incoming`

### Où
`kalga-whatsapp/src/services/kalga-api.service.js` → `sendIncomingMessage()` (lignes 23-49).
Déclenché par `message.service.js::_processClientBatch()` (ligne 191) après agrégation des rafales client.

### Le fetch exact (axios)
Client axios créé dans le constructeur (`kalga-api.service.js:11-16`) :
```js
this.client = axios.create({
    baseURL: config.kalgaApiUrl,                 // http://localhost:8001 (config/index.js:14)
    timeout: config.apiTimeout,                  // 30000ms
    headers: { 'Content-Type': 'application/json' },
});
```
Appel :
```js
const response = await this.client.post('/api/chat/incoming', {
    merchant_phone: merchantPhone,
    client_phone: clientPhone,
    message: truncatedMessage,                   // tronqué à config.maxMessageLength (2000)
    product_code: productCode,
    client_name: clientName || '',
});
```

### Headers actuels
**Aucun `X-Internal-Key`.** Le client axios n'envoie que `Content-Type: application/json`.
C'est le point à corriger pour le verrouillage (voir §3).

### Voie média parallèle
`sendIncomingMedia()` (lignes 84-117) → `POST /api/chat/incoming-media` (multipart FormData, audio/image).
Même absence de header interne — à verrouiller de la même façon si on protège l'ingestion.

---

## 3. État actuel de `/incoming` (NON authentifié) + où ajouter `X-Internal-Key`

### Endpoint API
`kalga-api/app/routers/chat.py:29-42` :
```python
@router.post("/incoming", response_model=BotResponse)
@limiter.limit("30/minute")
async def handle_incoming_message(
    request: Request,
    message: IncomingMessage,
    chat_service: ChatService = Depends(get_chat_service)
):
    return await chat_service.handle_incoming_message(message)
```
- Préfixe routeur : `prefix="/chat"` (`chat.py:21`) + monté avec `prefix="/api"` dans
  `main.py:176` → URL finale **`/api/chat/incoming`**.
- **Seule protection actuelle = rate limit `30/minute` par IP** (SlowAPI). Aucune vérif de clé,
  aucune `Depends` d'auth. N'importe qui atteignant le port 8001 peut injecter des messages.
- `/api/chat/incoming-media` (`chat.py:45-130`) : idem, juste `20/minute`, pas d'auth.

### Brique d'auth déjà disponible côté API
- `settings.internal_api_key` existe (`config.py:39`, default `""`), chargé depuis `INTERNAL_API_KEY` du `.env`.
- `validate_settings()` warn déjà si vide (`config.py:133-137`).
- **Aucune dépendance FastAPI `verify_internal_key` n'existe encore** — il faut la créer.

### Où ajouter le header (côté bridge — émetteur)
Dans `kalga-api.service.js`, injecter `X-Internal-Key` sur les appels sortants. Le plus propre :
ajouter le header au client axios partagé (constructeur, lignes 11-16) à partir d'une var d'env bridge :
```js
// kalga-whatsapp/src/config/index.js — internalApiKey existe déjà (ligne 43)
// kalga-whatsapp/src/services/kalga-api.service.js (constructeur)
this.client = axios.create({
    baseURL: config.kalgaApiUrl,
    timeout: config.apiTimeout,
    headers: {
        'Content-Type': 'application/json',
        ...(config.internalApiKey ? { 'X-Internal-Key': config.internalApiKey } : {}),
    },
});
```
Note : `sendIncomingMedia()` construit ses headers via `form.getHeaders()` (ligne 105) — il faut
y ajouter explicitement `'X-Internal-Key': config.internalApiKey` car il n'utilise pas les
headers par défaut du même chemin (FormData remplace).

### Où vérifier le header (côté API — récepteur)
Créer une dépendance FastAPI réutilisable et l'attacher à `/incoming` (+ `/incoming-media`).
Header lu via `Header(alias="X-Internal-Key")`. Exemple :
```python
# nouveau, ex: kalga-api/app/dependencies.py
from fastapi import Header, HTTPException
from .core.config import settings

async def verify_internal_key(x_internal_key: str | None = Header(default=None, alias="X-Internal-Key")):
    if not settings.internal_api_key:
        return  # dev mode : clé non configurée → on laisse passer (parité avec le bridge)
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Internal-Key")
```
Branchement (`chat.py:29-35`) :
```python
@router.post("/incoming", response_model=BotResponse)
@limiter.limit("30/minute")
async def handle_incoming_message(
    request: Request,
    message: IncomingMessage,
    chat_service: ChatService = Depends(get_chat_service),
    _: None = Depends(verify_internal_key),   # ← AJOUT
):
```
Faire de même sur `handle_incoming_media` (`chat.py:47`).
**Garder le `Request` en 1er param** : requis par SlowAPI (`@limiter.limit`).

### Cohérence dev/prod (parité avec le bridge)
Le bridge skip l'auth si `internalApiKey` vide. Reproduire ce comportement côté API
(`if not settings.internal_api_key: return`) évite de casser le dev où `INTERNAL_API_KEY` n'est pas posé.
En prod : définir `INTERNAL_API_KEY` (même valeur) dans les `.env` des **deux** services :
- `kalga-whatsapp/.env` → `INTERNAL_API_KEY=...`
- `kalga-api/.env` → `INTERNAL_API_KEY=...`

---

## 4. Récap fichiers à toucher

| Action | Fichier | Détail |
|---|---|---|
| Envoyer l'OTP | `kalga-api/app/infrastructure/whatsapp/client.py` | `whatsapp_client.send_message(...)` → POST `/send` (injecte déjà `X-Internal-Key`) |
| (alt) OTP inline | `kalga-api/app/services/activation_service.py:92` | pattern `_send_whatsapp_message` déjà prêt |
| Verrou émetteur | `kalga-whatsapp/src/services/kalga-api.service.js:11-16` + `:105` | ajouter `X-Internal-Key` aux 2 appels sortants |
| Verrou récepteur | `kalga-api/app/dependencies.py` (nouveau) + `kalga-api/app/routers/chat.py:29,47` | `verify_internal_key` en `Depends` |
| Clé | `kalga-whatsapp/.env`, `kalga-api/.env` | `INTERNAL_API_KEY=` identique des 2 côtés |

## Pièges
- `/send` est à la RACINE du bridge (`/send`), pas `/api/send`.
- Le bridge renvoie **503** si la session WhatsApp émettrice n'est pas `ready` — l'OTP échoue silencieusement si le marchand n'a pas scanné le QR.
- Express lit le header en lowercase `x-internal-key` ; httpx/axios l'envoient en `X-Internal-Key` (insensible à la casse, OK).
- `@limiter.limit` exige `request: Request` comme 1er paramètre — ne pas le retirer en ajoutant la dépendance d'auth.
- `sendIncomingMedia` utilise `form.getHeaders()` : ajouter `X-Internal-Key` explicitement, sinon il manque.
- Mode dev : si `INTERNAL_API_KEY` est vide, ni le bridge ni l'API ne protègent — penser à le poser en prod.
