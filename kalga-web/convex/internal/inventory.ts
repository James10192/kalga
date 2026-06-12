import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import type { Doc, Id } from "../_generated/dataModel";
import { assertInternalKey } from "./guard";

/**
 * NB visibilité : ces fonctions sont des `query`/`mutation` PUBLIQUES, MAIS
 * gardées par l'argument secret `internalKey` (validé par `assertInternalKey`
 * contre `process.env.INTERNAL_API_KEY`). On n'utilise pas `internalQuery`/
 * `internalMutation` (visibilité "internal" Convex) car celles-ci exigent une
 * deploy key (`set_admin_auth`) côté client — non disponible pour le backend
 * Python server-to-server. Le secret partagé EST la garde (contrat plan 004).
 */

/**
 * Fonctions internes inventaire (appelées par le backend Python).
 * Remplacent `product_repo` côté hot-path : lookup produit + statut stock,
 * inventaire pour les tools IA, décrément de stock atomique.
 *
 * Grain GROSSIER : on renvoie de gros payloads enrichis (statut stock calculé,
 * marchand rattaché) pour éviter les N round-trips réseau sur le chemin chat.
 */

/** Calcule le statut de stock (parité `product_repo.check_stock_status`). */
function stockStatus(product: Doc<"products">) {
  const quantity = product.stockQuantity ?? -1;
  const threshold = product.lowStockThreshold ?? 5;
  const isUnlimited = quantity === -1;
  return {
    available: isUnlimited || quantity > 0,
    quantity,
    isLow: !isUnlimited && quantity > 0 && quantity <= threshold,
    isOutOfStock: !isUnlimited && quantity === 0,
    isUnlimited,
    threshold,
  };
}

/**
 * Lookup d'un produit par code (parité `product_repo.get_by_code`), enrichi
 * du statut stock et du marchand rattaché. Le BLOB embedding CLIP n'est jamais
 * renvoyé (champ `imageEmbedding` exclu) — parité `_row_to_dict`.
 */
export const checkProduct = query({
  args: {
    internalKey: v.string(),
    code: v.string(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);

    const product = await ctx.db
      .query("products")
      .withIndex("by_code", (q) => q.eq("code", args.code.toUpperCase()))
      .unique();
    if (!product || product.isAvailable === false) return null;

    const merchant = await ctx.db.get(product.merchantId);
    const { imageEmbedding: _omit, ...productPublic } = product;

    return {
      product: productPublic,
      stockStatus: stockStatus(product),
      merchantPhone: merchant?.phone ?? null,
      merchantName: merchant?.name ?? null,
    };
  },
});

/**
 * Inventaire d'un marchand pour les tools IA (parité `product_repo.get_by_merchant`).
 * Produits actifs uniquement, embedding exclu.
 */
export const listProductsForTools = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);

    const products = await ctx.db
      .query("products")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();

    return products
      .filter((p) => p.isAvailable !== false)
      .map((p) => {
        const { imageEmbedding: _omit, ...rest } = p;
        return { ...rest, stockStatus: stockStatus(p) };
      });
  },
});

/**
 * Décrément de stock atomique (parité `product_repo.decrement_stock`).
 * stock illimité (-1) -> no-op. Plancher à 0. Journalise un `stockEvents`
 * (sale + out_of_stock le cas échéant) DANS la même transaction, supprimant
 * la séquence multi-écritures côté Python.
 */
export const decrementStock = mutation({
  args: {
    internalKey: v.string(),
    productId: v.id("products"),
    quantity: v.optional(v.number()),
    conversationId: v.optional(v.id("conversations")),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const qty = args.quantity ?? 1;

    const product = await ctx.db.get(args.productId);
    if (!product) return null;

    const current = product.stockQuantity ?? -1;
    // Stock illimité : pas de décrément, on renvoie le statut courant.
    if (current === -1) {
      return { stockStatus: stockStatus(product), decremented: false };
    }

    const newStock = Math.max(0, current - qty);
    await ctx.db.patch(args.productId, { stockQuantity: newStock });

    const updated = { ...product, stockQuantity: newStock };
    const status = stockStatus(updated);

    // Journal append-only (parité `waitlist.log_stock_event`).
    await ctx.db.insert("stockEvents", {
      merchantId: product.merchantId,
      productId: args.productId,
      eventType: "sale",
      quantityDelta: -qty,
      quantityAfter: newStock,
      conversationId: args.conversationId,
    });
    if (status.isOutOfStock) {
      await ctx.db.insert("stockEvents", {
        merchantId: product.merchantId,
        productId: args.productId,
        eventType: "out_of_stock",
        quantityDelta: 0,
        quantityAfter: 0,
        conversationId: args.conversationId,
      });
    }

    return { stockStatus: status, decremented: true };
  },
});
