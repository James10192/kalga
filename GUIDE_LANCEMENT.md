# GUIDE COMPLET - Lancer KALGA du Debut a la Fin

Ce guide te permet de lancer l'application KALGA completement, etape par etape.

---

## ETAPE 1 : Prerequis (a faire une seule fois)

### 1.1 Installer Python (pour l'API)
- Telecharger Python 3.10+ : https://www.python.org/downloads/
- Cocher "Add Python to PATH" lors de l'installation

### 1.2 Installer Node.js (pour WhatsApp Bridge)
- Telecharger Node.js 18+ : https://nodejs.org/
- Choisir la version LTS

### 1.3 Verifier les installations
Ouvrir un terminal (CMD ou PowerShell) :
```bash
python --version
# Doit afficher : Python 3.10.x ou plus

node --version
# Doit afficher : v18.x.x ou plus

npm --version
# Doit afficher : 9.x.x ou plus
```

---

## ETAPE 2 : Configuration (a faire une seule fois)

### 2.1 Configurer l'API (kalga-api)

**Ouvrir un terminal et executer :**
```bash
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-api"
```

**Installer les dependances :**
```bash
pip install -r requirements.txt
```

**Creer le fichier .env :**
Creer un fichier `kalga-api/.env` avec ce contenu :
```
DEBUG=true
DEEPSEEK_API_KEY=sk-ta-cle-deepseek-ici
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
WHATSAPP_BRIDGE_URL=http://localhost:3001
CONVERSATION_EXPIRY_DAYS=7
```

### 2.2 Configurer WhatsApp Bridge (kalga-whatsapp)

**Ouvrir un AUTRE terminal et executer :**
```bash
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-whatsapp"
```

**Installer les dependances :**
```bash
npm install
```

**Creer le fichier .env :**
Creer un fichier `kalga-whatsapp/.env` avec ce contenu :
```
NODE_ENV=development
PORT=3001
KALGA_API_URL=http://localhost:8001
DEBUG=true
```

---

## ETAPE 3 : Lancer les Services (a faire a chaque demarrage)

### IMPORTANT : Tu dois ouvrir 2 terminaux separes !

### Terminal 1 : Lancer l'API

```bash
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-api"
uvicorn app.main:app --port 8001 --reload
```

**Tu dois voir :**
```
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Started reloader process
Initialisation KALGA API...
Nettoyage des conversations expirees effectue
KALGA API prete!
```

### Terminal 2 : Lancer WhatsApp Bridge

```bash
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-whatsapp"
npm start
```

**Tu dois voir :**
```
🚀 KALGA WhatsApp Bridge (Baileys) demarre sur port 3001
📍 API KALGA: http://localhost:8001
```

### Verifier que tout fonctionne

Ouvrir dans un navigateur :
- API : http://localhost:8001 (doit afficher "KALGA API")
- Bridge : http://localhost:3001 (doit afficher "KALGA WhatsApp Bridge")

---

## ETAPE 4 : Connecter un Marchand

### 4.1 Ouvrir le Dashboard
Double-cliquer sur le fichier :
```
C:/Users/USER PC/Documents/propre à moi/KALGA/dashboard/index.html
```

### 4.2 Entrer le numero du marchand
- Format : sans + ni espaces
- Exemple Cote d'Ivoire : `2250544210112`
- Exemple : `0544210112` (fonctionne aussi)

### 4.3 Scanner le QR Code
1. Cliquer sur "Connecter WhatsApp"
2. Scanner le QR code avec WhatsApp (Appareils connectes > Connecter un appareil)
3. Attendre "Connecte" en vert

---

## ETAPE 5 : Utiliser KALGA via WhatsApp

### 5.1 Commandes du marchand (s'ecrire a soi-meme)

Le marchand doit s'envoyer des messages A LUI-MEME dans WhatsApp :

