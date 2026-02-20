# KALGA - WhatsApp Commerce Automation

Automatisation WhatsApp pour marchands - Gestion des ventes via Status WhatsApp.

## Architecture

```
KALGA/
├── kalga-api/          # API FastAPI (Python)
│   └── app/
│       ├── routers/    # Endpoints API
│       ├── services/   # Logique métier (IA, conversations)
│       ├── models/     # Modèles Pydantic
│       └── database/   # SQLite + gestion données
├── kalga-whatsapp/     # Bridge WhatsApp (Node.js)
└── dashboard/          # Interface web simple
    ├── static/         # CSS, JS
    └── templates/      # HTML
```

## Fonctionnalités

- Marchands publient produits via Status WhatsApp
- Bot engage automatiquement les clients qui répondent
- Conversation naturelle (pas robotique)
- Négociation de prix (prix normal → prix minimum)
- Chaque marchand = son propre numéro WhatsApp
- Historique conversations: 7 jours max

## Flux

1. Marchand crée produit → reçoit code #K001
2. Marchand poste Status avec #K001
3. Client répond au Status
4. Bot détecte #K001, engage conversation naturelle
5. Négociation jusqu'à accord ou abandon

## Lancement

```bash
# API (port 8001)
cd kalga-api
pip install -r requirements.txt
uvicorn app.main:app --port 8001

# WhatsApp Bridge (port 3001)
cd kalga-whatsapp
npm install
npm start

# Dashboard
Ouvrir dashboard/index.html
```

## Configuration

Voir `.env.example` pour les variables d'environnement.
