# 009 — Deploiement production sur Vercel

> Statut : preparation + handoff. Aucun deploiement interactif n'a ete lance (necessite
> l'authentification du proprietaire + la configuration DNS). Ce document decrit exactement
> les reglages a appliquer.

## Resume

`kalga-web` est une application TanStack Start (v1.168) servie par Nitro (`nitro/vite`).
Nitro **detecte automatiquement** l'environnement Vercel au build (variable `VERCEL=1`
injectee par la plateforme) et selectionne le preset `vercel` sans aucune configuration
codee en dur. Aucune modification de `vite.config.ts` n'est requise (il porte le fix critique
single-React et ne doit pas etre touche).

- Build verifie en local : `pnpm build` -> exit 0.
- Sortie locale : `.output/server/` (preset `node_server`, pas d'env Vercel presente).
- Sortie sur Vercel : `.vercel/output/` (Build Output API), lue nativement par Vercel.
  C'est le comportement attendu : le meme `vite build` produit une sortie differente
  selon le preset auto-detecte.

Aucun `vercel.json` n'est strictement necessaire : Nitro emet directement le format
Build Output API que Vercel consomme.

---

## a) Reglages exacts du projet Vercel

| Reglage | Valeur |
|---|---|
| Repository | `James10192/kalga` |
| Root Directory | `kalga-web` |
| Framework Preset | `Vite` (ou `Other` ; Nitro gere le serveur via Build Output API) |
| Build Command | `pnpm build` |
| Install Command | `pnpm install` |
| Output Directory | laisser vide / par defaut (Nitro ecrit `.vercel/output`, format Build Output API) |
| Node.js Version | 20.x (defaut Vercel actuel ; compatible) |

Notes :
- Le **Root Directory = `kalga-web`** est indispensable : le monorepo contient aussi
  `kalga-api/` (Python) et `kalga-whatsapp/` (Node Baileys) qui ne sont PAS deployes sur Vercel.
- Ne PAS forcer `NITRO_PRESET`/`SERVER_PRESET` : l'auto-detection Vercel suffit.
- Ne PAS toucher `vite.config.ts` (fix single-React : `dedupe` + `optimizeDeps.include`).

---

## b) Variables d'environnement Vercel (noms uniquement, jamais les valeurs)

A definir dans Project Settings > Environment Variables, scope **Production**
(et Preview si previews souhaitees). Cocher build + runtime.

Cote client (expose au bundle, prefixe `VITE_`) :
- `VITE_CONVEX_URL` — URL du deploiement Convex prod (`https://<deployment>.convex.cloud`)
- `VITE_CONVEX_SITE_URL` — URL `.site` du meme deploiement (`https://<deployment>.convex.site`)
  utilisee par Better Auth (handler HTTP) et le client auth.

Cote serveur (runtime SSR/server handlers uniquement, NON prefixe `VITE_`) :
- `KALGA_WHATSAPP_URL` — URL publique joignable du pont WhatsApp en prod (voir section d).
- `INTERNAL_API_KEY` — secret partage pour les appels serveur-vers-serveur internes.

> Important : ne jamais committer de valeurs. Les saisir uniquement dans l'UI Vercel
> (ou via `vercel env add`). `VITE_*` est inline dans le bundle client : n'y mettre
> que des URLs publiques, jamais de secret. Les secrets (`INTERNAL_API_KEY`) restent
> cote serveur.

Rappel Convex : le deploiement Convex prod doit aussi avoir ses propres env vars
(`BETTER_AUTH_SECRET`, `SITE_URL`, providers OAuth/OTP) definies via
`npx convex env set ... --prod`. Hors scope Vercel mais prerequis du `pnpm build`
si le build push Convex ; sinon executer `npx convex deploy` separement.

---

## c) Etapes manuelles du proprietaire

1. **Authentification + import**
   - `vercel login` (ou via le dashboard web).
   - Importer le repo `James10192/kalga`, definir Root Directory = `kalga-web`.
   - Renseigner les env vars de la section (b).

2. **Premier deploiement**
   - Laisser Vercel builder sur push, OU `vercel --prod` depuis `kalga-web/`.
   - Verifier que la sortie est `.vercel/output` (preset Vercel bien auto-detecte).

3. **Domaine wildcard + apex**
   - Ajouter le domaine apex `kalga.app` au projet.
   - Ajouter le **wildcard** `*.kalga.app` (necessaire pour les boutiques par sous-domaine).
   - Configurer le DNS chez le registrar :
     - apex `kalga.app` -> enregistrement A/ALIAS vers Vercel (selon instructions Vercel).
     - `*.kalga.app` -> CNAME `cname.vercel-dns.com` (valeur exacte fournie par Vercel).
   - Le wildcard `*.kalga.app` permet `{slug}.kalga.app` -> storefront. Le routage tenant
     **par hostname existe deja** (plan 007 : SSR storefront resout le marchand depuis le
     hostname). Aucun code supplementaire n'est requis : il suffit que le wildcard pointe
     vers le projet Vercel.
   - Note SSL : Vercel emet automatiquement les certificats wildcard une fois le DNS valide.

4. **Verification post-deploiement**
   - `https://kalga.app` -> landing.
   - `https://<slug-demo>.kalga.app` -> storefront du marchand correspondant.
   - `/app/*` -> dashboard marchand (auth Better Auth + Convex).

---

## d) Services hors Vercel (pont WhatsApp + Python)

Vercel n'heberge **que** `kalga-web` (frontend SSR + server handlers TanStack Start).
Les services suivants doivent etre heberges separement sur un hote persistant joignable :

- **`kalga-whatsapp/`** (Node + Baileys, port 3001) : connexion WhatsApp persistante
  (session, QR pairing, websockets sortants). Incompatible avec le modele serverless
  de Vercel (pas de process long-running). A heberger sur un VPS / conteneur dedie.
- **`kalga-api/`** (Python FastAPI, port 8001) : le cas echeant pour la partie legacy/IA.
  Idem, hors Vercel.

En prod, `KALGA_WHATSAPP_URL` (section b) **doit pointer vers l'hote public et joignable**
du pont WhatsApp (ex. `https://wa.kalga.app` ou IP/host du VPS), accessible depuis les
server handlers Vercel. Les appels serveur-vers-serveur sont proteges par `INTERNAL_API_KEY`.

> Rappel infra (regle never-build-on-prod) : ne pas builder sur l'hote de prod du pont.
> Vercel gere le build de `kalga-web` en CI ; le pont WhatsApp se deploie via son propre
> flux (artefact + restart), pas via Vercel.

---

## Verification effectuee

- `pnpm build` dans `kalga-web/` : **exit 0**, sortie `.output/server/` en local
  (preset node_server, attendu hors env Vercel).
- Sur Vercel, l'auto-detection produira `.vercel/output` (Build Output API).
- `vite.config.ts` non modifie (fix single-React preserve).
- Aucun `vercel.json` ajoute (non requis : Nitro emet le format Build Output API).
