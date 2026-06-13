import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import type { Doc } from "../_generated/dataModel";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts` — fonctions publiques gardées par
// l'argument secret `internalKey` (server-to-server Python sans deploy key).

/**
 * Fonctions internes abonnements (appelées par le backend Python).
 * Parité `subscription_repo` (kalga-api). Le doc Convex est renvoyé brut ; la
 * logique de dates / limites reste côté Python (qui possède `datetime.now()`),
 * sauf les écritures atomiques (create_trial / upgrade / increment / reactivate).
 *
 * Dates : SQLite stockait des ISO strings. En Convex on passe des epoch ms
 * (`v.number()`) pour les bornes ; l'adaptateur Python recompose les ISO.
 */

const TRIAL = "trial" as const;
const ACTIVE = "active" as const;
const EXPIRED = "expired" as const;

/** Abonnement d'un marchand (parité `subscription_repo.get_by_merchant`). */
export const getByMerchant = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    return await ctx.db
      .query("subscriptions")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .unique();
  },
});

/** Crée un abonnement trial (parité `subscription_repo.create_trial`). */
export const createTrial = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    startDate: v.number(),
    trialEndsAt: v.number(),
    messagesLimit: v.optional(v.number()),
    productsLimit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const id = await ctx.db.insert("subscriptions", {
      merchantId: args.merchantId,
      plan: TRIAL,
      status: ACTIVE,
      startDate: args.startDate,
      trialEndsAt: args.trialEndsAt,
      messagesLimit: args.messagesLimit ?? 500,
      messagesUsed: 0,
      productsLimit: args.productsLimit ?? 10,
    });
    return await ctx.db.get(id);
  },
});

/** Upgrade un abonnement payant (parité `subscription_repo.upgrade_plan`). */
export const upgradePlan = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    plan: v.union(
      v.literal("starter"),
      v.literal("pro"),
      v.literal("enterprise"),
    ),
    startDate: v.number(),
    endDate: v.number(),
    messagesLimit: v.optional(v.number()),
    productsLimit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const sub = await ctx.db
      .query("subscriptions")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .unique();
    if (!sub) return null;
    await ctx.db.patch(sub._id, {
      plan: args.plan,
      status: ACTIVE,
      startDate: args.startDate,
      endDate: args.endDate,
      trialEndsAt: undefined,
      messagesLimit: args.messagesLimit ?? 5000,
      messagesUsed: 0,
      productsLimit: args.productsLimit ?? 100,
      updatedAt: Date.now(),
    });
    return await ctx.db.get(sub._id);
  },
});

/** Incrémente le compteur de messages utilisés (parité `increment_messages`). */
export const incrementMessages = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const sub = await ctx.db
      .query("subscriptions")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .unique();
    if (!sub) return null;
    await ctx.db.patch(sub._id, {
      messagesUsed: (sub.messagesUsed ?? 0) + 1,
      updatedAt: Date.now(),
    });
    return await ctx.db.get(sub._id);
  },
});

/** Réactive un abonnement existant en trial (parité `reactivate`). */
export const reactivate = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    trialEndsAt: v.number(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const sub = await ctx.db
      .query("subscriptions")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .unique();
    if (sub) {
      await ctx.db.patch(sub._id, {
        status: ACTIVE,
        plan: TRIAL,
        trialEndsAt: args.trialEndsAt,
        messagesUsed: 0,
        updatedAt: Date.now(),
      });
      return await ctx.db.get(sub._id);
    }
    return null;
  },
});

/** Marque comme expirés les abonnements échus (parité `mark_expired`). `nowMs` = Python. */
export const markExpired = mutation({
  args: {
    internalKey: v.string(),
    nowMs: v.number(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const actives = await ctx.db
      .query("subscriptions")
      .withIndex("by_status", (q) => q.eq("status", ACTIVE))
      .collect();
    let count = 0;
    for (const s of actives) {
      const expired =
        (s.plan === TRIAL && (s.trialEndsAt ?? Infinity) < args.nowMs) ||
        (s.plan !== TRIAL && (s.endDate ?? Infinity) < args.nowMs);
      if (expired) {
        await ctx.db.patch(s._id, { status: EXPIRED, updatedAt: Date.now() });
        count += 1;
      }
    }
    return { expired: count };
  },
});

/** Abonnements expirant bientôt + infos marchand (parité `get_expiring_soon`). */
export const getExpiringSoon = query({
  args: {
    internalKey: v.string(),
    nowMs: v.number(),
    thresholdMs: v.number(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const actives = await ctx.db
      .query("subscriptions")
      .withIndex("by_status", (q) => q.eq("status", ACTIVE))
      .collect();
    const matching = actives.filter((s) => {
      const ref = s.plan === TRIAL ? s.trialEndsAt : s.endDate;
      return ref != null && ref >= args.nowMs && ref <= args.thresholdMs;
    });
    matching.sort((a, b) => {
      const ra = (a.plan === TRIAL ? a.trialEndsAt : a.endDate) ?? Infinity;
      const rb = (b.plan === TRIAL ? b.trialEndsAt : b.endDate) ?? Infinity;
      return ra - rb;
    });
    return await Promise.all(
      matching.map(async (s) => {
        const m = await ctx.db.get(s.merchantId);
        return {
          ...s,
          name: m?.name ?? null,
          phone: m?.phone ?? null,
          business_name: m?.businessName ?? null,
        };
      }),
    );
  },
});

/** Statistiques globales abonnements (parité `get_stats`). Agrégat JS. */
export const getStats = query({
  args: { internalKey: v.string() },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const all = await ctx.db.query("subscriptions").collect();
    const by = (pred: (s: Doc<"subscriptions">) => boolean) =>
      all.filter(pred).length;
    const totalUsed = all.reduce((acc, s) => acc + (s.messagesUsed ?? 0), 0);
    return {
      total: all.length,
      active: by((s) => s.status === ACTIVE),
      expired: by((s) => s.status === EXPIRED),
      trials: by((s) => s.plan === TRIAL),
      starter: by((s) => s.plan === "starter"),
      pro: by((s) => s.plan === "pro"),
      enterprise: by((s) => s.plan === "enterprise"),
      avg_messages_used: all.length ? totalUsed / all.length : 0,
    };
  },
});
