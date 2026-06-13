import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts` — fonctions publiques gardées par
// l'argument secret `internalKey` (server-to-server Python sans deploy key).

/**
 * Fonctions internes codes d'activation (appelées par le backend Python).
 * Parité `activation_repo` (kalga-api).
 *
 * La génération du code (KALG + 4 alphanum) reste côté Python ; Convex valide
 * l'unicité et insère atomiquement (`createCode`), invalidant les pending
 * précédents dans la même transaction.
 *
 * NB `admin_email` : le repo SQLite LEFT JOIN-ait `users` pour l'email de l'admin
 * créateur. La table `users` n'existe plus (Better Auth, plan 003) — `createdBy`
 * est désormais un user id Better Auth (string). On renvoie `admin_email: null`
 * (l'UI admin résout l'email via Better Auth si besoin). Voir rapport Phase E2.
 */

/**
 * Crée un code d'activation (parité `activation_repo.create_code`).
 * Invalide les codes pending précédents du marchand. Le `code` (déjà généré +
 * vérifié unique côté Python via `isCodeTaken`) est inséré atomiquement.
 */
export const createCode = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    code: v.string(),
    expiresAt: v.number(),
    createdBy: v.string(), // user id Better Auth (string)
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    // Invalider les codes pending précédents (parité UPDATE ... status='expired').
    const pendings = await ctx.db
      .query("activationCodes")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .filter((q) => q.eq(q.field("status"), "pending"))
      .collect();
    for (const p of pendings) {
      await ctx.db.patch(p._id, { status: "expired" });
    }

    const id = await ctx.db.insert("activationCodes", {
      merchantId: args.merchantId,
      code: args.code,
      status: "pending",
      expiresAt: args.expiresAt,
      createdBy: args.createdBy,
    });
    return {
      id,
      code: args.code,
      expires_at: args.expiresAt,
      merchant_id: args.merchantId,
    };
  },
});

/** Vérifie si un code est déjà pris (unicité, parité boucle `_generate_code`). */
export const isCodeTaken = query({
  args: {
    internalKey: v.string(),
    code: v.string(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const existing = await ctx.db
      .query("activationCodes")
      .withIndex("by_code", (q) => q.eq("code", args.code))
      .first();
    return existing !== null;
  },
});

/**
 * Valide un code d'activation (parité `activation_repo.validate_code`).
 * `nowMs` fourni par Python (vérif expiration). Marque 'used' si succès,
 * 'expired' si dépassé. Renvoie {success, message, merchant_id?}.
 */
export const validateCode = mutation({
  args: {
    internalKey: v.string(),
    code: v.string(),
    merchantPhone: v.string(),
    nowMs: v.number(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const row = await ctx.db
      .query("activationCodes")
      .withIndex("by_code", (q) => q.eq("code", args.code.toUpperCase()))
      .filter((q) => q.eq(q.field("status"), "pending"))
      .first();

    if (!row) {
      return { success: false, message: "Code invalide ou déjà utilisé" };
    }

    const merchant = await ctx.db.get(row.merchantId);
    if (!merchant || merchant.phone !== args.merchantPhone) {
      return {
        success: false,
        message: "Ce code n'est pas associé à votre numéro",
      };
    }

    if (row.expiresAt != null && args.nowMs > row.expiresAt) {
      await ctx.db.patch(row._id, { status: "expired" });
      return { success: false, message: "Code expiré. Contactez le support." };
    }

    await ctx.db.patch(row._id, { status: "used", usedAt: args.nowMs });
    return {
      success: true,
      message: "Code validé avec succès",
      merchant_id: row.merchantId,
    };
  },
});

/** Code d'activation par code + infos marchand (parité `get_by_code`). */
export const getByCode = query({
  args: {
    internalKey: v.string(),
    code: v.string(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const row = await ctx.db
      .query("activationCodes")
      .withIndex("by_code", (q) => q.eq("code", args.code.toUpperCase()))
      .first();
    if (!row) return null;
    const m = await ctx.db.get(row.merchantId);
    return {
      ...row,
      merchant_phone: m?.phone ?? null,
      merchant_name: m?.name ?? null,
    };
  },
});

/** Code pending le plus récent d'un marchand (parité `get_pending_for_merchant`). */
export const getPendingForMerchant = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const pendings = await ctx.db
      .query("activationCodes")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .filter((q) => q.eq(q.field("status"), "pending"))
      .collect();
    pendings.sort((a, b) => b._creationTime - a._creationTime);
    return pendings[0] ?? null;
  },
});

/**
 * Marchands WhatsApp sans abonnement actif (parité `get_pending_merchants`).
 * SQLite : LEFT JOIN subscriptions + subqueries activation_codes. Convex : on
 * collecte tous les marchands et on résout leur sub + dernier code pending en JS.
 */
export const getPendingMerchants = query({
  args: {
    internalKey: v.string(),
    nowMs: v.number(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const merchants = await ctx.db.query("merchants").collect();
    const out = [];
    for (const m of merchants) {
      const sub = await ctx.db
        .query("subscriptions")
        .withIndex("by_merchant", (q) => q.eq("merchantId", m._id))
        .unique();
      const inactive =
        !sub ||
        sub.status !== "active" ||
        (sub.plan === "trial" && (sub.trialEndsAt ?? Infinity) < args.nowMs);
      if (!inactive) continue;

      const pendings = await ctx.db
        .query("activationCodes")
        .withIndex("by_merchant", (q) => q.eq("merchantId", m._id))
        .filter((q) => q.eq(q.field("status"), "pending"))
        .collect();
      pendings.sort((a, b) => b._creationTime - a._creationTime);
      const latest = pendings[0];
      out.push({
        id: m._id,
        phone: m.phone,
        name: m.name,
        business_name: m.businessName ?? null,
        created_at: m._creationTime,
        subscription_status: sub?.status ?? null,
        subscription_plan: sub?.plan ?? null,
        pending_code_sent_at: latest?._creationTime ?? null,
        pending_code: latest?.code ?? null,
      });
    }
    out.sort((a, b) => b.created_at - a.created_at);
    return out;
  },
});

/** Expire les codes pending dépassés (parité `expire_old_codes`). `nowMs` = Python. */
export const expireOldCodes = mutation({
  args: {
    internalKey: v.string(),
    nowMs: v.number(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const pendings = await ctx.db
      .query("activationCodes")
      .withIndex("by_status", (q) => q.eq("status", "pending"))
      .collect();
    let count = 0;
    for (const p of pendings) {
      if (p.expiresAt != null && p.expiresAt < args.nowMs) {
        await ctx.db.patch(p._id, { status: "expired" });
        count += 1;
      }
    }
    return { expired: count };
  },
});

/**
 * Historique des activations (parité `get_activation_history`).
 * `admin_email` = null (table users supprimée — cf. note d'entête).
 */
export const getActivationHistory = query({
  args: {
    internalKey: v.string(),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const all = await ctx.db.query("activationCodes").collect();
    all.sort((a, b) => b._creationTime - a._creationTime);
    const sliced = all.slice(0, args.limit ?? 50);
    return await Promise.all(
      sliced.map(async (ac) => {
        const m = await ctx.db.get(ac.merchantId);
        return {
          ...ac,
          merchant_phone: m?.phone ?? null,
          merchant_name: m?.name ?? null,
          admin_email: null,
        };
      }),
    );
  },
});
