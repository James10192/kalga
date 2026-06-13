import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts` — fonctions publiques gardées par
// l'argument secret `internalKey` (server-to-server Python sans deploy key).

/**
 * Fonctions internes marchands CRUD (appelées par le backend Python).
 * Parité `merchant_repo` côté NON hot-path (le hot-path lit via
 * `internal/chat:getContext`). Couvre : get_by_id, get_all (admin),
 * get_total_count, update générique, update_location, update_away_settings,
 * get_away_settings.
 *
 * `update` reçoit un patch déjà en camelCase (l'adaptateur Python convertit
 * les clés snake_case du repo -> camelCase Convex). On valide les champs
 * autorisés pour éviter d'écrire des clés inconnues.
 */

const MERCHANT_FIELDS = new Set([
  "name",
  "phone",
  "slug",
  "businessName",
  "address",
  "latitude",
  "longitude",
  "awayModeEnabled",
  "workingHours",
  "awayMessage",
  "logoPath",
  "about",
  "tagline",
  "bannerPath",
  "botTone",
  "botStyle",
  "botCatchphrase",
  "paymentMethods",
  "stockAlertDays",
  "stockAlertsEnabled",
  "waitlistEnabled",
  "lowStockAlertGlobal",
  "whatsappLinkedAt",
  "whatsappRealPhone",
  "organizationId",
]);

/**
 * Marchand par téléphone, avec fallback numéro ivoirien 225->2250
 * (parité `merchant_repo.get_by_phone` + `resolveMerchant` du hot-path).
 */
export const getByPhone = query({
  args: {
    internalKey: v.string(),
    phone: v.string(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    let m = await ctx.db
      .query("merchants")
      .withIndex("by_phone", (q) => q.eq("phone", args.phone))
      .unique();
    if (!m && args.phone.startsWith("225") && args.phone.length === 12) {
      const corrected = "225" + "0" + args.phone.slice(3);
      m = await ctx.db
        .query("merchants")
        .withIndex("by_phone", (q) => q.eq("phone", corrected))
        .unique();
    }
    // Fallback : le bridge envoie le numero REEL du compte WhatsApp connecte
    // (`sock.user.id`), qui peut differer du `phone` d'inscription
    // (terrain 2026-06-13 : phone=225141540178 mais whatsappRealPhone=22541540178).
    if (!m) {
      m = await ctx.db
        .query("merchants")
        .withIndex("by_whatsapp_real_phone", (q) =>
          q.eq("whatsappRealPhone", args.phone),
        )
        .unique();
    }
    return m;
  },
});

/**
 * Crée un marchand minimal (parité `merchant_repo.create`).
 * `slug` est requis par le schéma : on le dérive du téléphone si non fourni
 * (les marchands "réels" obtiennent leur slug à l'onboarding 003/010).
 */
export const create = mutation({
  args: {
    internalKey: v.string(),
    name: v.string(),
    phone: v.string(),
    businessName: v.optional(v.string()),
    slug: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const slug = args.slug ?? `m-${args.phone}`;
    const id = await ctx.db.insert("merchants", {
      name: args.name,
      phone: args.phone,
      slug,
      businessName: args.businessName,
    });
    return await ctx.db.get(id);
  },
});

/** Marchand par id (parité `merchant_repo.get_by_id`). */
export const getById = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    return await ctx.db.get(args.merchantId);
  },
});

/** Liste paginée des marchands (parité `merchant_repo.get_all`, admin). */
export const getAll = query({
  args: {
    internalKey: v.string(),
    page: v.optional(v.number()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const limit = args.limit ?? 20;
    const offset = ((args.page ?? 1) - 1) * limit;
    const all = await ctx.db.query("merchants").collect();
    all.sort((a, b) => b._creationTime - a._creationTime);
    return all.slice(offset, offset + limit);
  },
});

/** Nombre total de marchands (parité `merchant_repo.get_total_count`). */
export const getTotalCount = query({
  args: { internalKey: v.string() },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const all = await ctx.db.query("merchants").collect();
    return all.length;
  },
});

/**
 * Met à jour un marchand (parité `merchant_repo.update` + `update_location` +
 * `update_away_settings`). `patch` = champs camelCase autorisés.
 * Renvoie true si le marchand existe et au moins un champ a été appliqué.
 */
export const update = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    patch: v.any(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const existing = await ctx.db.get(args.merchantId);
    if (!existing) return { updated: false };

    const raw = (args.patch ?? {}) as Record<string, unknown>;
    const clean: Record<string, unknown> = {};
    for (const [k, val] of Object.entries(raw)) {
      if (MERCHANT_FIELDS.has(k) && val !== undefined) clean[k] = val;
    }
    if (Object.keys(clean).length === 0) return { updated: false };
    await ctx.db.patch(args.merchantId, clean);
    return { updated: true };
  },
});

/**
 * Paramètres mode absence (parité `merchant_repo.get_away_settings`).
 * `workingHours` est renvoyé en string JSON (l'appelant Python le parse).
 */
export const getAwaySettings = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const m = await ctx.db.get(args.merchantId);
    if (!m) return null;
    return {
      away_mode_enabled: m.awayModeEnabled ?? false,
      working_hours: m.workingHours ?? null,
      away_message: m.awayMessage ?? null,
    };
  },
});
