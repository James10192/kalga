# 000 — Décisions d'architecture & cible (ADR)

> Document de référence (pas un plan exécutable). Verrouille les décisions prises
> avec le proprio le 2026-06-11. Tout plan `001+` s'y appuie. Si une décision
> change, mettre à jour ce fichier ET les plans impactés.

**Stamp** : décidé au commit `1e28bf5`, 2026-06-11.

---

## Contexte

KALGA = automatisation du commerce WhatsApp. Aujourd'hui :

- `kalga-api/` — FastAPI (port 8001), SQLite (aiosqlite), 21 tables, ~22k LOC.
- `kalga-whatsapp/` — bridge Node Baileys (port 3001), socket WhatsApp persistant.
- `kalga-frontend/` — **Nuxt 4 / Vue 3** (storefront + dashboard + admin) — **abandonné** (voir D1).
- `dashboard/`, `storefront/` — anciens fronts statiques HTML/JS.

Migration décidée : **frontend → TanStack Start (React)**, **DB + auth → Convex**,
**déploiement front → Vercel**. Backend Python + bridge restent (hébergement reporté).

---

## Décisions verrouillées

| # | Décision | Choix |
|---|----------|-------|
| **D1** | Frontend | **Réécriture complète en TanStack Start (React 19 + Vite SSR)**. Le Nuxt `kalga-frontend/` est conservé comme **référence visuelle uniquement**, aucun code migré. Nouveau dossier : `kalga-web/`. |
| **D2** | Surfaces | 3 surfaces dans **une seule app** TanStack Start, routées par **hostname** : `kalga.app`/`www` = **landing**, `app.kalga.app` = **dashboard marchand**, `{slug}.kalga.app` = **storefront public** (+ admin sous `app.kalga.app/admin`). |
| **D3** | Source de vérité données | **Convex = SoT unique**. SQLite abandonné. **Python réécrit** pour appeler Convex (client Python officiel) y compris l'écriture des messages/mémoire pendant le chat. Bénéfice : conversations **live** au dashboard via `useQuery`. |
| **D4** | Auth | **Better Auth single-store sur Convex, Local Install** (`@convex-dev/better-auth`), plugins **`organization`** (chaque marchand = 1 org/tenant) + **`admin`** (back-office). Conforme à la règle globale `convex-better-auth-setup.md`. |
| **D5** | Login marchand | **v1 = téléphone + OTP WhatsApp** (OTP envoyé via le bridge Baileys existant, coût nul). **Email + mot de passe activable dans les settings** ensuite (les deux coexistent). Plugin `phone` + `emailAndPassword`. |
| **D6** | Modèle org | **v1 = 1 proprio = 1 org**. Plugin `organization` quand même pour le scoping (`activeOrganizationId` dans le JWT). Schéma extensible vers staff multi-membres sans migration. |
| **D7** | Hébergement backend | Plus d'EC2/VPS. Front → Vercel, DB → Convex. **Python + bridge restent à héberger plus tard** (Render free = NON : sleep 15 min tue le socket Baileys + cold start). Cible pressentie : **Oracle Cloud Always Free** (always-on, 4 vCPU / 24 Go, gratuit à vie). **Décision finale reportée.** |
| **D8** | Stratégie ML Python | **Reportée.** Pour l'instant Python tourne **en local** (modèles torch/whisper/CLIP locaux) et pointe sur le **Convex cloud**. Allègement (Whisper → Groq/Deepgram, CLIP → DeepSeek Vision) à décider au moment de l'hébergement. |
| **D9** | Intérim | **Python intégré à Convex dès la phase 1** (réécrit, tourne en local, parle au Convex cloud). Pas d'étape SQLite jetable. Seul l'**hébergement** Python/bridge est reporté. |
| **D10** | Migration données | **Aucune** : KALGA non lancé, données = dev jetable. Schéma Convex propre + **seed démo**. Pas de script SQLite→Convex. |
| **D11** | Périmètre v1 | **Landing + dashboard core + storefront + admin back-office.** Paiement **in-app exclu**. L'abonnement passe par **code d'activation** (admin émet après preuve de paiement manuelle, marchand saisit le code → abonnement actif) — **inclus en v1**. Wave/Orange Money direct = reporté. |
| **D12** | Maquettes | **Références IA par écran** (skill `imagegen-frontend-web`) → validation proprio → code en **shadcn/ui** (React). Règles design : **pas d'AI slop, 1 accent + monochrome, mobile-first, touch ≥ h-11, UI en français, code en anglais, pas d'em dash**. |

---

## Architecture cible

