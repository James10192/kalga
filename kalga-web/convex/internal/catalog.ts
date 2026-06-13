import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import type { Doc } from "../_generated/dataModel";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts` — fonctions publiques gardées par
// l'argument secret `internalKey` (server-to-server Python sans deploy key).

/**
 * Fonctions internes catalogue produits CRUD (appelées par le backend Python).
 * Parité `product_repo` côté NON hot-path (le hot-path lit/écrit via
 * `internal/inventory:*`). Couvre : create, create_variants_batch, update,
 * get_by_id, get_by_code (admin, sans filtre is_available côté get_by_id),
 * get_all_in_group / get_other_variants, deactivate, get_low/out_of_stock.
 *
 * Le BLOB embedding CLIP (`get_all_with_embeddings`/`save_embedding`) RESTE sur
 * SQLite (incompatible round-trip Convex float64<->numpy float32 ; tied D8 ML
 * offload, hors scope 004). Voir rapport Phase E2.
 *
 * `imageEmbedding` n'est JAMAIS renvoyé (parité `_row_to_dict` qui pop embedding).
 */

const PRODUCT_FIELDS = new Set([
  "name",
  "code",
  "price",
  "minPrice",
  "description",
  "imagePath",
  "groupId",
  "variantName",
  "isActive",
  "outOfStockMode",
  "lastStockAlertAt",
  "stockQuantity",
  "lowStockThreshold",
  "isAvailable",
]);

/** Exclut le vecteur embedding du doc renvoyé (parité `_row_to_dict`). */
function stripEmbedding(p: Doc<"products">) {
  const { imageEmbedding: _omit, ...rest } = p;
  return rest;
}

/** Prochain code produit #K00x basé sur le MAX global (parité `get_next_code`). */
async function nextCode(ctx: { db: any }): Promise<string> {
  const all = await ctx.db.query("products").collect();
  let maxNum = 0;
  for (const p of all as Doc<"products">[]) {
    const m = /^#?K(\d+)$/i.exec(p.code);
    if (m) maxNum = Math.max(maxNum, parseInt(m[1], 10));
  }
  const n = maxNum + 1;
  return `#K${String(n).padStart(3, "0")}`;
}

/** Prochain code produit disponible (parité `product_repo.get_next_code`). */
export const getNextCode = query({
  args: { internalKey: v.string() },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    return await nextCode(ctx);
  },
});

/** Produit par id, embedding exclu (parité `product_repo.get_by_id`). */
export const getById = query({
  args: { internalKey: v.string(), productId: v.id("products") },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const p = await ctx.db.get(args.productId);
    return p ? stripEmbedding(p) : null;
  },
});

/** Crée un produit avec code auto-généré (parité `product_repo.create`). */
export const create = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    name: v.string(),
    price: v.number(),
    minPrice: v.number(),
    description: v.optional(v.string()),
    imagePath: v.optional(v.string()),
    groupId: v.optional(v.string()),
    variantName: v.optional(v.string()),
    stockQuantity: v.optional(v.number()),
    lowStockThreshold: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const code = await nextCode(ctx);
    const id = await ctx.db.insert("products", {
      merchantId: args.merchantId,
      name: args.name,
      code,
      price: args.price,
      minPrice: args.minPrice,
      description: args.description,
      imagePath: args.imagePath,
      groupId: args.groupId,
      variantName: args.variantName,
      stockQuantity: args.stockQuantity ?? -1,
      lowStockThreshold: args.lowStockThreshold ?? 5,
      isAvailable: true,
    });
    const created = await ctx.db.get(id);
    return stripEmbedding(created!);
  },
});

/**
 * Crée N variantes partageant prix/groupId dans une transaction atomique
 * (parité `product_repo.create_variants_batch`). Validation stricte des noms.
 */
