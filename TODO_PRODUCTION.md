# KALGA - TODO LIST PRODUCTION

## Etat actuel
- Dashboard fonctionnel avec connexion WhatsApp, gestion produits et conversations
- API backend operationnelle
- Bot IA de negociation en place

---

## PRIORITE CRITIQUE (A faire AVANT lancement)

| # | Tache | Impact | Status |
|---|-------|--------|--------|
| 1 | Securiser la cle API DeepSeek (.gitignore) | Cle volee = factures illimitees | [x] .gitignore OK + warning au demarrage |
| 2 | Ajouter un fallback si l'API IA echoue | Clients sans reponse = perdus | [x] DEJA IMPLEMENTE (conversation_ai.py:440-562) |
| 3 | Corriger la gestion des reconnexions WhatsApp | Messages non envoyes | [x] DEJA IMPLEMENTE (server.js MAX_RECONNECT=5) |
| 4 | Ajouter validation des numeros de telephone | Erreurs et crashs | [x] Ajoute dans schemas.py (format CI 225...) |
| 5 | Limiter la taille des messages clients | Crash API / cout DeepSeek | [x] Ajoute dans schemas.py + server.js (max 2000 car) |

---

## PRIORITE HAUTE (A faire dans la semaine)

| # | Tache | Impact | Status |
|---|-------|--------|--------|
| 6 | Ameliorer le prompt IA | Qualite des conversations | [x] Expressions ivoiriennes ajoutees |
| 7 | Ajouter des index DB manquants | Lenteur avec beaucoup de conversations | [x] Index composites ajoutes (db.py) |
| 8 | Pagination des listes | Timeout / crash | [x] Pagination ajoutee (merchants, chat) |
| 9 | Backup automatique de la DB | Perte de donnees = catastrophe | [x] Script scripts/backup_db.py cree |
| 10 | Nettoyer les conversations expirees (cron) | DB qui grossit indefiniment | [x] Script scripts/cleanup_expired.py cree |
| 11 | Rate limiting basique | Anti-spam/abuse | [x] slowapi 30req/min sur /chat/incoming |
| 12 | Ameliorer les logs | Debug difficile | [x] Logs separes (api/errors) + rotation 7j |

---

## BUGS CORRIGES

| Date | Bug | Solution |
|------|-----|----------|
| 2026-01-18 | Bot redemande livraison/magasin apres 'D accord j attends votre retour' | Corrige dans conversation_ai.py |
| 2026-01-28 | Bot en boucle sur demande de localisation | Ajout status pending_pickup + notification marchand |
| 2026-01-28 | Marchand ne peut pas finaliser vente apres negociation | Ajout commandes !ok et !annuler |

---

## FONCTIONNALITES AJOUTEES

| Date | Fonctionnalite | Description |
|------|----------------|-------------|
| 2026-01-28 | Localisation marchand obligatoire | Demande de localisation a l'inscription (dashboard), stockage en DB |
| 2026-01-28 | Envoi automatique de localisation | Quand client demande adresse, envoi GPS automatique au client |
| 2026-01-28 | Commandes marchands WhatsApp | !ok, !livre, !annuler pour gerer ventes via WhatsApp |
| 2026-01-28 | Endpoint /send-location | Bridge WhatsApp peut envoyer des messages de localisation GPS |

---

## NOTES

- Fichier cree pour garder trace des taches a faire
- Cocher [x] quand une tache est terminee
- Ajouter les nouveaux bugs decouverts dans la section appropriee