| Commande | Action |
|----------|--------|
| `aide` | Voir toutes les commandes |
| `produit` | Creer un nouveau produit |
| `mes produits` | Voir la liste des produits |
| `supprimer #K001` | Supprimer un produit |

### 5.2 Creer un produit

1. Ecrire `produit` (a toi-meme)
2. Repondre avec le nom du produit : `Robe Wax`
3. Repondre avec le prix : `25000` ou `25k`
4. Repondre avec le prix minimum : `20000` ou `20k`
5. Repondre avec la description ou `passer`

**Resultat :** Tu recois un code comme `#K001`

### 5.3 Poster un Status WhatsApp

Creer un Status avec le code produit :
```
Belle Robe Wax disponible! #K001 - 25,000 F
Contactez-moi vite!
```

### 5.4 Quand un client repond

1. Le client voit ton Status et repond
2. KALGA detecte automatiquement le code #K001
3. Le bot negocie avec le client
4. Quand le client accepte, tu recois une notification

---

## ETAPE 6 : Arreter les Services

### Dans chaque terminal, appuyer sur : `Ctrl + C`

---

## RESUME : Lancement Rapide (apres configuration)

```bash
# Terminal 1 - API
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-api"
uvicorn app.main:app --port 8001 --reload

# Terminal 2 - WhatsApp
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-whatsapp"
npm start
```

Puis ouvrir `dashboard/index.html` et connecter WhatsApp.

---

## DEPANNAGE

### L'API ne demarre pas
```bash
# Reinstaller les dependances
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-api"
pip install -r requirements.txt
```

### WhatsApp Bridge ne demarre pas
```bash
# Reinstaller les dependances
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-whatsapp"
rm -rf node_modules
npm install
```

### Comment redemarrer l'API (apres modification du code)

**Etape 1 :** Trouver le terminal ou l'API tourne (celui qui affiche "KALGA API prete!")

**Etape 2 :** Arreter l'API
- Appuyer sur `Ctrl + C` dans ce terminal
- Tu verras : "Arret KALGA API..."

**Etape 3 :** Relancer l'API
```bash
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-api"
uvicorn app.main:app --port 8001 --reload
```

**Etape 4 :** Verifier que ca marche
- Attendre "KALGA API prete!"
- Ou tester : `curl http://localhost:8001/health`

### Comment redemarrer WhatsApp Bridge

**Etape 1 :** Trouver le terminal du Bridge (celui qui affiche "KALGA WhatsApp Bridge")

**Etape 2 :** Arreter le Bridge
- Appuyer sur `Ctrl + C`

**Etape 3 :** Relancer le Bridge
```bash
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-whatsapp"
npm start
```

**Note :** Apres redemarrage du Bridge, tu devras peut-etre rescanner le QR code.

### "mes produits" ou "produit" ne marche pas

**Cause possible 1 :** Session de creation en cours
- Ecris `annuler` d'abord, puis `mes produits`

**Cause possible 2 :** L'API n'est pas a jour
- Redemarre l'API (voir section ci-dessus)

**Cause possible 3 :** WhatsApp n'est pas connecte
- Verifie le statut : http://localhost:3001/status
- Si "connected": false, reconnecte via le dashboard

### QR Code ne s'affiche pas
1. Arreter le Bridge (Ctrl+C)
2. Supprimer le dossier sessions :
```bash
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-whatsapp"
rm -rf sessions
```
3. Relancer : `npm start`

### WhatsApp se deconnecte souvent
- Garde ton telephone connecte a internet
- Ne deconnecte pas WhatsApp Web manuellement
- Le bot se reconnecte automatiquement (max 5 tentatives)

### Verifier que les services tournent
```bash
# Dans un nouveau terminal
curl http://localhost:8001/health
curl http://localhost:3001/health
```

### Reinitialisation complete (si rien ne marche)

Si tu as beaucoup de problemes, fais une reinitialisation complete :

**Etape 1 : Arreter tous les processus**
- Fermer tous les terminaux
- Ou dans PowerShell : `Stop-Process -Name node -Force; Stop-Process -Name python -Force`

