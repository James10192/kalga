import { mutation, query } from "./_generated/server";
import { v, ConvexError } from "convex/values";
import type { Doc, Id } from "./_generated/dataModel";

/**
 * Back-office ADMIN KALGA (plan 008) — équipe KALGA, pas le marchand.
 *
 * Surface dense, desktop-leaning. Trois besoins :
 *  1. lister TOUS les marchands (nom, slug, statut abonnement, statut WhatsApp) ;
 *  2. émettre un CODE D'ACTIVATION `pending` pour un marchand ;
 *  3. consulter le journal d'audit (`adminAuditLogs`).
 *
 * Scoping / gating (mode démo) :
 *  - On est en mode démo : pas d'auth gating réel encore (expectAuth=false).
 *  - Le plugin admin Better Auth gatera ces fonctions plus tard (rôle `admin`).
 *    Le point d'entrée du gating est `assertAdmin()` ci-dessous : aujourd'hui il
 *    laisse passer (parité dev), demain il vérifiera l'identité + le rôle admin.
 *  - Les lectures restent volontairement SCOPEES à la surface admin (liste
 *    globale read-only), jamais d'écriture métier marchand depuis ici hormis
 *    l'émission de code (mutation gardée).
 */

// ───────────────────────────────────────────────────────────────────────────
// Gating admin (placeholder mode démo) — sera branché sur Better Auth admin.
// ───────────────────────────────────────────────────────────────────────────

/**
 * Garde admin. En mode démo (003 pas finalisé), laisse passer et retourne un
 * identifiant d'acteur lisible pour l'audit. Quand le plugin admin Better Auth
 * sera actif, cette fonction vérifiera `ctx.auth.getUserIdentity()` + rôle
 * `admin` et lèvera si non autorisé.
 */
async function assertAdmin(ctx: {
  auth: { getUserIdentity: () => Promise<{ subject: string } | null> };
}): Promise<string> {
  const identity = await ctx.auth.getUserIdentity();
  // TODO(003): exiger identity != null ET rôle "admin" (plugin admin Better Auth).
  return identity?.subject ?? "demo-admin";
}

// ───────────────────────────────────────────────────────────────────────────
// Helpers
// ───────────────────────────────────────────────────────────────────────────

/** Alphabet sans ambiguïté visuelle (pas de 0/O/1/I) pour codes lisibles. */
const CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";

/** Génère un code d'activation de 8 caractères (VARCHAR(8) UNIQUE). */
function randomCode(): string {
  let out = "";
  for (let i = 0; i < 8; i += 1) {
    out += CODE_ALPHABET[Math.floor(Math.random() * CODE_ALPHABET.length)];
  }
  return out;
}

/** Statut d'abonnement projeté pour l'admin (lisible, dérivé du doc). */
type SubProjection = {
  plan: Doc<"subscriptions">["plan"];
  status: Doc<"subscriptions">["status"];
  trialEndsAt: number | null;
  endDate: number | null;
  updatedAt: number;
} | null;

/**
 * Statut WhatsApp par marchand.
 *
 * Le statut réel vit dans le bridge Node (Baileys), pas dans Convex : il n'y a
 * pas de champ de connexion WA sur `merchants`. Tant que la passerelle de
 * statut n'écrit pas dans Convex (plan ultérieur), on renvoie un placeholder
 * neutre `unknown`. L'UI affiche "Non connecté" / placeholder en conséquence.
 */
type WhatsAppStatus = "connected" | "disconnected" | "unknown";

// ───────────────────────────────────────────────────────────────────────────
// 1. listMerchants — liste globale (read-only)
// ───────────────────────────────────────────────────────────────────────────

/**
 * Liste TOUS les marchands avec leur dernier abonnement et un statut WhatsApp.
 *
 * Read-only, gardé admin. Renvoie un tableau plat prêt pour un tableau dense :
 * `{ id, name, slug, phone, businessName, subscription, whatsapp, createdAt }`.
 *
 * Coût : 1 scan `merchants` + 1 lecture d'abonnement par marchand (index
 * `by_merchant`). Volume admin attendu modeste (dizaines/centaines), acceptable.
 */
