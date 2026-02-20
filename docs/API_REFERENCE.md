# KALGA API - Documentation Complète

**Base URLs:**
- KALGA API: `http://localhost:8001`
- WhatsApp Bridge: `http://localhost:3001`

**Authentication:**
JWT Bearer tokens. Header: `Authorization: Bearer <access_token>`

---

## 1. AUTH (`/api/auth`)

### POST `/api/auth/register`
Inscription d'un nouveau marchand. Crée user + merchant + trial.
**Auth:** Non

**Request:**
```json
{
  "email": "merchant@example.com",
  "password": "securepass",
  "name": "Jean Kouame",
  "phone": "2250700000000",
  "business_name": "Boutique JK"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "merchant@example.com",
    "role": "merchant",
    "merchant_id": 1,
    "is_verified": false
  },
  "merchant": {
    "id": 1,
    "name": "Jean Kouame",
    "phone": "2250700000000",
    "business_name": "Boutique JK",
    "created_at": "2026-02-20T10:00:00"
  },
  "message": "Inscription réussie!"
}
```

**Erreurs:** `400` - Email ou phone déjà utilisé

---

### POST `/api/auth/login`
Connexion admin ou marchand.
**Auth:** Non

**Request:**
```json
{
  "email": "merchant@example.com",
  "password": "securepass"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "merchant@example.com",
    "role": "merchant",
    "merchant_id": 1,
    "is_verified": true
  }
}
```

**Erreurs:** `401` - Email ou mot de passe incorrect

---

### POST `/api/auth/refresh`
Rafraîchir le token d'accès.
**Auth:** Non

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

---

### POST `/api/auth/logout`
Déconnexion.
**Auth:** Oui

**Response (200):**
```json
{
  "message": "Déconnexion réussie"
}
```

---

### GET `/api/auth/me`
Info utilisateur connecté + merchant + subscription.
**Auth:** Oui

**Response (200):**
```json
{
  "id": 1,
  "email": "merchant@example.com",
  "role": "merchant",
  "merchant_id": 1,
  "is_active": true,
  "is_verified": true,
  "last_login": "2026-02-20T10:00:00",
  "merchant": { },
  "subscription": { }
}
```

---

### POST `/api/auth/change-password`
Changer mot de passe.
**Auth:** Oui

**Request:**
```json
{
  "current_password": "oldpass",
  "new_password": "newpass123"
}
```

---

### POST `/api/auth/forgot-password`
Demande de reset mot de passe.
**Auth:** Non

**Request:**
```json
{
  "email": "merchant@example.com"
}
```

**Response (200):**
```json
{
  "message": "Si cet email existe, un lien de réinitialisation a été envoyé.",
  "debug_token": "abc123..."
}
```

---

### POST `/api/auth/reset-password`
Reset mot de passe avec token.
**Auth:** Non

**Request:**
```json
{
  "token": "abc123...",
  "new_password": "newpass123"
}
```

---

### GET `/api/auth/verify-email/{token}`
Vérifier l'email.
**Auth:** Non

---

## 2. MERCHANTS (`/api/merchants`)

### POST `/api/merchants/`
Créer un marchand.
**Auth:** Non

**Request:**
```json
{
  "name": "Jean Kouame",
  "phone": "2250700000000",
  "business_name": "Boutique JK"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Marchand créé avec succès",
  "merchant": {
    "id": 1,
    "name": "Jean Kouame",
    "phone": "2250700000000",
    "business_name": "Boutique JK",
    "created_at": "2026-02-20T10:00:00"
  }
}
```

---

### GET `/api/merchants/`
Lister les marchands avec pagination.
**Auth:** Non

**Query:** `page` (int, defaut 1), `limit` (int, defaut 20)

**Response (200):**
```json
{
  "merchants": [],
  "page": 1,
  "limit": 20,
  "total": 5,
  "pages": 1
}
```

---

### GET `/api/merchants/{phone}`
Obtenir un marchand par téléphone.
**Auth:** Non

**Response (200):**
```json
{
  "id": 1,
  "name": "Jean Kouame",
  "phone": "2250700000000",
  "business_name": "Boutique JK",
  "address": "Cocody, Abidjan",
  "latitude": 5.3364,
  "longitude": -4.0266,
  "about": "...",
  "tagline": "...",
  "logo_path": "logo_1_abc123.jpg",
  "banner_path": null,
  "created_at": "2026-02-20T10:00:00",
  "is_active": true
}
```

