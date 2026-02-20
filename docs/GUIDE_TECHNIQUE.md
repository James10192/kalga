# GUIDE TECHNIQUE - KALGA

## 1. Vue d'ensemble

### 1.1 Description

KALGA est un système d'automatisation de commerce via WhatsApp qui permet aux marchands de vendre leurs produits via les Status WhatsApp avec un chatbot intelligent pour la négociation.

### 1.2 Technologies utilisées

| Composant | Technologie | Version |
|-----------|-------------|---------|
| API Backend | Python + FastAPI | 3.10+ / 0.115+ |
| Base de données | SQLite | 3.x |
| Bridge WhatsApp | Node.js + Express | 18+ |
| Librairie WhatsApp | whatsapp-web.js | 1.x |
| IA Conversation | DeepSeek API | - |
| ORM/Validation | Pydantic | 2.x |
| HTTP Client | httpx (Python) / axios (Node) | - |

### 1.3 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT WHATSAPP                          │
│                    (Téléphone du marchand)                       │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 │ WebSocket (WhatsApp Web Protocol)
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                    WHATSAPP BRIDGE (Node.js)                     │
│                         Port: 3001                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  • Gestion des sessions WhatsApp (LocalAuth)                │ │
│  │  • Réception des messages (event: message_create)           │ │
│  │  • Détection commandes marchand vs messages clients         │ │
│  │  • Envoi des réponses                                       │ │
│  │  • API REST pour connexion/status                           │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 │ HTTP REST (axios)
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                      KALGA API (FastAPI)                         │
│                         Port: 8001                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Routers:                                                   │ │
│  │  • /api/merchants     - Gestion des marchands               │ │
│  │  • /api/products      - Gestion des produits                │ │
│  │  • /api/chat          - Conversations clients               │ │
│  │  • /api/merchant      - Commandes marchand WhatsApp         │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Services:                                                  │ │
│  │  • conversation_ai.py - Génération réponses IA              │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
┌─────────────────────────────┐  ┌─────────────────────────────┐
│      SQLite Database        │  │      DeepSeek API           │
│      (kalga.db)             │  │  (IA conversationnelle)     │
│  • merchants                │  │                             │
│  • products                 │  │  POST /chat/completions     │
│  • conversations            │  │                             │
│  • messages                 │  │                             │
└─────────────────────────────┘  └─────────────────────────────┘
```

---

## 2. API Endpoints

### 2.1 Marchands (`/api/merchants`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/merchants/` | Créer un marchand |
| GET | `/api/merchants/` | Lister tous les marchands |
| GET | `/api/merchants/{phone}` | Obtenir un marchand par téléphone |
| GET | `/api/merchants/{id}/products` | Produits d'un marchand |

**Exemple - Créer un marchand :**
```bash
curl -X POST http://localhost:8001/api/merchants/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jean Dupont",
    "phone": "2250123456789",
    "business_name": "Boutique Jean"
  }'
```

**Réponse :**
```json
{
  "id": 1,
  "name": "Jean Dupont",
  "phone": "2250123456789",
  "business_name": "Boutique Jean",
  "created_at": "2024-01-15T10:30:00",
  "is_active": true
}
```

### 2.2 Produits (`/api/products`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/products/` | Créer un produit |
| GET | `/api/products/{code}` | Obtenir un produit par code |
| DELETE | `/api/products/{code}` | Désactiver un produit |

**Exemple - Créer un produit :**
```bash
curl -X POST http://localhost:8001/api/products/ \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": 1,
    "name": "Robe Wax",
    "description": "Belle robe africaine",
    "price": 20000,
    "min_price": 15000
  }'
```

**Réponse :**
```json
{
  "success": true,
  "message": "Produit créé: Robe Wax - Code: #K001",
  "product": {
    "id": 1,
    "code": "#K001",
    "name": "Robe Wax",
    "price": 20000,
    "min_price": 15000
  },
  "tip": "Ajoutez #K001 à votre Status WhatsApp"
}
```

