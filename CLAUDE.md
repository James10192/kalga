# CLAUDE.md - KALGA Project

## Project Overview

KALGA is a WhatsApp commerce automation system for merchants. It allows merchants to:
- Post products via WhatsApp Status
- Have AI automatically engage clients who respond to statuses
- Handle price negotiation within defined limits
- Track conversations and sales
- Automatically send store location to clients

## Architecture (v2.0)

```
KALGA/
├── kalga-api/                         # FastAPI Backend (Python) - Port 8001
│   └── app/
│       ├── main.py                    # Point d'entrée FastAPI
│       │
│       ├── core/                      # Configuration centrale
│       │   ├── config.py              # Settings Pydantic centralisés
│       │   ├── exceptions.py          # Exceptions personnalisées
│       │   └── events.py              # Lifecycle events (startup/shutdown)
│       │
│       ├── modules/                   # Organisation par DOMAINE
│       │   └── merchant_commands/     # Module commandes marchand
│       │       ├── router.py          # Route unique /command
│       │       ├── service.py         # Orchestration des commandes
│       │       ├── session_manager.py # Gestion sessions en mémoire
│       │       ├── schemas.py         # Pydantic models
│       │       └── handlers/          # Un handler par flux
│       │           ├── base.py        # Classe abstraite + PriceExtractor
│       │           ├── product_creation.py
│       │           ├── variant_creation.py
│       │           ├── sales_management.py
│       │           └── help_commands.py
│       │
│       ├── infrastructure/            # Couche technique
│       │   ├── logging/               # Configuration logs structurés
│       │   └── whatsapp/              # Client HTTP pour le bridge
│       │       └── client.py
│       │
│       ├── database/
│       │   ├── connection.py          # Gestionnaire de connexion SQLite
│       │   ├── db.py                  # Couche de compatibilité
│       │   └── repositories/          # Pattern Repository
│       │       ├── base.py
│       │       ├── merchant_repo.py
│       │       ├── product_repo.py
│       │       └── conversation_repo.py
│       │
│       ├── services/
│       │   ├── chat_service.py        # Orchestration du flux de chat
│       │   ├── notification_service.py # Envoi WhatsApp centralisé
│       │   └── ai/                    # Module IA
│       │       ├── detectors.py
│       │       ├── deepseek_client.py
│       │       ├── fallback_responses.py
│       │       └── conversation_ai.py
│       │
│       ├── models/
│       │   ├── schemas.py             # Schemas Pydantic
│       │   └── enums.py               # ConversationStatus, etc.
│       │
│       └── routers/
│           ├── chat.py
│           ├── merchants.py
│           └── products.py
│
├── kalga-whatsapp/                    # WhatsApp Bridge (Node.js) - Port 3001
│   ├── src/                           # Architecture modulaire v2.0
│   │   ├── index.js                   # Point d'entrée
│   │   ├── config/                    # Configuration centralisée
│   │   │   └── index.js
│   │   ├── api/
│   │   │   └── routes/                # Routes Express séparées
│   │   │       ├── index.js
│   │   │       ├── connect.routes.js
│   │   │       ├── send.routes.js
│   │   │       └── status.routes.js
│   │   ├── services/                  # Logique métier
│   │   │   ├── whatsapp.service.js    # Gestion clients Baileys
│   │   │   ├── message.service.js     # Traitement messages
│   │   │   ├── kalga-api.service.js   # Client API KALGA
│   │   │   └── media.service.js       # Gestion images
│   │   ├── utils/
│   │   │   ├── logger.js              # Logging structuré
│   │   │   ├── jid.js                 # Manipulation JID WhatsApp
│   │   │   └── humanBehavior.js       # Simulation anti-ban
│   │   └── loaders/                   # Initialisation
│   │       ├── index.js
│   │       └── express.js
│   ├── server.js                      # (Legacy - toujours supporté)
│   └── sessions/                      # Sessions WhatsApp par marchand
│
└── dashboard/                         # Web Interface (HTML/CSS/JS)
    ├── index.html
    └── static/
        ├── app.js
        └── style.css
```

## Common Commands

### API (kalga-api)
```bash
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-api"
pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload
```

### WhatsApp Bridge (kalga-whatsapp)
```bash
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-whatsapp"
npm install
npm start              # Nouvelle architecture (src/index.js)
npm run start:legacy   # Ancienne architecture (server.js)
```

### Dashboard
Open `dashboard/index.html` in a browser

## API Endpoints

### Merchants
- `POST /api/merchants/` - Create merchant
- `GET /api/merchants/` - List all merchants
- `GET /api/merchants/{phone}` - Get merchant by phone
- `GET /api/merchants/{id}/products` - Get merchant's products
- `PUT /api/merchants/{id}/location` - Update merchant location

