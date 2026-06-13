import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts` — fonctions publiques gardées par
// l'argument secret `internalKey` (server-to-server Python sans deploy key).

/**
 * Fonctions internes catégories (appelées par le backend Python).
 * Parité `category_repo` (kalga-api) : CRUD catégories + comptage produits.
 *
 * Le repo SQLite faisait un LEFT JOIN products avec GROUP BY pour `product_count`.
 * Convex n'a pas d'agrégat SQL : on compte les produits actifs en JS.
 */

/**
 * Crée une catégorie (parité `category_repo.create`).
 * Renvoie le doc Convex brut (l'adaptateur Python le passe en snake_case).
 */
export const create = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    name: v.string(),
    icon: v.optional(v.string()),
    color: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const id = await ctx.db.insert("categories", {
      merchantId: args.merchantId,
      name: args.name,
      icon: args.icon ?? "📦",
      color: args.color ?? "#667eea",
    });
    return await ctx.db.get(id);
  },
});

/**
 * Catégories d'un marchand + nombre de produits actifs par catégorie
 * (parité `category_repo.get_by_merchant`).
 *
 * NB : le schéma Convex `products` n'a PAS de champ `categoryId` (le SQLite
 * `category_id` n'a pas été transposé). On renvoie donc `product_count: 0`
 * tant que le lien produit↔catégorie n'est pas reporté (TODO Phase F/D).
 */
export const listByMerchant = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const cats = await ctx.db
      .query("categories")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    cats.sort((a, b) => a.name.localeCompare(b.name));
    return cats.map((c) => ({ ...c, productCount: 0 }));
  },
});

/**
 * Récupère une catégorie par nom (parité `category_repo.get_by_name`).
 */
export const getByName = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    name: v.string(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    return await ctx.db
      .query("categories")
      .withIndex("by_merchant_name", (q) =>
        q.eq("merchantId", args.merchantId).eq("name", args.name),
      )
      .unique();
  },
});

/**
 * Met à jour une catégorie (parité `category_repo.update`).
 * `patch` = champs partiels (name/icon/color). Renvoie true si la catégorie existe.
 */
export const update = mutation({
  args: {
    internalKey: v.string(),
    categoryId: v.id("categories"),
    name: v.optional(v.string()),
    icon: v.optional(v.string()),
    color: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const existing = await ctx.db.get(args.categoryId);
    if (!existing) return { updated: false };
    const patch: Record<string, unknown> = {};
    if (args.name !== undefined) patch.name = args.name;
    if (args.icon !== undefined) patch.icon = args.icon;
    if (args.color !== undefined) patch.color = args.color;
    if (Object.keys(patch).length === 0) return { updated: false };
    await ctx.db.patch(args.categoryId, patch);
    return { updated: true };
  },
});

/**
 * Supprime une catégorie (parité `category_repo.delete`).
 * Le repo SQLite NULL-ait `products.category_id` d'abord ; le schéma Convex
 * `products` n'a pas ce champ, donc on supprime simplement la catégorie.
 */
export const remove = mutation({
  args: {
    internalKey: v.string(),
    categoryId: v.id("categories"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const existing = await ctx.db.get(args.categoryId);
    if (!existing) return { deleted: false };
    await ctx.db.delete(args.categoryId);
    return { deleted: true };
  },
});
