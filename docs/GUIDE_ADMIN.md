# GUIDE ADMINISTRATEUR - KALGA

## Introduction

KALGA est un système d'automatisation de commerce via WhatsApp. Ce guide explique comment installer, configurer et maintenir l'application.

---

## 1. Prérequis

### Logiciels requis

| Logiciel | Version minimum | Téléchargement |
|----------|-----------------|----------------|
| Node.js | 18+ | https://nodejs.org |
| Python | 3.10+ | https://python.org |
| Git | 2.0+ | https://git-scm.com |

### Vérifier les installations

```bash
node --version    # Doit afficher v18.x.x ou plus
python --version  # Doit afficher Python 3.10.x ou plus
pip --version     # Doit être installé avec Python
```

---

## 2. Installation

### 2.1 Cloner le projet

```bash
git clone <url-du-repo> KALGA
cd KALGA
```

### 2.2 Installer l'API (Backend Python)

```bash
cd kalga-api
pip install -r requirements.txt
```

### 2.3 Installer le Bridge WhatsApp (Node.js)

```bash
cd kalga-whatsapp
npm install
```

---

## 3. Configuration

### 3.1 Configurer l'API (kalga-api/.env)

Créer le fichier `kalga-api/.env` :

```env
DEBUG=true
DEEPSEEK_API_KEY=sk-votre-cle-api-deepseek
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
WHATSAPP_BRIDGE_URL=http://localhost:3001
CONVERSATION_EXPIRY_DAYS=7
```

**Important** : Obtenir une clé API DeepSeek sur https://platform.deepseek.com

### 3.2 Configurer le Bridge (kalga-whatsapp/.env)

Créer le fichier `kalga-whatsapp/.env` :

```env
NODE_ENV=development
PORT=3001
KALGA_API_URL=http://localhost:8001
DEBUG=true
```

---

## 4. Démarrage des services

### 4.1 Démarrer l'API (Terminal 1)

```bash
cd kalga-api
uvicorn app.main:app --port 8001 --reload
```

Vous devez voir :
```
INFO:     Uvicorn running on http://127.0.0.1:8001
KALGA API prête!
```

### 4.2 Démarrer le Bridge WhatsApp (Terminal 2)

```bash
cd kalga-whatsapp
npm start
```

Vous devez voir :
```
🚀 KALGA WhatsApp Bridge démarré sur port 3001
📍 API KALGA: http://localhost:8001
```

### 4.3 Vérifier que tout fonctionne

```bash
# Tester l'API
curl http://localhost:8001/health
# Réponse attendue: {"status":"healthy","service":"kalga-api"}

# Tester le Bridge
curl http://localhost:3001/status
# Réponse attendue: {"service":"kalga-whatsapp-bridge",...}
```

---

## 5. Connexion d'un marchand

### 5.1 Créer le marchand (si nouveau)

```bash
curl -X POST http://localhost:8001/api/merchants/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Nom du Marchand", "phone": "2250123456789", "business_name": "Ma Boutique"}'
```

### 5.2 Connecter WhatsApp

```bash
curl -X POST http://localhost:3001/connect \
  -H "Content-Type: application/json" \
  -d '{"merchant_phone": "2250123456789"}'
```

### 5.3 Scanner le QR Code

Ouvrir dans le navigateur :
```
http://localhost:3001/qr/2250123456789
```

Le marchand scanne le QR code avec WhatsApp sur son téléphone.

---

## 6. Structure des fichiers

```
KALGA/
├── kalga-api/                 # Backend Python (FastAPI)
│   ├── app/
│   │   ├── main.py           # Point d'entrée de l'API
│   │   ├── config.py         # Configuration
│   │   ├── database/         # Gestion base de données
│   │   │   ├── db.py         # Classe Database
│   │   │   └── kalga.db      # Base SQLite
│   │   ├── models/           # Schémas Pydantic
│   │   │   └── schemas.py
│   │   ├── routers/          # Endpoints API
│   │   │   ├── merchants.py
│   │   │   ├── products.py
│   │   │   ├── chat.py
│   │   │   └── merchant_commands.py
│   │   └── services/         # Logique métier
│   │       └── conversation_ai.py
│   ├── requirements.txt
│   └── .env
│
├── kalga-whatsapp/            # Bridge WhatsApp (Node.js)
│   ├── server.js             # Serveur principal
│   ├── sessions/             # Sessions WhatsApp sauvegardées
│   ├── package.json
│   └── .env
│
├── dashboard/                 # Interface web (optionnel)
│   └── index.html
│
└── docs/                      # Documentation
    ├── GUIDE_ADMIN.md
    ├── GUIDE_UTILISATEUR.md
    └── GUIDE_TECHNIQUE.md
```

---

## 7. Maintenance

### 7.1 Logs

**API** : Les logs s'affichent dans le terminal où uvicorn est lancé.

**Bridge** : Les logs sont dans `kalga-whatsapp/server.log` ou dans le terminal.

### 7.2 Base de données

La base SQLite est dans `kalga-api/app/database/kalga.db`.

Pour voir les données :
```bash
cd kalga-api/app/database
sqlite3 kalga.db

# Commandes utiles
.tables                    # Voir les tables
SELECT * FROM merchants;   # Voir les marchands
SELECT * FROM products;    # Voir les produits
SELECT * FROM conversations;  # Voir les conversations
.quit                      # Quitter
```

### 7.3 Nettoyer les conversations expirées

```bash
curl -X POST http://localhost:8001/api/chat/cleanup
```

### 7.4 Redémarrer les services

```bash
# Arrêter tout
# Windows:
taskkill /IM node.exe /F
taskkill /IM python.exe /F

# Linux/Mac:
pkill -f node
pkill -f uvicorn

# Puis relancer (voir section 4)
```

---

## 8. Dépannage

### Problème : Port déjà utilisé

```bash
# Trouver le processus sur le port 8001
netstat -ano | findstr :8001

# Tuer le processus (remplacer XXXX par le PID)
taskkill /PID XXXX /F
```

### Problème : WhatsApp déconnecté

1. Supprimer le dossier de session :
```bash
rm -rf kalga-whatsapp/sessions/kalga-NUMERO
```

2. Redémarrer le bridge et rescanner le QR code.

### Problème : L'IA ne répond pas

Vérifier :
1. La clé API DeepSeek est valide
2. Le fichier `.env` est bien configuré
3. L'API DeepSeek est accessible

---

## 9. Sécurité

- Ne jamais partager les fichiers `.env`
- Ne jamais commiter les clés API sur Git
- Sauvegarder régulièrement `kalga.db`
- Les sessions WhatsApp dans `sessions/` sont sensibles

---

## 10. Contacts

Pour toute question technique, contacter l'équipe de développement.
