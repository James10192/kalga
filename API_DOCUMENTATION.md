# KALGA API Documentation

Documentation pour développer l'interface de monitoring client.

**Base URL:** `http://localhost:8001/api`

---

## 1. MARCHANDS (Merchants)

### Créer un marchand
```
POST /api/merchants/
Content-Type: application/json

{
  "name": "Jean Kouassi",
  "phone": "2250544210112",
  "business_name": "Boutique Mode Jean"  // optionnel
}
```

**Réponse:**
```json
{
  "success": true,
  "message": "Marchand Jean Kouassi créé avec succès",
  "merchant": {
    "id": 1,
    "name": "Jean Kouassi",
    "phone": "2250544210112",
    "business_name": "Boutique Mode Jean",
    "created_at": "2025-01-16T10:00:00",
    "is_active": true
  }
}
```

### Lister tous les marchands
```
GET /api/merchants/
```

**Réponse:**
```json
[
  {
    "id": 1,
    "name": "Jean Kouassi",
    "phone": "2250544210112",
    "business_name": "Boutique Mode Jean",
    "created_at": "2025-01-16T10:00:00",
    "is_active": true
  }
]
```

### Récupérer un marchand par téléphone
```
GET /api/merchants/{phone}
```

**Exemple:** `GET /api/merchants/2250544210112`

**Réponse:**
```json
{
  "id": 1,
  "name": "Jean Kouassi",
  "phone": "2250544210112",
  "business_name": "Boutique Mode Jean",
  "created_at": "2025-01-16T10:00:00",
  "is_active": true
}
```

### Lister les produits d'un marchand
```
GET /api/merchants/{merchant_id}/products
```

**Exemple:** `GET /api/merchants/1/products`

**Réponse:**
```json
{
  "merchant_id": 1,
  "products": [
    {
      "id": 1,
      "code": "#K001",
      "name": "Robe Wax",
      "description": "Belle robe en wax",
      "price": 25000,
      "min_price": 20000,
      "is_available": true,
      "created_at": "2025-01-16T10:30:00"
    }
  ],
  "count": 1
}
```

---

## 2. PRODUITS (Products)

### Créer un produit
```
POST /api/products/
Content-Type: application/json

{
  "merchant_id": 1,
  "name": "Robe Wax Ankara",
  "description": "Belle robe en wax pour femme",
  "price": 25000,
  "min_price": 20000
}
```

**Réponse:**
```json
{
  "success": true,
  "message": "Produit créé: Robe Wax Ankara - Code: #K001",
  "product": {
    "id": 1,
    "merchant_id": 1,
    "code": "#K001",
    "name": "Robe Wax Ankara",
    "description": "Belle robe en wax pour femme",
    "price": 25000,
    "min_price": 20000,
    "is_available": true,
    "created_at": "2025-01-16T10:30:00"
  },
  "tip": "Ajoutez #K001 à votre Status WhatsApp"
}
```

### Récupérer un produit par code
```
GET /api/products/{code}
```