---

### GET `/api/merchants/{merchant_id}/products`
Produits d'un marchand avec pagination.
**Auth:** Non

**Query:** `page`, `limit`

**Response (200):**
```json
{
  "merchant_id": 1,
  "products": [],
  "page": 1,
  "limit": 20,
  "total": 3,
  "pages": 1
}
```

---

### PUT `/api/merchants/{merchant_id}`
Mettre à jour un marchand.
**Auth:** Non

**Request (tous optionnels):**
```json
{
  "name": "New Name",
  "business_name": "New Business",
  "address": "Plateau, Abidjan",
  "latitude": 5.32,
  "longitude": -4.01,
  "about": "Description",
  "tagline": "Slogan"
}
```

---

### PUT `/api/merchants/{merchant_id}/location`
Mettre à jour la localisation GPS.
**Auth:** Non

**Request (tous optionnels):**
```json
{
  "address": "Cocody, Abidjan",
  "latitude": 5.3364,
  "longitude": -4.0266
}
```

---

### PUT `/api/merchants/{merchant_id}/phone`
Corriger le numéro de téléphone.
**Auth:** Non

**Request:**
```json
{
  "phone": "2250700000001"
}
```

---

### POST `/api/merchants/{merchant_id}/upload-image`
Upload logo ou bannière. **Multipart form-data.**
**Auth:** Non

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `image_type` | string | Oui | `"logo"` ou `"banner"` |
| `file` | file | Oui | Image (JPG, PNG, WebP, GIF, max 5 MB) |

**Response (200):**
```json
{
  "success": true,
  "message": "Logo mis à jour",
  "url": "/uploads/logo_1_abc123.jpg"
}
```

---

## 3. PRODUCTS (`/api/products`)