```
                         Convex Cloud (SoT unique)
        ┌──────────────────────────────────────────────────┐
        │  Better Auth (Local Install)   Business tables    │
        │   - users / sessions / accounts   - merchants     │
        │   - organizations / members       - products      │
        │   - phone OTP, email+pwd          - conversations │
        │                                   - messages      │
        │  Convex functions (queries/        - clientHistory│
        │  mutations/actions/scheduler)      - knowledgeBase│
        │  HTTP actions (/api/auth/*)        - followUps ... │
        └───────▲───────────────────────▲──────────────────┘
                │ useQuery/useMutation   │ Convex Python client
                │ + /api/auth/* (proxy)  │ (lecture+écriture)
        ┌───────┴───────────┐    ┌───────┴──────────────────┐
        │ kalga-web         │    │ kalga-api (FastAPI)       │
        │ TanStack Start    │    │  chat ingestion + IA      │
        │ (Vercel)          │    │  (DeepSeek, Whisper, CLIP)│
        │  landing /        │    │  tourne en LOCAL (D8/D9)  │
        │  app. dashboard / │    └───────▲──────────────────┘
        │  {slug}. storefront│           │ POST /api/chat/incoming
        └───────────────────┘    ┌───────┴──────────────────┐
                                  │ kalga-whatsapp (Baileys)  │
                                  │  socket WA + OTP sender    │
                                  │  tourne en LOCAL           │
                                  └────────────────────────────┘
```

**Flux clés**
- Marchand → `app.kalga.app` → Better Auth (OTP WhatsApp) → dashboard lit/écrit Convex en direct.
- Client WhatsApp → bridge → `POST /api/chat/incoming` (FastAPI, **protégé par `INTERNAL_API_KEY`**) → IA → **écrit dans Convex** (pas SQLite) → dashboard voit le message en live.
- Visiteur → `{slug}.kalga.app` → SSR TanStack Start → lit le catalogue depuis Convex (résolution tenant par hostname).
- Admin → `app.kalga.app/admin` → émet codes d'activation, gère marchands, audit.

**Intégration Python↔Convex (principe directeur, détaillé dans 004)** : ne PAS porter les 13
repos SQLite en 13 appels fins (N round-trips réseau sur le hot path IA). Définir un **petit
jeu de fonctions Convex grossières** (ex. `chat.recordTurn`, `inventory.checkProduct`,
`memory.upsert`) que Python appelle. Les opérations multi-écritures deviennent **atomiques**
côté Convex (résout nativement les races, cf. audit #7).

---

## Disposition des findings d'audit (commit `1e28bf5`)

L'audit `quick` est conservé et **résolu par la migration**, pas oublié :

| Finding audit | Sévérité | Disposition dans la migration |
|---|---|---|
| SEC-01 mutations marchand/produit sans auth (IDOR) | HIGH | **Dissous** : toutes les écritures passent par des mutations Convex scoptées org (`withOrg`). La surface FastAPI non-auth disparaît. → plan **003/006**. |
| SEC-02 `debug_token` rendu sur `/forgot-password` | HIGH | **Supprimé** : reset géré par Better Auth, la route FastAPI part. → **003**. |
| SEC-03 conversations lisibles par téléphone (IDOR) | HIGH | **Dissous** : lecture via Convex scopée org. → **003/006**. |
| `/api/chat/incoming` non authentifié | HIGH | **Verrouillé** : on garde l'endpoint (ingestion bridge→API) mais on **exige `INTERNAL_API_KEY`**. → **004**. |
| SEC-04 CORS wildcard si debug | MED | `debug=false` en prod + origines explicites Vercel/Convex. → **004/009**. |
| SEC-05 import CSV sans limite (DoS) | HIGH | Import déplacé en action Convex (ou route auth) **avec cap de taille**. → **006/008**. |
| #5 double moteur dialogue v1/v2 actif | HIGH | **Tranché** : on garde **v2**, on supprime le fallback v1. → **004**. |
| #6 zéro test d'intégration ChatService | HIGH | Tests d'intégration sur le chemin Convex-backed. → **004**. |
| #7 race condition scheduler follow-up | HIGH | Réécrit en **mutation/scheduler Convex atomique**. → **004**. |
| #8 god files intent.py / chat_service.py | HIGH | Allégés opportunément lors de l'extraction stockage. → **004**. |
| Quick wins (bcrypt dupliqué, `merchant_commands.py.backup`, `except: pass`) | LOW | Nettoyage. → **004**. |

---

## Hors périmètre (explicitement reporté)

- Paiement in-app Wave / Orange Money (reste manuel via code d'activation).
- Hébergement final + allègement ML du Python (D7/D8).
- Sous-domaines custom par marchand (`boutique-x.com`) — v1 = `{slug}.kalga.app`.
- Staff multi-membres par org (schéma prévu, UI plus tard).