### 2.3 Chat (`/api/chat`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/chat/incoming` | Traiter un message entrant |
| GET | `/api/chat/conversations/{phone}` | Conversations d'un marchand |
| POST | `/api/chat/cleanup` | Nettoyer conversations expirées |

**Exemple - Message entrant :**
```bash
curl -X POST http://localhost:8001/api/chat/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_phone": "2250123456789",
    "client_phone": "2250987654321",
    "message": "C est dispo ?",
    "product_code": "#K001"
  }'
```

**Réponse :**
```json
{
  "message": "Salut! Oui c'est disponible. C'est 20,000 F. Ça te dit?",
  "conversation_id": 5,
  "should_notify_merchant": false,
  "notification_reason": null
}
```

### 2.4 Commandes Marchand (`/api/merchant`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/merchant/command` | Traiter une commande marchand |

**Exemple - Commande marchand :**
```bash
curl -X POST http://localhost:8001/api/merchant/command \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_phone": "2250123456789",
    "message": "produit"
  }'
```

**Réponse :**
```json
{
  "response": "📦 *Création d'un nouveau produit*\n\nÉtape 1/4: Quel est le *nom* du produit?",
  "action": "product_create_start"
}
```

### 2.5 WhatsApp Bridge (`localhost:3001`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/status` | Statut global du bridge |
| POST | `/connect` | Connecter un marchand |
| GET | `/qr/{phone}` | Page QR code |
| GET | `/status/{phone}` | Statut d'un marchand |
| POST | `/send` | Envoyer un message |

---

## 3. Base de données

### 3.1 Schéma

```sql
-- Table des marchands
CREATE TABLE merchants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT UNIQUE NOT NULL,
    business_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Table des produits
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    merchant_id INTEGER NOT NULL,
    code TEXT UNIQUE NOT NULL,      -- #K001, #K002, etc.
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,            -- Prix affiché
    min_price REAL NOT NULL,        -- Prix minimum négociable
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_available BOOLEAN DEFAULT 1,
    FOREIGN KEY (merchant_id) REFERENCES merchants(id)
);

-- Table des conversations
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    merchant_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    client_phone TEXT NOT NULL,
    status TEXT DEFAULT 'active',   -- active, negotiating, agreed, pending_delivery, completed, ended
    current_offer REAL,             -- Dernière offre du client
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (merchant_id) REFERENCES merchants(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Table des messages
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    is_from_client BOOLEAN NOT NULL,  -- true = client, false = bot
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

### 3.2 États des conversations

| État | Description |
|------|-------------|
| `active` | Conversation démarrée |
| `negotiating` | Négociation en cours |
| `agreed` | Prix accepté, en attente livraison |
| `pending_delivery` | Client a confirmé la livraison |
| `completed` | Vente terminée |
| `ended` | Négociation échouée |
| `expired` | Conversation expirée (7+ jours) |

---

## 4. Flux de données

### 4.1 Flux - Client répond à un Status

```
1. Client répond au Status WhatsApp
         │
         ▼
2. WhatsApp envoie le message au téléphone du marchand
         │
         ▼
3. whatsapp-web.js capture le message (event: message_create)
         │
         ▼
4. Bridge détecte que c'est un message client (pas fromMe)
         │
         ▼