### Products
- `POST /api/products/` - Create product (returns code like #K001)
- `GET /api/products/{code}` - Get product by code

### Chat
- `POST /api/chat/incoming` - Handle incoming WhatsApp message
- `GET /api/chat/conversations/{merchant_phone}` - Get merchant's conversations
- `POST /api/chat/cleanup` - Clean expired conversations (7+ days)

### Merchant Commands
- `POST /api/merchant/command` - Handle merchant WhatsApp commands

### WhatsApp Bridge
- `POST /connect` - Connect merchant's WhatsApp
- `GET /qr/{merchant_phone}` - Get QR code page
- `GET /status/{merchant_phone}` - Get connection status
- `GET /status` - Get all merchants status
- `GET /health` - Health check
- `POST /send` - Send text message
- `POST /send-image` - Send image
- `POST /send-location` - Send GPS location

## Key Features

### Product Code System
- Products get unique codes: #K001, #K002, etc.
- Merchants add code to WhatsApp Status
- Bot detects code in client messages via regex: `#K\d{3}`

### AI Conversation
- Uses DeepSeek API with intelligent fallback
- Natural conversation style
- Price negotiation within limits
- Never reveals minimum price
- Structured in modules: detectors, client, fallback

### Merchant Location
- Location captured at first connection (mandatory)
- Supports GPS coordinates + text address
- Automatically sent to clients when they ask for the store address

### Merchant Commands (via WhatsApp)
- `produit` - Start product creation wizard
- `variante #K001` - Add variant to existing product
- `mes produits` - List products
- `supprimer #K001` - Delete a product
- `!ok` or `!livré` - Mark sale as completed
- `!annuler` - Cancel a pending sale
- `aide` - Show available commands

### Conversation Flow
1. Client responds to merchant's Status containing #K001
2. WhatsApp Bridge receives message
3. Bridge sends to KALGA API `/api/chat/incoming`
4. ChatService orchestrates: merchant → product → conversation → AI
5. AI generates response (DeepSeek or fallback)
6. Response sent back via WhatsApp
7. If client asks for location → auto-send GPS coordinates

### Conversation Status Flow
```
active → negotiating → agreed → pending_delivery/pending_pickup → completed
                              ↓
                           abandoned/ended/expired
```

### Database
- SQLite (kalga-api/app/database/kalga.db)
- Tables: merchants, products, conversations, messages
- Auto-generated on first run
- Repository pattern for data access

## Environment Variables

### kalga-api/.env
```
DEBUG=true
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
WHATSAPP_BRIDGE_URL=http://localhost:3001
CONVERSATION_EXPIRY_DAYS=7
```

### kalga-whatsapp/.env
```
NODE_ENV=development
PORT=3001
KALGA_API_URL=http://localhost:8001
DEBUG=true
```

## Testing Flow

1. Start API: `uvicorn app.main:app --port 8001`
2. Start WhatsApp Bridge: `npm start` (in kalga-whatsapp)
3. Open dashboard: `dashboard/index.html`
4. Enter merchant phone number
5. Scan QR code with WhatsApp
6. **Enter store location** (mandatory at first connection)
7. Create a product (get code #K001)
8. Post Status with #K001
9. Have someone reply to the Status
10. Bot should respond automatically

## Code Patterns

### Using the New Module Architecture (recommended)
```python
# Merchant commands with handlers
from app.modules.merchant_commands import MerchantCommandService

service = MerchantCommandService()
response = await service.process_command(msg)
```

### Using Session Manager
```python
from app.modules.merchant_commands.session_manager import session_manager

# Create session
session = session_manager.create(
    merchant_phone="225XXXXXXXX",
    step="name",
    data={"merchant_id": 1}
)

# Get session with lock (prevents race conditions)
lock = await session_manager.get_lock(merchant_phone)
async with lock:
    session = session_manager.get(merchant_phone)
    if session:
        session.update_step("price")
```

### Using Repositories (recommended for new code)
```python
from app.database.repositories import MerchantRepository

merchant_repo = MerchantRepository()
merchant = await merchant_repo.get_by_phone("225XXXXXXXX")
```

### Using Legacy Database (still supported)
```python
from app.database import get_db

db = await get_db()
merchant = await db.get_merchant_by_phone("225XXXXXXXX")
```

### Using Services with Dependency Injection
```python
from fastapi import Depends
from app.services.chat_service import ChatService, get_chat_service

@router.post("/incoming")
async def handle_message(
    message: IncomingMessage,
    chat_service: ChatService = Depends(get_chat_service)
):
    return await chat_service.handle_incoming_message(message)
```

### Using Custom Exceptions
```python
from app.core.exceptions import (
    MerchantNotFoundError,
    ProductNotFoundError,
    ValidationError
)

if not merchant:
    raise MerchantNotFoundError(phone)
```

### Node.js Service Pattern
```javascript
// Using services in Node.js
const { whatsappService } = require('./services/whatsapp.service');
const { messageService } = require('./services/message.service');

// Send message
await whatsappService.sendMessage(merchantPhone, clientJid, "Hello!");

// Process client message
await messageService.handleClientMessage(merchantPhone, sock, message);
```

## Important Notes

- Each merchant = separate WhatsApp session
- Sessions stored in `kalga-whatsapp/sessions/`
- Conversations expire after 7 days
- DeepSeek API key shared with WOURI project
- Location is mandatory for new merchants
- Fallback responses if DeepSeek API fails
- **New architecture uses modular design with handlers**
- **Session manager includes race condition protection with asyncio locks**
- **Legacy server.js still available via `npm run start:legacy`**
