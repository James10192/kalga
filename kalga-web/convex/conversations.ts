import { query } from "./_generated/server";
import { v } from "convex/values";

/**
 * Lectures de base sur les conversations et messages (read-only, plan 002),
 * scopées par marchand.
 */

/** Liste les conversations d'un marchand (scoping tenant via index by_merchant). */
export const listByMerchant = query({
  args: { merchantId: v.id("merchants") },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("conversations")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
  },
});

/** Liste les messages d'une conversation, dans l'ordre de création. */
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
