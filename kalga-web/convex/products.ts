import { query } from "./_generated/server";
import { v } from "convex/values";
import { withOrg } from "./lib/withOrg";

/**
 * Lectures de base sur les produits (read-only, plan 002), scopées par marchand.
 */

/**
 * Liste les produits du marchand courant, scopée via withOrg (anti-fuite
 * cross-tenant : aucun `merchantId` venant du client). Consommée par `/app/products`.
 */
export const listForCurrentMerchant = query({
  args: {},
  handler: async (ctx) =>
    withOrg(ctx, async (octx) =>
      octx.db
        .query("products")
        .withIndex("by_merchant", (q) => q.eq("merchantId", octx.merchantId))
        .collect(),
    ),
});

/**
 * Liste les produits d'un marchand (scoping tenant via index by_merchant).
 *
 * @deprecated Variante paramétrée par `merchantId` (pas de scoping auth) —
 * conservée pour compat ; le dashboard `/app` utilise `listForCurrentMerchant`.
 */
export const listByMerchant = query({
  args: { merchantId: v.id("merchants") },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("products")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
  },
});

/** Récupère un produit par son code unique. */
export const getByCode = query({
  args: { code: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("products")
      .withIndex("by_code", (q) => q.eq("code", args.code))
      .unique();
  },
});
