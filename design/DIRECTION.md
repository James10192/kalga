# KALGA — Direction de design (contrat UI pour 006/007/008)

> Issu d'une session ultrathink (2026-06-12). Remplace les prototypes rejetés de
> `design-prototypes/`. C'est le **contrat visuel** que les plans 006 (dashboard),
> 007 (storefront), 008 (admin) doivent suivre. Règles proprio : 1 accent + monochrome,
> mobile-first, touch ≥ 48px, UI en français (pas d'em dash), code en anglais, pas d'AI slop.

## Thèse

KALGA n'est PAS un tableau de bord SaaS. C'est **WhatsApp rencontre une caisse de boutique
premium.** Le marchand (solo, ouest-africain, non-technique, sur téléphone) vit dans deux
réalités : **les conversations** et **l'argent du jour**. L'interface se construit autour de
ça, pas autour de KPIs et de graphes.

## 7 principes

1. **Conversation = colonne vertébrale.** L'accueil dashboard est une liste vivante de
   conversations (façon WhatsApp) enrichie du contexte commerce, pas une grille de widgets.
2. **Argent toujours lisible.** Les montants FCFA sont first-class, grands, sans ambiguïté.
3. **Mobile natif, au pouce.** Barre d'onglets en bas (pas de sidebar desktop). Cibles ≥ 48px.
   Une action primaire par écran.
4. **Calme, pas chargé.** Whitespace généreux, un accent, zéro slop (pas d'orbes/gradients
   décoratifs, pas de graphe-spam, pas de glassmorphism, pas de compteurs animés gratuits).
5. **Rapide + tolérant réseau.** Skeletons, optimistic UI, storefront SSR, payloads légers.
6. **Confiance par l'artisanat.** Typo précise, spacing constant, vraies photos, jamais de vide.
7. **Français chaleureux, local.** FCFA, Wave/Orange Money/MTN MoMo. Voix directe, pas corporate.

## Tokens (source de vérité ; à porter en CSS variables shadcn/Tailwind v4 OKLCH)

**Couleurs**
- Accent (vert KALGA) : `--primary #16A34A`, deep `#15803D`, tint `#EAF6EE`. Usage chirurgical :
  actions primaires, argent positif/payé, marque. JAMAIS en décoration de fond.
- Neutres CHAUDS (pas gris froid) : page `#FBFAF7`, surface `#FFFFFF`, bordure `#ECEAE3`,
  bordure-forte `#DEDBD2`. Encre : texte `#1C1A17` (noir chaud), muted `#6B675F`, faint `#9C988E`.
- Sémantiques (tons mats, premium) :
  - Négociation (amber) `#B45309` / tint `#FAF1E4`
  - À livrer / en cours (blue) `#1D4ED8` / tint `#E9EEFC`
  - Payé / succès → vert primaire
  - Rupture / danger (red) `#B91C1C` / tint `#FBEAEA`
  - Info neutre : encre muted sur surface

**Typo**
- Display + montants : **Bricolage Grotesque** (600/700). Confiant, gros, du caractère.
- Corps : **Inter** (fallback de Geist) 400/500/600.
- Mono : **Geist Mono** / `ui-monospace` pour codes produit, codes d'activation, références.
- Échelle : montant héros ~34-40px, titres section 18-20px, corps 15-16px, méta 13px.

**Forme**
- Radius : cartes 16px, pills/chips 999px, inputs 12px.
- Ombres : très douces, basses (`0 1px 2px rgba(28,26,23,.05)`), jamais dramatiques.
- Bordures 1px `#ECEAE3` plutôt que des ombres lourdes pour séparer.
- Espacement : base 4px, rythme généreux (padding cartes 16-20px, gaps 12-16px).

**Motion**
- Subtile, utile : message entrant = slide doux ; changement de statut = transition de chip ;
  argent = fondu court. Rien de gratuit. `prefers-reduced-motion` respecté.

## Architecture par surface

### Dashboard marchand — `app.kalga.app` (mobile-first, onglets bas)
Barre d'onglets bas (pouce) : **Conversations · Produits · Argent · Réglages**.

- **Conversations (accueil, la colonne vertébrale)** : en-tête compact (Bonjour + nom boutique),
  **héros argent** « Aujourd'hui : 45 000 FCFA » (Bricolage, grand) + delta discret vs hier ;
  rangée de 2-3 pills quiètes (Conversations actives · À livrer · Rupture) ; puis la **liste de
  conversations** : avatar initiales, nom + aperçu dernier message, chip de statut (négo/à livrer/
  payé), heure, et si offre active une ligne argent « Offre 12 000 · demande 15 000 », point vert
  non-lu, glyphe bot si le bot gère. Tap → détail.
- **Détail conversation** : fil de bulles façon WhatsApp + panneau « affaire » slim (prix demandé,
  offre actuelle, marge, prix plancher) + actions (accepter / contre-offre / marquer payé /
  à livrer). Live via Convex `useQuery`.
- **Produits** : grille visuelle (les produits sont visuels), état de stock en pastille discrète
  (illimité/bas/rupture), FAB « + Ajouter », tap → édition. État vide soigné.
- **Argent** : vue registre, pas analytics. Gros « Aujourd'hui / Cette semaine », liste des ventes
  récentes, total. Simple et digne de confiance.
- **Réglages** : persona du bot (ton/style/catchphrase), boutique (slug `{slug}.kalga.app`, infos),
  connexion (ajouter email+mot de passe), **code d'activation** (abonnement, état actif/expiré),
  statut WhatsApp (connecté / QR à scanner).

### Storefront public — `{slug}.kalga.app` (SSR, conversion, zéro chrome d'app)
En-tête boutique (nom, tagline, bouton WhatsApp), filtre catégories, grille produits (prix FCFA,
état stock). Page produit : grandes photos, prix, variantes, **un** bouton vert « Commander sur
WhatsApp ». Micro-site retail propre, branté par marchand sur un squelette KALGA constant. Léger,
rapide, rend sans JS.

### Landing — `kalga.app` (marketing, pour faire signer les marchands)
Promesse de transformation : « Ton WhatsApp devient une boutique qui vend et négocie toute seule. »
Vraies captures du dashboard/conversation. Étapes (connecter WhatsApp → ajouter produits → le bot
vend), features, modèle d'abonnement par **code d'activation** (paiement Wave/OM hors app), CTA.
Héros distinctif (pas le cliché texte-gauche/image-droite) : un téléphone montrant une vraie
conversation KALGA où le bot négocie, avec l'issue en argent.

### Admin KALGA — `app.kalga.app/admin` (équipe KALGA, pas le marchand)
Surface plus dense, desktop-leaning (densité différente du dashboard marchand) : liste marchands,
**émission de codes d'activation**, audit logs, statut WhatsApp par marchand. Même tokens, densité
supérieure.

## Inventaire de composants (à construire en shadcn/ui, React)
Money hero, stat pill, conversation row (avatar + preview + status chip + money line), status chip
(négo/à livrer/payé/rupture), product card (image + prix + pastille stock), bottom tab bar, deal
panel (négociation), bouton WhatsApp, input OTP, activation-code input, QR/statut WhatsApp, empty
states, skeletons.

## Anti-patterns (rejet automatique en review)
- Grille de cartes KPI en accueil (c'est de l'analytics, pas le besoin marchand).
- Sidebar desktop rétrécie en mobile (utiliser onglets bas).
- Gris froid SaaS, gradients/orbes décoratifs, glassmorphism, graphe-spam.
- Montants FCFA en petit/secondaire.
- Plus d'un accent. Vert utilisé en décoration de fond.
- Em dash dans le texte français.