**Etape 2 : Supprimer les sessions WhatsApp**
```bash
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-whatsapp"
rm -rf sessions
```

**Etape 3 : Relancer les services**
```bash
# Terminal 1 - API
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-api"
uvicorn app.main:app --port 8001

# Terminal 2 - WhatsApp Bridge
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-whatsapp"
npm start
```

**Etape 4 : Reconnecter WhatsApp**
- Ouvrir http://localhost:3001/qr/TON_NUMERO
- Scanner le QR code

---

## PROBLEMES CONNUS ET SOLUTIONS

### Probleme : Les commandes (produit, mes produits) ne repondent pas

**Cause :** Ce probleme survient quand WhatsApp utilise un format d'identifiant different (LID vs standard).
Quand tu t'ecris a toi-meme, WhatsApp peut utiliser un identifiant special (`@lid`) au lieu du numero standard (`@s.whatsapp.net`).

**Solution :** Ce probleme a ete corrige dans le code. Le bot repond maintenant directement a l'endroit ou tu ecris, quel que soit le format d'identifiant.

**Si ca ne marche toujours pas :**
1. Redemarre le WhatsApp Bridge (Ctrl+C puis `npm start`)
2. Verifie que tu vois les logs dans le terminal :
   ```
   📨 Message reçu:
      remoteJid: ...@lid
      fromMe: true
      text: "mes produits"
      → Traitement comme commande marchand
   🔧 Message marchand detecte: "mes produits"
      API Response action: list
      Envoi a: ...@lid
   📤 Reponse envoyee au marchand
   ```
3. Si tu vois ces logs mais pas de reponse dans WhatsApp, c'est un probleme de Baileys. Fais une reinitialisation complete (voir section ci-dessus).

### Probleme : Plusieurs processus tournent en meme temps

**Symptome :** L'API ou le Bridge ne demarre pas, ou des comportements bizarres.

**Verification :**
```bash
netstat -ano | findstr ":8001"
netstat -ano | findstr ":3001"
```

**Solution :** Arreter tous les processus et relancer proprement :
```bash
# PowerShell
Stop-Process -Name node -Force -ErrorAction SilentlyContinue
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
```

### Probleme : Session de creation de produit bloquee

**Symptome :** Quand tu ecris "mes produits", ca te demande un prix au lieu de lister les produits.

**Solution :** Ecris `annuler` d'abord, puis `mes produits`.
Le systeme annule aussi automatiquement si tu ecris `aide`, `liste`, ou `?`.

### Probleme : WhatsApp se deconnecte (erreurs 408, 428, 515)

**Signification des erreurs :**
- **408** = Timeout - WhatsApp ne repond pas assez vite
- **428** = Conflit - Une autre session WhatsApp Web est peut-etre active
- **515** = Erreur serveur WhatsApp temporaire

**Causes possibles :**
1. Une autre session WhatsApp Web est ouverte (ordinateur, navigateur)
2. Le telephone a perdu sa connexion internet
3. WhatsApp detecte une activite automatisee (trop de messages)

**Solution immediate :**
1. Le bot essaie automatiquement de se reconnecter (5 tentatives)
2. Regarde les logs - si tu vois `✅ WhatsApp connecté`, c'est bon
3. Si ca echoue apres 5 tentatives, fais une reinitialisation complete

**Prevention :**
1. **Ferme toutes les autres sessions WhatsApp Web** :
   - Va dans WhatsApp > Parametres > Appareils connectes
   - Deconnecte tous les appareils sauf KALGA
2. **Garde ton telephone connecte a internet** (Wi-Fi stable)
3. **Ne scanne pas le QR code trop souvent** - ca peut declencher une detection
4. **Evite d'envoyer trop de messages rapidement** - WhatsApp peut bloquer

