import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts` — fonctions publiques gardées par
// l'argument secret `internalKey` (server-to-server Python sans deploy key).

/**
 * Fonctions internes commandes vitrine (appelées par le backend Python).
 * Parité `storefront_order_repo` (kalga-api).
 *
 * Le repo SQLite faisait un JOIN products pour enrichir chaque commande de
 * `product_name`, `product_code`, `price`. Convex n'a pas de JOIN : on fait le
 * lookup produit en JS et on aplatit les champs dans le même dict (parité shape).
 */

/**
 * Crée une commande vitrine (parité `storefront_order_repo.create`).
 * `status` initial = 'new'. Renvoie le doc créé (l'appelant lit `_id`).
 */
export const createOrder = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    productId: v.id("products"),
    clientName: v.string(),
    clientPhone: v.string(),
    message: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const id = await ctx.db.insert("storefrontOrders", {
      merchantId: args.merchantId,
      productId: args.productId,
      clientName: args.clientName,
      clientPhone: args.clientPhone,
      message: args.message,
      status: "new",
    });
    return await ctx.db.get(id);
  },
});

/**
 * Commandes d'un marchand, enrichies des infos produit
 * (parité `storefront_order_repo.get_by_merchant`).
 * Filtre optionnel par `status`. Tri par ancienneté décroissante.
 */
export const listByMerchant = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    status: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    let orders = await ctx.db
      .query("storefrontOrders")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    if (args.status) orders = orders.filter((o) => o.status === args.status);
    orders.sort((a, b) => b._creationTime - a._creationTime);

    return await Promise.all(
      orders.map(async (o) => {
        const p = await ctx.db.get(o.productId);
        return {
          ...o,
          productName: p?.name ?? null,
          productCode: p?.code ?? null,
          price: p?.price ?? null,
        };
      }),
    );
  },
});

/**
 * Met à jour le statut d'une commande (parité `storefront_order_repo.update_status`).
 */
export const updateStatus = mutation({
  args: {
    internalKey: v.string(),
    orderId: v.id("storefrontOrders"),
    status: v.string(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const existing = await ctx.db.get(args.orderId);
    if (!existing) return { updated: false };
    await ctx.db.patch(args.orderId, { status: args.status });
    return { updated: true };
  },
});
