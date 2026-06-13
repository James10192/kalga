import { query } from "./_generated/server";
import { v } from "convex/values";
import { withOrg } from "./lib/withOrg";

/**
 * Lectures de base sur les conversations et messages (read-only, plan 002),
 * scopées par marchand.
 */

/**
 * Liste les conversations du marchand courant, scopée via withOrg (anti-fuite :
 * aucun `merchantId` venant du client). Consommée par `/app/conversations`.
 */
export const listForCurrentMerchant = query({
  args: {},
  handler: async (ctx) =>
    withOrg(ctx, async (octx) =>
      octx.db
        .query("conversations")
        .withIndex("by_merchant", (q) => q.eq("merchantId", octx.merchantId))
        .collect(),
    ),
});

/**
 * Liste les conversations d'un marchand (scoping tenant via index by_merchant).
 *
 * @deprecated Variante paramétrée par `merchantId` (pas de scoping auth) —
 * conservée pour compat ; le dashboard `/app` utilise `listForCurrentMerchant`.
 */
export const listByMerchant = query({
  args: { merchantId: v.id("merchants") },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("conversations")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
  },
});

/**
 * Liste les messages d'une conversation, dans l'ordre de création.
 *
 * @deprecated Pas de scoping auth ; le dashboard `/app` utilise
 * `messagesForCurrentMerchant` (withOrg + vérification d'appartenance au tenant).
 */
export const messagesByConversation = query({
  args: { conversationId: v.id("conversations") },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("messages")
      .withIndex("by_conversation", (q) =>
        q.eq("conversationId", args.conversationId),
      )
      .collect();
  },
});

/**
 * Messages d'une conversation, scopés au marchand courant via withOrg.
 * Vérifie que la conversation appartient bien au tenant (anti-fuite) ; renvoie
 * une liste vide sinon. Consommée par `/app/conversations/$id`.
 */
export const messagesForCurrentMerchant = query({
  args: { conversationId: v.id("conversations") },
  handler: async (ctx, args) =>
    withOrg(ctx, async (octx) => {
      const conversation = await octx.db.get(args.conversationId);
      if (!conversation || conversation.merchantId !== octx.merchantId) {
        return [];
      }
      return await octx.db
        .query("messages")
        .withIndex("by_conversation", (q) =>
          q.eq("conversationId", args.conversationId),
        )
        .collect();
    }),
});

/**
 * Contexte "affaire" d'une conversation pour l'écran Détail (plan 006, read-only).
 *
 * Renvoie en un seul round-trip tout ce que le panneau négociation a besoin :
 * la conversation, son client, et le produit en jeu (prix demandé + prix
 * plancher = `minPrice`). La marge se calcule côté client (offre - plancher).
 *
 * Renvoie `null` si la conversation est introuvable (id invalide / supprimée),
 * pour que la route affiche un état vide soigné plutôt que de crasher.
 *
 * NB : pas d'auth gating ici (l'OTP live + withOrg viendront en 003/004). La
 * signature `{ conversationId }` se rebranchera derrière withOrg sans casser
 * le contrat de lecture (vérifier alors que la conv appartient bien au tenant).
 *
 * @deprecated Pas de scoping auth ; le dashboard `/app` utilise
 * `dealForCurrentMerchant` (withOrg + vérification d'appartenance au tenant).
 */
export const dealForConversation = query({
  args: { conversationId: v.id("conversations") },
  handler: async (ctx, args) => {
    const conversation = await ctx.db.get(args.conversationId);
    if (!conversation) return null;

    const product = await ctx.db.get(conversation.productId);

    return {
      conversationId: conversation._id,
      clientPhone: conversation.clientPhone,
      status: conversation.status,
      currentOffer: conversation.currentOffer ?? null,
      updatedAt: conversation.updatedAt ?? conversation._creationTime,
      product: product
        ? {
            productId: product._id,
            name: product.name,
            code: product.code,
            // prix demandé (affiché) et prix plancher (négo, jamais montré au client).
            price: product.price,
            minPrice: product.minPrice,
          }
        : null,
    };
  },
});

/**
 * Contexte "affaire" d'une conversation, scopé au marchand courant via withOrg.
 * Vérifie que la conversation appartient bien au tenant (anti-fuite cross-tenant)
 * et renvoie `null` sinon (id invalide, supprimée, ou d'un autre marchand).
 * Consommée par `/app/conversations/$id`.
 */
export const dealForCurrentMerchant = query({
  args: { conversationId: v.id("conversations") },
  handler: async (ctx, args) =>
    withOrg(ctx, async (octx) => {
      const conversation = await octx.db.get(args.conversationId);
      if (!conversation || conversation.merchantId !== octx.merchantId) {
        return null;
      }

      const product = await octx.db.get(conversation.productId);

      return {
        conversationId: conversation._id,
        clientPhone: conversation.clientPhone,
        status: conversation.status,
        currentOffer: conversation.currentOffer ?? null,
        updatedAt: conversation.updatedAt ?? conversation._creationTime,
        product: product
          ? {
              productId: product._id,
              name: product.name,
              code: product.code,
              price: product.price,
              minPrice: product.minPrice,
            }
          : null,
      };
    }),
});
