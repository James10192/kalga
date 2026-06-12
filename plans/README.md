# Plans de migration KALGA → TanStack Start + Convex

Généré le 2026-06-11 (skill `improve` + grill, commit `1e28bf5`).
Lire **`000-decisions-and-architecture.md`** d'abord — il verrouille les décisions et
la cible. Exécuter dans l'ordre ci-dessous sauf indication des dépendances.

## Ordre d'exécution & statut

| Plan | Titre | Prio | Effort | Dépend de | Statut |
|------|-------|------|--------|-----------|--------|
| 000 | Décisions & architecture (ADR, référence) | — | — | — | DONE |
| 001 | Scaffold `kalga-web` (TanStack Start) + init Convex + Vercel-ready | P1 | M | — | DONE |
| 002 | Schéma Convex (tables métier) + seed démo + queries de base | P1 | L | 001 | DONE (17 tables + 38 index + seed idempotent + queries lecture ; dev `rugged-albatross-514`) |
| 003 | Better Auth Local Install (OTP WhatsApp, org+admin, email/pwd opt-in) | P1 | L | 001, 002 | PARTIAL (GATE-2 : code complet, test OTP live bloqué par session émettrice + `KALGA_OTP_SENDER_PHONE`) |
| 004 | Réécriture Python → Convex (client, fonctions grossières, v2 only, audit) | P1 | L | 002 | PARTIAL (fonctions Convex + client Python + verrou /incoming + quick wins + 7 tests OK ; reste : bascule hot-path writes, suppression v1, retrait SQLite — gate humain) |
| 005 | Références design IA par écran (gate UI) | P2 | M | — (parallèle) | REJECTED (design non validé, à refaire via /ultrathink) |
| 006 | Dashboard marchand (produits, conversations live, stock, settings, activation) | P1 | L | 003, 004, 005 | TODO |
| 007 | Storefront public `{slug}.kalga.app` (SSR, résolution tenant par hostname) | P2 | M | 002, 005 | TODO |
| 008 | Admin back-office (marchands, émission codes, audit, statut WA) | P2 | M | 003, 005 | TODO |
| 009 | Déploiement prod Vercel (domaine wildcard, env, CI off-prod) | P1 | M | 006, 007, 008 | TODO |

Statuts : TODO · IN PROGRESS · DONE · BLOCKED (raison) · REJECTED (raison).

> **État de rédaction** : `000`–`004` sont rédigés en détail exécutable (step-tasks
> granulaires, `acceptance_criteria` vérifiables). `005` (design) est **rejeté, à refaire**
> (via `/ultrathink`). `006`–`009` sont cadrés ci-dessous (scope + dépendances) et seront
> développés en fichiers complets **au fur et à mesure qu'on les atteint**.
> Demander « développe le plan 00X » pour l'étendre.
>
> **État d'exécution réel (2026-06-12)** : 001 = DONE, 002 = DONE, 003 = PARTIAL (GATE-2),
> 004 = PARTIAL (gate humain bascule write-path), 005 = REJECTED, 006-009 = TODO. Voir la
> colonne Statut ci-dessus et `REFERENCE.md` §6 pour les gates restants à remonter au proprio.

## Notes de dépendances

- **001 avant tout** : `convex/` vit dans `kalga-web/`, donc le scaffold précède le schéma.
- **004 dépend de 002 seulement** (pas de 003) : Python parle à Convex via une **clé de
  déploiement / fonctions internes**, pas via une session Better Auth utilisateur. Peut donc
  avancer en parallèle de l'auth front.
- **003 et 004 sont parallélisables** une fois 002 fait (auth front ⟂ rewrite Python).
- **005 (design) est parallèle** et bloque 006/007/008 (on code l'UI après validation visuelle).
- **009 en dernier** : déploie ce qui existe ; le backend Python/bridge n'y va pas (D7).

## Cadrage des plans 003–009 (à développer à l'approche)

- **003 — Better Auth** : `@convex-dev/better-auth` en **Local Install** (doc ctx7
  `/websites/labs_convex_dev_better-auth`). Plugins `organization` (creatorRole owner,
  1 org/marchand) + `admin` + `phone` (sender = bridge WhatsApp `kalga-whatsapp`, envoie
  l'OTP) + `emailAndPassword` (opt-in settings). `definePayload` injecte
  `activeOrganizationId` dans le JWT. Helper `withOrg`. **Fallback OTP** (bridge down) à
  trancher : email OTP de secours. Mappe SEC-02 (reset géré par Better Auth).
- **004 — Python → Convex** : client Python `convex` ; définir **fonctions grossières**
  (`chat.recordTurn`, `inventory.checkProduct`, `merchant.getPersona`, `memory.upsert`,
  `followups.schedule`) ; **supprimer le moteur v1** (garder v2, cf. audit #5/#6) ;
  réécrire le scheduler follow-up en **scheduler Convex** (audit #7) ; **verrouiller
  `/api/chat/incoming` avec `INTERNAL_API_KEY`** ; nettoyer quick wins (bcrypt, `.backup`,
  `except: pass`) ; tests d'intégration du chemin Convex.
- **005 — Design** : générer références par écran (landing, dashboard home, détail
  conversation, gestion produits, storefront, admin). Valider avec le proprio. Établir
  tokens shadcn/ui (1 accent + monochrome). Gate pour 006/007/008.
- **006 — Dashboard marchand** (`app.kalga.app`) : produits CRUD, **conversations live**
  (`useQuery` Convex), stock, settings (incl. ajout email+pwd), saisie **code d'activation**.
  Providers Convex/Better Auth scopés à `/app/*` (règle `tanstack-start-vite-gotchas`).
- **007 — Storefront** (`{slug}.kalga.app`) : SSR, résolution tenant par **hostname** dans
  le loader racine ; sous-domaines réservés blacklistés (`app`, `www`, `api`, `admin`) ;
  catalogue + commande (table `storefront_orders`) ; **pas** de provider auth (page publique).
- **008 — Admin** (`app.kalga.app/admin`, plugin `admin`) : liste marchands, **émission codes
  d'activation**, audit logs, statut WhatsApp par marchand. Import CSV avec cap taille (SEC-05).
- **009 — Vercel** : projet unique, **domaine wildcard `*.kalga.app`** + apex + `app.`, env
  Convex (`VITE_CONVEX_URL`, `VITE_CONVEX_SITE_URL`), `SITE_URL`/`BETTER_AUTH_SECRET` côté
  Convex, `debug=false`, origines CORS explicites (SEC-04). Build **off-prod** (CI Vercel).

## Findings d'audit considérés et conservés

Tous les findings de l'audit `quick` (commit `1e28bf5`) sont **mappés** dans
`000-decisions-and-architecture.md` § « Disposition des findings d'audit ». Aucun
n'est rejeté : la nouvelle architecture les dissout ou ils sont fixés dans 004/006/008/009.
