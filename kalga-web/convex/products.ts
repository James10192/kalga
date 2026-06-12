import { query } from "./_generated/server";
import { v } from "convex/values";

/**
 * Lectures de base sur les produits (read-only, plan 002), scopées par marchand.
 */

/** Liste les produits d'un marchand (scoping tenant via index by_merchant). */
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