**Si les deconnexions persistent :**
```bash
# 1. Arreter le Bridge
Ctrl+C dans le terminal du Bridge

# 2. Supprimer les sessions
cd "C:/Users/USER PC/Documents/propre à moi/KALGA/kalga-whatsapp"
rm -rf sessions

# 3. Relancer
npm start

# 4. Scanner le nouveau QR code
```

### Probleme : Le code produit n'est pas detecte dans les reponses au Status

**Symptome :** Quand quelqu'un repond a ton Status avec #K012, le bot dit "Tu t'interesses a quel produit?"

**Causes possibles :**
1. Le Status est une image/video mais le code n'est pas dans la legende (caption)
2. Le code est mal ecrit (doit etre #K suivi de 3 chiffres, ex: #K001, #K012)

**Solution :**
- Assure-toi que le code produit (#K001) est visible dans la legende de ton Status
- Le code doit etre au format exact : # + K + 3 chiffres
- Verifie les logs du Bridge pour voir si le code est detecte :
  ```
  📋 Message cité: "#K012 Merci de commander..."
  🏷️ Code produit trouvé: #K012
  ```

**Ce probleme a ete corrige :** Le bot detecte maintenant les codes dans :
- Les messages texte cites
- Les legendes d'images
- Les legendes de videos
- Le message lui-meme (si le client ecrit "#K012 je veux ca")

---

## MESURES ANTI-BAN (comportement humain)

Le bot KALGA inclut des mesures pour éviter d'être détecté comme automatisé par WhatsApp.

### Ce que fait le bot automatiquement :

1. **Marque les messages comme lus** - Avant de répondre, le bot marque le message du client comme "vu" (les coches bleues)

2. **Affiche "en train d'écrire..."** - Le client voit que le marchand est en train de taper, comme un humain

3. **Délai aléatoire de 5 à 15 secondes** - Le bot attend un temps variable avant de répondre pour simuler le temps de lecture et de frappe

### Logs que tu verras dans le terminal :

```
📩 [22500000000] Message de 22512345678:
   "Je suis intéressé par le produit #K001"
🛒 Envoi à KALGA API...
✅ Réponse KALGA: "Ah super! Tu as bon goût..."
   🤖 Simulation comportement humain...
   👁️ Message marqué comme lu
   ⌨️ Statut "en train d'écrire" envoyé
   ⏳ Attente 8.3s avant réponse...
   ✅ Simulation terminée, envoi du message...
📤 Réponse envoyée à 22512345678
```

### Conseils supplémentaires pour éviter le ban :

1. **Ne pas envoyer trop de messages** - Si tu as beaucoup de clients, espace les réponses
2. **Varier les messages** - L'IA génère des réponses différentes, c'est bien
3. **Ne pas spammer** - Évite de créer trop de produits ou de faire trop de tests
4. **Garder une activité normale** - Utilise aussi ton WhatsApp normalement

### Si tu reçois un avertissement de WhatsApp :

1. Arrête le bot immédiatement (Ctrl+C)
2. Attends 24-48 heures avant de le relancer
3. Si le problème persiste, crée un nouveau numéro WhatsApp Business

---

## PORTS UTILISES

| Service | Port | URL |
|---------|------|-----|
| API KALGA | 8001 | http://localhost:8001 |
| WhatsApp Bridge | 3001 | http://localhost:3001 |
| Swagger Docs | 8001 | http://localhost:8001/docs |

---

## FICHIERS IMPORTANTS

```
KALGA/
├── kalga-api/
│   ├── .env                 # Configuration API (cle DeepSeek)
│   └── app/
│       └── database/
│           └── kalga.db     # Base de donnees SQLite
├── kalga-whatsapp/
│   ├── .env                 # Configuration Bridge
│   └── sessions/            # Sessions WhatsApp (ne pas supprimer!)
├── dashboard/
│   └── index.html           # Interface web
├── API_DOCUMENTATION.md     # Doc pour ton ami developpeur
└── GUIDE_LANCEMENT.md       # Ce fichier
```
