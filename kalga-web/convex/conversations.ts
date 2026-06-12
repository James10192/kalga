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
