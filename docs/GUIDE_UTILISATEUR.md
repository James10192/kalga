# GUIDE UTILISATEUR - KALGA

## Qu'est-ce que KALGA ?

KALGA est un assistant de vente automatique pour WhatsApp. Il permet de :
- Vendre vos produits via les Status WhatsApp
- Laisser un robot intelligent répondre aux clients automatiquement
- Négocier les prix avec les clients selon vos limites
- Recevoir des notifications quand une vente est conclue

---

## 1. Premiers pas

### 1.1 Connexion de votre WhatsApp

1. L'administrateur vous donnera un lien QR code
2. Ouvrez WhatsApp sur votre téléphone
3. Allez dans **Paramètres > Appareils connectés > Connecter un appareil**
4. Scannez le QR code affiché

Une fois connecté, vous verrez un message de confirmation.

---

## 2. Créer un produit

### Via WhatsApp (Recommandé)

1. **Ouvrez WhatsApp** et allez dans votre propre conversation (messages à vous-même)

2. **Écrivez** : `produit`

3. **Suivez les étapes** :

```
Vous : produit
Bot  : 📦 Création d'un nouveau produit
       Étape 1/4: Quel est le nom du produit?

Vous : Robe Wax Taille M
Bot  : ✅ Nom: Robe Wax Taille M
       Étape 2/4: Quel est le prix de vente? (en FCFA)

Vous : 20000
Bot  : ✅ Prix: 20,000 F
       Étape 3/4: Quel est le prix minimum que tu acceptes?

Vous : 15000
Bot  : ✅ Prix minimum: 15,000 F
       Étape 4/4: Ajoute une description (ou écris "passer")

Vous : Belle robe africaine, disponible en M et L
Bot  : ✅ Produit créé avec succès!
       📦 Robe Wax Taille M
       🏷️ Code: #K006
       💰 Prix: 20,000 F
       💵 Prix min: 15,000 F

       👉 Ajoute #K006 dans ton Status WhatsApp!
```

4. **Notez le code** (ex: #K006) - vous en aurez besoin pour le Status

---

## 3. Publier un produit sur Status

1. **Créez un Status WhatsApp** avec :
   - La **photo** du produit
   - Le **code** dans le texte (ex: #K006)
   - Le **prix** affiché

**Exemple de texte pour le Status :**
```
Robe Wax Africaine #K006
Prix: 20,000 F
Taille M disponible
DM pour commander!
```

---

## 4. Comment ça fonctionne ensuite ?

### Quand un client répond à votre Status :

```
Client : "C'est disponible ?"
Bot    : "Salut! Oui c'est disponible. C'est 20,000 F. Ça te dit?"

Client : "C'est trop cher, 12000 ?"
Bot    : "Ah 12,000 F c'est trop bas! Fais 16,000 F et on se comprend."

Client : "15000 dernier prix"
Bot    : "Ça marche pour 15,000 F! Tu veux qu'on te livre?"

Client : "Oui"
Bot    : "C'est noté! Le patron va te contacter pour la livraison."
```

### Vous recevez une notification :
```
🛒 NOUVELLE VENTE KALGA!

Produit: Robe Wax (#K006)
Prix accordé: 15,000 F
Client: 22501234567

Le client attend la livraison.
Contacte-le vite!
```

---

## 5. Commandes disponibles

Écrivez ces commandes dans votre propre conversation WhatsApp :

| Commande | Description |
|----------|-------------|
| `produit` | Créer un nouveau produit |
| `mes produits` | Voir la liste de vos produits |
| `supprimer #K006` | Retirer un produit de la vente |
| `aide` | Voir toutes les commandes |

### Exemples :

**Voir vos produits :**
```
Vous : mes produits
Bot  : 📦 Tes produits:
       • #K003 - Habi (20,000 F)
       • #K004 - Ventilateur (20,000 F)
       • #K006 - Robe Wax (20,000 F)
```

**Supprimer un produit :**
```
Vous : supprimer #K004
Bot  : ✅ Produit #K004 (Ventilateur) supprimé!
```

---

## 6. Règles de négociation automatique

Le bot négocie intelligemment selon vos paramètres :

| Situation | Action du bot |
|-----------|---------------|
| Client propose ≥ prix minimum | Accepte et propose la livraison |
| Client propose entre min et max | Fait une contre-offre |
| Client propose trop bas (1-2 fois) | Refuse poliment, demande mieux |
| Client propose trop bas (2+ fois) | Donne le dernier prix (votre minimum) |
| Client refuse le minimum (3+ fois) | Termine poliment la négociation |

**Important :** Le bot ne révèle JAMAIS votre prix minimum au client !

---

## 7. Conseils pour bien vendre

### Pour les photos de Status :
- Utilisez des photos de bonne qualité
- Montrez le produit sous plusieurs angles
- Ajoutez le prix visible sur la photo

### Pour les prix :
- Mettez un prix de vente légèrement au-dessus de votre objectif
- Le prix minimum doit être votre limite absolue
- Laissez une marge de négociation (10-20%)

### Exemple de stratégie :
- Vous voulez vendre à 15,000 F minimum
- Mettez le prix affiché à 20,000 F
- Mettez le prix minimum à 15,000 F
- Le bot négociera entre 15,000 et 20,000 F

---

## 8. Questions fréquentes

### Q: Le bot répond-il 24h/24 ?
**R:** Oui, tant que les services sont actifs, le bot répond automatiquement.

### Q: Puis-je intervenir dans une conversation ?
**R:** Oui, vous pouvez répondre directement au client à tout moment. Le bot continuera la conversation.

### Q: Que faire si le bot ne répond pas ?
**R:** Contactez l'administrateur pour vérifier que les services sont actifs.

### Q: Puis-je modifier un produit ?
**R:** Pour l'instant, supprimez le produit et recréez-le avec les nouvelles informations.

### Q: Les conversations sont-elles sauvegardées ?
**R:** Oui, toutes les conversations sont enregistrées pendant 7 jours.

---

## 9. Support

En cas de problème :
1. Vérifiez que vous avez bien suivi les étapes
2. Contactez l'administrateur du système
3. Fournissez le code produit et le numéro du client concerné

---

**Bonne vente avec KALGA !** 🛒