### POST `/api/products/`
Créer un produit. Retourne un code unique (#K001, #K002...).
**Auth:** Non

**Request:**
```json
{
  "merchant_id": 1,
  "name": "iPhone 14 Pro",
  "description": "128GB Space Black",
  "price": 650000,
  "min_price": 600000,
  "image_path": "products/img.jpg",
  "group_id": "IPHONE14",
  "variant_name": "Space Black"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Produit créé: iPhone 14 Pro - Code: #K001",
  "product": {
    "id": 1,
    "code": "#K001",
    "merchant_id": 1,
    "name": "iPhone 14 Pro",
    "price": 650000,
    "min_price": 600000,
    "description": "128GB Space Black",
    "image_path": "products/img.jpg",
    "is_available": true,
    "created_at": "2026-02-20T10:00:00"
  },
  "tip": "Ajoutez #K001 à votre Status WhatsApp"
}
```

---

### GET `/api/products/{code}`
Obtenir un produit par code (`#K001` ou `K001`).
**Auth:** Non

---

### GET `/api/products/{code}/variants`
Obtenir les variantes d'un produit.
**Auth:** Non

**Response (200):**
```json
{
  "product": {},
  "variants": [],
  "count": 2
}
```

---

### DELETE `/api/products/{identifier}`
Désactiver un produit (soft delete). Accepte code ou ID numérique.
**Auth:** Non

---

### GET `/api/products/{code}/stock`
Statut du stock.
**Auth:** Non

**Response (200):**
```json
{
  "product_code": "#K001",
  "product_name": "iPhone 14 Pro",
  "quantity": 10,
  "is_low": false,
  "is_out_of_stock": false,
  "is_unlimited": false
}
```

---

### PUT `/api/products/{code}/stock`
Mettre à jour le stock.
**Auth:** Non

**Request:**
```json
{
  "quantity": 10,
  "low_stock_threshold": 3
}
```

---

### GET `/api/products/merchant/{merchant_id}/low-stock`
Produits en stock bas et en rupture.
**Auth:** Non

**Response (200):**
```json
{
  "merchant_id": 1,
  "low_stock": [],
  "out_of_stock": [],
  "low_stock_count": 2,
  "out_of_stock_count": 1
}
```

---

## 4. CHAT (`/api/chat`)

### POST `/api/chat/incoming`
Message entrant d'un client. Rate limit: 30/min par IP.
**Auth:** Non

**Request:**
```json
{
  "merchant_phone": "2250700000000",
  "client_phone": "2250700000001",
  "message": "Bonjour, c'est combien?",
  "product_code": "#K001",
  "client_name": "Aya"
}
```

**Response (200):**
```json
{
  "message": "Bonjour! L'iPhone 14 Pro est à 650,000 F...",
  "conversation_id": 42,
  "should_notify_merchant": false,
  "notification_reason": null,
  "no_response": false,
  "images_to_send": null,
  "away_mode": false
}
```

---

### GET `/api/chat/conversations/{merchant_phone}`
Conversations d'un marchand.
**Auth:** Non

**Query:** `status` (defaut "active"), `page`, `limit`

---

### GET `/api/chat/conversations/{conv_id}/messages`
Messages d'une conversation.
**Auth:** Non

---

### POST `/api/chat/conversations/{conv_id}/accept`
Accepter l'offre du client.
**Auth:** Non

---

### POST `/api/chat/conversations/{conv_id}/reject`
Rejeter l'offre du client.
**Auth:** Non

---

### POST `/api/chat/cleanup`
Nettoyer les conversations expirées (7+ jours).
**Auth:** Non

---

## 5. MERCHANT COMMANDS (`/api/merchant`)

### POST `/api/merchant/command`
Commande WhatsApp du marchand (wizard stateful).
**Auth:** Non

**Request:**
```json
{
  "merchant_phone": "2250700000000",
  "message": "produit",
  "image_path": "/path/to/image.jpg"
}
```

**Commandes:** `produit`, `modifier #K001`, `variante #K001`, `mes produits`, `supprimer #K001`, `!ok`, `!livré`, `!annuler`, `aide`, `annuler`

**Response (200):**
```json
{
  "response": "Quel est le nom du produit?",
  "action": "product_create_start",
  "product_code": null
}
```

**Actions possibles:** `product_create_start`, `product_step`, `product_created`, `product_complete`, `variant_create_start`, `variant_step`, `variant_created`, `variant_continue`, `variants_complete`, `product_edit_start`, `product_edit_step`, `product_edited`, `sale_completed`, `sale_cancelled`, `list`, `list_empty`, `delete`, `help`, `error`, `cancelled`, `ignored`, `ask_again`, `unknown`, `no_pending`

---

## 6. CATEGORIES (`/api/categories`)

### GET `/api/categories/{merchant_phone}`
Catégories d'un marchand.

### POST `/api/categories/{merchant_phone}`
Créer une catégorie.

**Request:**
```json
{
  "name": "Vêtements",
  "icon": "👕",
  "color": "#667eea"
}
```

### PUT `/api/categories/{category_id}`
Modifier une catégorie.

### DELETE `/api/categories/{category_id}`
Supprimer une catégorie.

### GET `/api/categories/options/icons`
Icônes disponibles.

### GET `/api/categories/options/colors`
Couleurs disponibles.

---

## 7. STATISTICS (`/api/stats`)

### GET `/api/stats/{merchant_phone}/summary`
Résumé sur une période.
**Query:** `days` (defaut 30)

**Response (200):**
```json
{
  "total_conversations": 50,
  "total_messages": 320,
  "total_sales": 12,
  "total_revenue": 3500000,
  "conversion_rate": 0.24,
  "average_sale": 291666
}
```

### GET `/api/stats/{merchant_phone}/daily`
Stats journalières pour graphiques.
**Query:** `start_date`, `end_date`, `days` (defaut 7)

**Response (200):**
```json
{
  "data": [
    {
      "date": "2026-02-13",
      "conversations_count": 3,
      "messages_count": 20,
      "sales_count": 1,
      "revenue": 150000,
      "unique_clients": 3
    }
  ]
}
```

### GET `/api/stats/{merchant_phone}/top-products`
Produits les plus populaires.
**Query:** `limit` (defaut 5)

### GET `/api/stats/{merchant_phone}/hourly-activity`
Activité par heure.
**Query:** `days` (defaut 7)

### GET `/api/stats/{merchant_phone}/realtime`
Stats en temps réel (aujourd'hui).

---

## 8. AWAY MODE (`/api/merchants`)

### GET `/api/merchants/{merchant_phone}/away-settings`
Paramètres du mode absence.

### PUT `/api/merchants/{merchant_phone}/away-settings`
Mettre à jour les paramètres.

**Request (tous optionnels):**
```json
{
  "away_mode_enabled": true,
  "working_hours": {
    "enabled": true,
    "timezone": "Africa/Abidjan",
    "schedule": {
      "monday": {"open": "08:00", "close": "18:00", "enabled": true},
      "sunday": {"open": "00:00", "close": "00:00", "enabled": false}
    }
  },
  "away_message": "Fermé pour le moment!"
}
```

### POST `/api/merchants/{merchant_phone}/away-toggle`
Toggle rapide on/off.

**Request:**
```json
{
  "enabled": true,
  "message": "De retour dans 1h!"
}
```

### GET `/api/merchants/{merchant_phone}/availability`
Vérifier la disponibilité.

---

## 9. IMPORT/EXPORT (`/api/import-export`)

### GET `/api/import-export/{merchant_phone}/products/export`
Exporter les produits en CSV.

### POST `/api/import-export/{merchant_phone}/products/import`
Importer des produits depuis CSV. **Multipart form-data.**

**Colonnes CSV:** `name` (requis), `price` (requis), `min_price` (requis), `description`, `stock_quantity`, `low_stock_threshold`, `group_id`, `variant_name`

### GET `/api/import-export/{merchant_phone}/products/template`
Télécharger le template CSV.

---

## 10. ACTIVATION (`/api/activation`)

### POST `/api/activation/verify`
Vérifier et activer un code.

**Request:**
```json
{
  "code": "KALG7X3F",
  "merchant_phone": "2250700000000"
}
```

### POST `/api/activation/check-subscription`
Vérifier si abonnement actif.

**Request:**
```json
{
  "merchant_phone": "2250700000000"
}
```

### GET `/api/activation/status/{merchant_phone}`
Statut d'activation.

---

## 11. STOREFRONT - Public (`/api/storefront`)

> **IMPORTANT:** Ces endpoints ne renvoient JAMAIS le `min_price`.

### GET `/api/storefront/{phone}`
Info publique de la boutique.

**Response (200):**
```json
{
  "name": "Jean Kouame",
  "business_name": "Boutique JK",
  "phone": "2250700000000",
  "address": "Cocody, Abidjan",
  "logo_url": "/uploads/logo_1_abc123.jpg",
  "banner_url": null,
  "about": "...",
  "tagline": "...",
  "product_count": 12
}
```

### GET `/api/storefront/{phone}/products`
Tous les produits actifs (sans min_price).

**Response (200):**
```json
{
  "merchant": {
    "name": "Jean Kouame",
    "business_name": "Boutique JK",
    "phone": "2250700000000",
    "logo_url": "/uploads/logo_1_abc123.jpg"
  },
  "products": [
    {
      "id": 1,
      "code": "#K001",
      "name": "iPhone 14 Pro",
      "price": 650000,
      "description": "128GB",
      "image_url": "/uploads/products/img.jpg",
      "variant_name": null,
      "group_id": null,
      "in_stock": true
    }
  ]
}
```

### GET `/api/storefront/product/{code}`
Détail produit avec variantes et info marchand.

### POST `/api/storefront/order`
Passer une commande web. Rate limit: 5/min par IP.

**Request:**
```json
{
  "merchant_phone": "2250700000000",
  "product_code": "#K001",
  "client_name": "Aya Koné",
  "client_phone": "2250700000001",
  "message": "Je veux la couleur noire"
}
```

**Response (200):**
```json
{
  "success": true,
  "order_id": 1,
  "message": "Commande envoyée! Le marchand vous contactera bientôt."
}
```

---

## 12. ADMIN (`/api/admin`)

> **Tous les endpoints admin requièrent:** `Authorization: Bearer <token>` avec `role: "admin"`

### GET `/api/admin/dashboard`
Dashboard global admin.

**Response (200):**
```json
{
  "merchants": {"total": 50, "active": 35, "this_month": 8},
  "conversations": {"total": 1200, "today": 45},
  "messages": {"total": 8500},
  "sales": {"total": 300},
  "subscriptions": {
    "by_plan": {"trial": 10, "basic": 20, "premium": 5},
    "expiring_soon": 3
  }
}
```

### GET `/api/admin/merchants`
Lister marchands avec filtres.
**Query:** `page`, `limit`, `status_filter` (`active|inactive|trial|expired`), `search`

### GET `/api/admin/merchants/{merchant_id}`
Détails complets d'un marchand (subscription, stats, conversations, WhatsApp status).

### PUT `/api/admin/merchants/{merchant_id}/status`
Activer/désactiver un marchand.

**Request:**
```json
{
  "is_active": false,
  "reason": "Violation des CGU"
}
```

### PUT `/api/admin/merchants/{merchant_id}/subscription`
Modifier l'abonnement.

**Request:**
```json
{
  "plan": "premium",
  "duration_months": 3,
  "messages_limit": 10000,
  "products_limit": 200
}
```

### GET `/api/admin/admins`
Lister les admins.

### POST `/api/admin/admins`
Créer un admin.

**Request:**
```json
{
  "email": "newadmin@kalga.com",
  "password": "securepass",
  "name": "Admin 2"
}
```

### GET `/api/admin/audit-logs`
Logs d'audit admin.
**Query:** `page`, `limit` (defaut 50)

### POST `/api/admin/system/cleanup-expired`
Nettoyer abonnements expirés et conversations anciennes.

### GET `/api/admin/system/whatsapp-status`
Status WhatsApp de tous les marchands.

### GET `/api/admin/pending-activations`
Marchands en attente d'activation.

### POST `/api/admin/send-activation/{merchant_id}`
Générer et envoyer un code d'activation par WhatsApp.

### GET `/api/admin/activation-history`
Historique des codes d'activation.

---

## 13. WHATSAPP BRIDGE (Port 3001)

### GET `/health`
Health check.

### GET `/status`
Status global de tous les marchands connectés.

### GET `/status/{merchant_phone}`
Status WhatsApp d'un marchand.

### POST `/connect`
Initialiser une session WhatsApp (génère QR code).

**Request:**
```json
{
  "merchant_phone": "2250700000000"
}
```

### GET `/qr/{merchant_phone}`
Page HTML avec le QR code (auto-refresh 10s).

### POST `/send`
Envoyer un message texte.

**Request:**
```json
{
  "merchant_phone": "2250700000000",
  "to": "2250700000001",
  "message": "Bonjour!"
}
```

### POST `/send-image`
Envoyer une image.

**Request:**
```json
{
  "merchant_phone": "2250700000000",
  "to": "2250700000001",
  "image_path": "/path/to/image.jpg",
  "caption": "Voici le produit"
}
```

### POST `/send-location`
Envoyer une localisation GPS.

**Request:**
```json
{
  "merchant_phone": "2250700000000",
  "to": "2250700000001",
  "latitude": 5.3364,
  "longitude": -4.0266,
  "name": "Boutique JK",
  "address": "Cocody, Abidjan"
}
```

---

## ENUMS

### ConversationStatus
| Valeur | Description |
|--------|-------------|
| `active` | En cours |
| `negotiating` | Négociation en cours |
| `agreed` | Prix accepté, choix livraison/pickup |
| `pending_delivery` | En attente de livraison |
| `pending_pickup` | En attente de récupération |
| `completed` | Vente terminée |
| `abandoned` | Client parti |
| `ended` | Conversation terminée (pas de vente) |
| `expired` | Expirée (7+ jours) |

---

## FLUX D'AUTHENTIFICATION

1. **Inscription:** `POST /api/auth/register` → `access_token` + `refresh_token`
2. **Connexion:** `POST /api/auth/login` → `access_token` + `refresh_token`
3. **Utilisation:** Header `Authorization: Bearer <access_token>`
4. **Token expiré:** `POST /api/auth/refresh` avec `refresh_token` → nouveau `access_token`
5. **Rôles:** `merchant` (utilisateur standard) et `admin` (accès complet)

**Note:** La plupart des endpoints marchands (products, merchants, chat, stats) ne requièrent PAS de JWT actuellement. Seuls `/api/auth/me`, `/api/auth/logout`, `/api/auth/change-password` et tous les `/api/admin/*` requièrent un JWT valide. Les endpoints storefront sont intentionnellement publics.

---

## ENDPOINTS UTILITAIRES

### GET `/`
Info API racine.

### GET `/health`
Health check API.

**Response:** `{"status": "healthy", "service": "kalga-api"}`