export const listMerchants = query({
  args: {},
  handler: async (ctx) => {
    await assertAdmin(ctx);

    const merchants = await ctx.db.query("merchants").collect();

    const rows = await Promise.all(
      merchants.map(async (m: Doc<"merchants">) => {
        // Dernier abonnement du marchand (le plus récemment mis à jour).
        const subs = await ctx.db
          .query("subscriptions")
          .withIndex("by_merchant", (q) => q.eq("merchantId", m._id))
          .collect();
        subs.sort(
          (a, b) =>
            (b.updatedAt ?? b._creationTime) - (a.updatedAt ?? a._creationTime),
        );
        const latest = subs[0];
        const subscription: SubProjection = latest
          ? {
              plan: latest.plan,
              status: latest.status,
              trialEndsAt: latest.trialEndsAt ?? null,
              endDate: latest.endDate ?? null,
              updatedAt: latest.updatedAt ?? latest._creationTime,
            }
          : null;

        // Statut WhatsApp : non suivi dans Convex pour l'instant -> placeholder.
        const whatsapp: WhatsAppStatus = "unknown";

        return {
          id: m._id as Id<"merchants">,
          name: m.name,
          slug: m.slug,
          phone: m.phone,
          businessName: m.businessName ?? null,
          subscription,
          whatsapp,
          createdAt: m._creationTime,
        };
      }),
    );

    // Tri : marchands récents en tête.
    rows.sort((a, b) => b.createdAt - a.createdAt);
    return rows;
  },
});

/**
 * Marchands minimaux pour un sélecteur (émission de code).
 * Read-only, gardé admin. `{ id, name, slug }` trié par nom.
 */
export const listMerchantOptions = query({
  args: {},
  handler: async (ctx) => {
    await assertAdmin(ctx);
    const merchants = await ctx.db.query("merchants").collect();
    return merchants
      .map((m) => ({ id: m._id as Id<"merchants">, name: m.name, slug: m.slug }))
      .sort((a, b) => a.name.localeCompare(b.name, "fr"));
  },
});

// ───────────────────────────────────────────────────────────────────────────
// 2. issueActivationCode — émission d'un code pending (mutation gardée)
// ───────────────────────────────────────────────────────────────────────────

/**
 * Émet un code d'activation `pending` pour un marchand.
 *
 * Gardé admin. Génère un code 8 caractères unique (boucle bornée anti-collision),
 * pose une expiration (défaut 30 jours), trace l'action dans `adminAuditLogs`.
 * Renvoie `{ code, expiresAt }`.
 *
 * Le code reste `pending` jusqu'à consommation par le marchand (flow activation
 * marchand, hors de cette surface). On n'invalide pas les codes existants ici :
 * un marchand peut avoir plusieurs codes pending (l'admin décide).
 */
export const issueActivationCode = mutation({
  args: {
    merchantId: v.id("merchants"),
    expiresInDays: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const adminUserId = await assertAdmin(ctx);

    const merchant = await ctx.db.get(args.merchantId);
    if (!merchant) {
      throw new ConvexError({
        code: "NOT_FOUND",
        message: "Marchand introuvable",
      });
    }

    // Code unique : on retente si collision (très improbable, mais sûr).
    let code = randomCode();
    let attempts = 0;
    while (attempts < 20) {
      const clash = await ctx.db
        .query("activationCodes")
        .withIndex("by_code", (q) => q.eq("code", code))
        .unique();
      if (!clash) break;
      code = randomCode();
      attempts += 1;
    }
    if (attempts >= 20) {
      throw new ConvexError({
        code: "INTERNAL",
        message: "Impossible de générer un code unique, réessayez",
      });
    }

    const now = Date.now();
    const days = args.expiresInDays ?? 30;
    const expiresAt = now + days * 24 * 60 * 60 * 1000;

    await ctx.db.insert("activationCodes", {
      merchantId: args.merchantId,
      code,
      status: "pending",
      expiresAt,
      createdBy: adminUserId,
    });

    // Journal d'audit (traçabilité de l'émission).
    await ctx.db.insert("adminAuditLogs", {
      adminUserId,
      action: "issue_activation_code",
      targetType: "merchant",
      targetId: String(args.merchantId),
      details: JSON.stringify({
        code,
        merchantName: merchant.name,
        merchantSlug: merchant.slug,
        expiresAt,
      }),
    });

    return { code, expiresAt };
  },
});

// ───────────────────────────────────────────────────────────────────────────
// 3. auditLogs — journal d'audit (read-only)
// ───────────────────────────────────────────────────────────────────────────

/**
 * Journal d'audit admin, trié par récence décroissante, limité.
 * Read-only, gardé admin. `details` est renvoyé brut (string JSON) — l'UI le
 * parse si elle veut afficher un sous-détail.
 */
export const auditLogs = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    await assertAdmin(ctx);
    const limit = Math.min(args.limit ?? 50, 200);

    // Pas d'index temporel dédié : on scanne puis trie par _creationTime.
    // Volume audit modeste en démo ; un index temporel viendra si nécessaire.
    const logs = await ctx.db.query("adminAuditLogs").collect();
    logs.sort((a, b) => b._creationTime - a._creationTime);

    return logs.slice(0, limit).map((log) => ({
      id: log._id,
      adminUserId: log.adminUserId,
      action: log.action,
      targetType: log.targetType ?? null,
      targetId: log.targetId ?? null,
      details: log.details ?? null,
      ipAddress: log.ipAddress ?? null,
      createdAt: log._creationTime,
    }));
  },
});