**Exemple:** `GET /api/products/%23K001` (URL encoded: # = %23)

**Réponse:**
```json
{
  "id": 1,
  "merchant_id": 1,
  "code": "#K001",
  "name": "Robe Wax Ankara",
  "description": "Belle robe en wax pour femme",
  "price": 25000,
  "min_price": 20000,
  "is_available": true,
  "created_at": "2025-01-16T10:30:00"
}
```

### Désactiver un produit
```
DELETE /api/products/{code}
```

**Exemple:** `DELETE /api/products/%23K001`

**Réponse:**
```json
{
  "success": true,
  "message": "Produit #K001 désactivé"
}
```

---

## 3. CONVERSATIONS & CHAT

### Lister les conversations d'un marchand
```
GET /api/chat/conversations/{merchant_phone}?status=active
```

**Paramètres:**
- `merchant_phone`: Numéro du marchand
- `status`: Filtre par statut (optionnel)
  - `active` - Conversations en cours
  - `completed` - Ventes conclues
  - `abandoned` - Client parti
  - `expired` - Plus de 7 jours

**Exemple:** `GET /api/chat/conversations/2250544210112?status=active`

**Réponse:**
```json
{
  "merchant": "Jean Kouassi",
  "status": "active",
  "conversations": [
    {
      "id": 1,
      "merchant_id": 1,
      "product_id": 1,
      "client_phone": "2250701234567",
      "status": "active",
      "current_offer": 22000,
      "created_at": "2025-01-16T11:00:00",
      "updated_at": "2025-01-16T11:30:00"
    }
  ],
  "count": 1
}
```

### Nettoyer les conversations expirées
```
POST /api/chat/cleanup
```

**Réponse:**
```json
{
  "success": true,
  "message": "Conversations expirées nettoyées"
}
```

---

## 4. WHATSAPP BRIDGE (Port 3001)

**Base URL:** `http://localhost:3001`

### Vérifier le statut de santé
```
GET /health
```

**Réponse:**
```json
{
  "status": "healthy",
  "service": "kalga-whatsapp"
}
```

### Connecter un marchand (générer QR code)
```
POST /connect
Content-Type: application/json

{
  "merchant_phone": "2250544210112"
}
```

**Réponse:**
```json
{
  "success": true,
  "message": "QR code généré. Scannez-le dans WhatsApp"
}
```

### Afficher la page QR code
```
GET /qr/{merchant_phone}
```

**Exemple:** `GET /qr/2250544210112`

Retourne une page HTML avec le QR code à scanner.

### Vérifier le statut de connexion
```
GET /status/{merchant_phone}
```

**Exemple:** `GET /status/2250544210112`

**Réponse:**
```json
{
  "phone": "2250544210112",
  "connected": true,
  "status": "connected"
}
```

### Envoyer un message
```
POST /send
Content-Type: application/json

{
  "merchant_phone": "2250544210112",
  "to": "2250701234567",
  "message": "Bonjour, votre commande est prête!"
}
```

**Réponse:**
```json
{
  "success": true,
  "messageId": "3EB0..."
}
```

---

## 5. MODÈLES DE DONNÉES

### Statuts de conversation
| Statut | Description |
|--------|-------------|
| `active` | Négociation en cours |
| `completed` | Vente conclue, livraison confirmée |
| `pending_delivery` | Prix accepté, en attente livraison |
| `abandoned` | Client n'a plus répondu |
| `expired` | Plus de 7 jours d'inactivité |

### Structure Marchand
```typescript
interface Merchant {
  id: number;
  name: string;
  phone: string;
  business_name?: string;
  created_at: string;  // ISO datetime
  is_active: boolean;
}
```

### Structure Produit
```typescript
interface Product {
  id: number;
  merchant_id: number;
  code: string;        // #K001, #K002, etc.
  name: string;
  description?: string;
  price: number;       // Prix affiché
  min_price: number;   // Prix minimum négociable
  is_available: boolean;
  created_at: string;
}
```

### Structure Conversation
```typescript
interface Conversation {
  id: number;
  merchant_id: number;
  product_id: number;
  client_phone: string;
  status: "active" | "completed" | "pending_delivery" | "abandoned" | "expired";
  current_offer?: number;  // Dernière offre du client
  created_at: string;
  updated_at: string;
}
```

---

## 6. EXEMPLES D'UTILISATION (JavaScript/Fetch)

### Créer un marchand
```javascript
const response = await fetch('http://localhost:8001/api/merchants/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: "Jean Kouassi",
    phone: "2250544210112",
    business_name: "Boutique Mode"
  })
});
const data = await response.json();
console.log(data.merchant.id);
```

### Lister les conversations actives
```javascript
const merchantPhone = "2250544210112";
const response = await fetch(
  `http://localhost:8001/api/chat/conversations/${merchantPhone}?status=active`
);
const data = await response.json();
console.log(`${data.count} conversations actives`);
```

### Vérifier connexion WhatsApp
```javascript
const merchantPhone = "2250544210112";
const response = await fetch(`http://localhost:3001/status/${merchantPhone}`);
const data = await response.json();
if (data.connected) {
  console.log("WhatsApp connecté!");
} else {
  console.log("Besoin de scanner le QR code");
}
```

---

## 7. CODES D'ERREUR

| Code | Description |
|------|-------------|
| 200 | Succès |
| 400 | Requête invalide (données manquantes/incorrectes) |
| 404 | Ressource non trouvée |
| 500 | Erreur serveur |

### Exemple d'erreur
```json
{
  "detail": "Ce numéro WhatsApp est déjà enregistré"
}
```

---

## 8. NOTES POUR LE DÉVELOPPEMENT

1. **CORS activé** - L'API accepte les requêtes de n'importe quelle origine
2. **Format téléphone** - Utiliser le format international sans le + (ex: 2250544210112)
3. **Codes produits** - Le # doit être URL encoded (%23) dans les URLs
4. **Dates** - Format ISO 8601 (ex: 2025-01-16T10:30:00)

---

## 9. DÉMARRER LES SERVICES

### API (Port 8001)
```bash
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-api"
uvicorn app.main:app --port 8001 --reload
```

### WhatsApp Bridge (Port 3001)
```bash
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-whatsapp"
npm start
```

### Tester l'API
- Swagger UI: http://localhost:8001/docs
- Health check: http://localhost:8001/health