export const createVariantsBatch = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    baseName: v.string(),
    price: v.number(),
    minPrice: v.number(),
    description: v.optional(v.string()),
    groupId: v.string(),
    variants: v.array(
      v.object({
        variantName: v.string(),
        imagePath: v.optional(v.string()),
      }),
    ),
    stockQuantity: v.optional(v.number()),
    lowStockThreshold: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    if (args.variants.length === 0)
      throw new Error("La liste de variantes ne peut pas être vide");
    for (const vrt of args.variants) {
      if (!vrt.variantName || !vrt.variantName.trim())
        throw new Error("variant_name manquant ou vide dans le lot");
    }

    // Code de base calculé une fois, incrémenté (parité SQLite).
    const all = await ctx.db.query("products").collect();
    let maxNum = 0;
    for (const p of all as Doc<"products">[]) {
      const m = /^#?K(\d+)$/i.exec(p.code);
      if (m) maxNum = Math.max(maxNum, parseInt(m[1], 10));
    }

    const created: Doc<"products">[] = [];
    for (let i = 0; i < args.variants.length; i++) {
      const vrt = args.variants[i];
      const code = `#K${String(maxNum + 1 + i).padStart(3, "0")}`;
      const id = await ctx.db.insert("products", {
        merchantId: args.merchantId,
        name: `${args.baseName} - ${vrt.variantName}`,
        code,
        price: args.price,
        minPrice: args.minPrice,
        description: args.description,
        imagePath: vrt.imagePath,
        groupId: args.groupId,
        variantName: vrt.variantName,
        stockQuantity: args.stockQuantity ?? -1,
        lowStockThreshold: args.lowStockThreshold ?? 5,
        isAvailable: true,
      });
      created.push((await ctx.db.get(id))!);
    }
    return created.map(stripEmbedding);
  },
});

/** Met à jour un produit (parité `product_repo.update`/`update_stock`/`deactivate`). */
export const update = mutation({
  args: {
    internalKey: v.string(),
    productId: v.id("products"),
    patch: v.any(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const existing = await ctx.db.get(args.productId);
    if (!existing) return { updated: false };
    const raw = (args.patch ?? {}) as Record<string, unknown>;
    const clean: Record<string, unknown> = {};
    for (const [k, val] of Object.entries(raw)) {
      if (PRODUCT_FIELDS.has(k) && val !== undefined) clean[k] = val;
    }
    if (Object.keys(clean).length === 0) return { updated: false };
    await ctx.db.patch(args.productId, clean);
    return { updated: true };
  },
});

/** Variantes d'un groupe (parité `get_all_in_group`). `excludeId` -> get_other_variants. */
export const getInGroup = query({
  args: {
    internalKey: v.string(),
    groupId: v.string(),
    excludeId: v.optional(v.id("products")),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    let rows = await ctx.db
      .query("products")
      .withIndex("by_group", (q) => q.eq("groupId", args.groupId))
      .collect();
    rows = rows.filter((p) => p.isAvailable !== false);
    if (args.excludeId) rows = rows.filter((p) => p._id !== args.excludeId);
    rows.sort((a, b) =>
      (a.variantName ?? "").localeCompare(b.variantName ?? ""),
    );
    return rows.map(stripEmbedding);
  },
});

/** Produits en stock bas (parité `get_low_stock_products`). */
export const getLowStock = query({
  args: { internalKey: v.string(), merchantId: v.id("merchants") },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const rows = await ctx.db
      .query("products")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    return rows
      .filter((p) => {
        const q = p.stockQuantity ?? -1;
        const t = p.lowStockThreshold ?? 5;
        return p.isAvailable !== false && q !== -1 && q <= t;
      })
      .sort((a, b) => (a.stockQuantity ?? 0) - (b.stockQuantity ?? 0))
      .map(stripEmbedding);
  },
});

/** Produits en rupture (parité `get_out_of_stock_products`). */
export const getOutOfStock = query({
  args: { internalKey: v.string(), merchantId: v.id("merchants") },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const rows = await ctx.db
      .query("products")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    return rows
      .filter((p) => p.isAvailable !== false && (p.stockQuantity ?? -1) === 0)
      .sort((a, b) => a.name.localeCompare(b.name))
      .map(stripEmbedding);
  },
});