5. Bridge extrait le code produit (#K001) du message cité
         │
         ▼
6. Bridge envoie POST /api/chat/incoming
         │
         ▼
7. API trouve/crée la conversation
         │
         ▼
8. API appelle DeepSeek pour générer la réponse
         │
         ▼
9. API retourne la réponse au Bridge
         │
         ▼
10. Bridge envoie la réponse au client via WhatsApp
```

### 4.2 Flux - Marchand crée un produit

```
1. Marchand écrit "produit" dans sa propre conversation
         │
         ▼
2. whatsapp-web.js capture le message
         │
         ▼
3. Bridge détecte que c'est le marchand (senderPhone == merchantPhone)
         │
         ▼
4. Bridge envoie POST /api/merchant/command
         │
         ▼
5. API vérifie s'il y a une session de création en cours
         │
         ▼
6. API retourne l'étape suivante ou crée le produit
         │
         ▼
7. Bridge envoie la réponse au marchand
```

---

## 5. IA - Génération des réponses

### 5.1 API utilisée

**DeepSeek Chat Completions API**

```
URL: https://api.deepseek.com/v1/chat/completions
Méthode: POST
Headers:
  - Authorization: Bearer {API_KEY}
  - Content-Type: application/json
```

### 5.2 Structure du prompt

```python
system_prompt = """
Tu es un vendeur sympathique sur WhatsApp.

PRODUIT EN VENTE:
- Nom: {product_name}
- Prix affiché: {price} FCFA
- Prix minimum acceptable: {min_price} FCFA (NE JAMAIS révéler!)

RÈGLES DE NÉGOCIATION:
1. Prix >= min_price → Accepter
2. Prix entre min et max → Négocier
3. Prix < min_price → Refuser poliment

STYLE: Familier, amical, 2-3 phrases max
"""

user_prompt = "Le client dit: '{message}'"
```

### 5.3 Logique de négociation

```python
# Compteur d'offres trop basses
low_offers_count = count_low_offers(history, min_price)

# Après 2 offres trop basses → Donner le dernier prix
if low_offers_count >= 2:
    final_price_mode = True

# Après 3 offres trop basses → Terminer la négociation
if low_offers_count >= 3 and offer < min_price:
    end_negotiation = True
```

### 5.4 Fallback (si API échoue)

Si l'API DeepSeek ne répond pas, des réponses prédéfinies sont utilisées :

```python
if price_offer >= min_price:
    return "OK {price} F c'est bon! Tu veux qu'on te livre?"
elif price_offer >= min_price * 0.8:
    counter = (price_offer + min_price) / 2
    return "Ah {price} F c'est trop bas! Fais {counter} F."
else:
    return "Ah non {price} F c'est pas possible!"
```

---

## 6. Sécurité

### 6.1 Points sensibles

| Élément | Emplacement | Risque |
|---------|-------------|--------|
| Clé API DeepSeek | `.env` | Fuite = coûts non autorisés |
| Sessions WhatsApp | `sessions/` | Fuite = accès au compte |
| Base de données | `kalga.db` | Fuite = données clients |

### 6.2 Bonnes pratiques

- Ne jamais commiter les fichiers `.env`
- Ajouter au `.gitignore` :
  ```
  .env
  *.db
  sessions/
  ```
- Utiliser des variables d'environnement en production
- Sauvegarder régulièrement la base de données

---

## 7. Déploiement Production

### 7.1 Recommandations

| Aspect | Développement | Production |
|--------|---------------|------------|
| Base de données | SQLite | PostgreSQL |
| Serveur API | uvicorn --reload | gunicorn + uvicorn workers |
| Serveur Bridge | node server.js | PM2 |
| Reverse proxy | - | Nginx |
| SSL | - | Let's Encrypt |

### 7.2 Exemple PM2 (Node.js)

```bash
# Installer PM2
npm install -g pm2

# Démarrer le bridge
pm2 start server.js --name kalga-bridge

# Voir les logs
pm2 logs kalga-bridge

# Redémarrer
pm2 restart kalga-bridge
```

### 7.3 Exemple systemd (API)

```ini
# /etc/systemd/system/kalga-api.service
[Unit]
Description=KALGA API
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/kalga/kalga-api
ExecStart=/usr/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 8. Évolutions possibles

- [ ] Interface web d'administration
- [ ] Support multi-langues
- [ ] Statistiques de vente
- [ ] Gestion des stocks
- [ ] Paiement intégré (Mobile Money)
- [ ] Support images dans les réponses
- [ ] Catégories de produits
- [ ] Promotions automatiques

---

## 9. Ressources

- **FastAPI** : https://fastapi.tiangolo.com
- **whatsapp-web.js** : https://wwebjs.dev
- **DeepSeek API** : https://platform.deepseek.com/docs
- **SQLite** : https://sqlite.org/docs.html
- **Pydantic** : https://docs.pydantic.dev

---

*Document technique KALGA v1.0*
