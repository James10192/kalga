import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import type { Doc } from "../_generated/dataModel";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts` — fonctions publiques gardées par
// l'argument secret `internalKey` (server-to-server Python sans deploy key).

/**
 * Fonctions internes conversations NON hot-path (appelées par le backend Python).
 * Parité `conversation_repo` côté lecture dashboard + maintenance. Le hot-path
 * (create/update/add_message/getContext) passe par `internal/chat:*`.
 * Couvre : get_by_merchant, get_pending, get_messages, cleanup_expired.
 * Plus l'insertion de feedback (parité chat.py callsite SQL direct ~ligne 521).
 *
 * Les reads SQLite faisaient un JOIN products -> on aplatit `product_name`,
 * `product_code`, `price` dans le même dict (parité shape dashboard).
 */

const DEAD_STATUSES = new Set(["ended", "completed", "abandoned"]);

/** Aplatit conversation + infos produit (parité dict(row) JOIN products). */
async function withProduct(ctx: { db: any }, c: Doc<"conversations">) {
  const p = await ctx.db.get(c.productId);
  return {
    id: c._id,
    merchant_id: c.merchantId,
    product_id: c.productId,
    client_phone: c.clientPhone,
    status: c.status,
    current_offer: c.currentOffer ?? null,
    selected_variant_id: c.selectedVariantId ?? null,
    updated_at: c.updatedAt ?? c._creationTime,
    product_name: p?.name ?? null,
    product_code: p?.code ?? null,
    price: p?.price ?? null,
  };
}

/**
 * Conversation vivante d'un client (parité `get_active`). Si `productId` fourni,
 * cible ce produit ; sinon la plus récente non-morte. Aplatie + infos produit.
 */
export const getActive = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    clientPhone: v.string(),
    productId: v.optional(v.id("products")),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    let convs = await ctx.db
      .query("conversations")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    convs = convs.filter(
      (c) =>
        c.clientPhone === args.clientPhone && !DEAD_STATUSES.has(c.status),
    );
    if (args.productId)
      convs = convs.filter((c) => c.productId === args.productId);
    convs.sort(
      (a, b) =>
        (b.updatedAt ?? b._creationTime) - (a.updatedAt ?? a._creationTime),
    );
    return convs[0] ? await withProduct(ctx, convs[0]) : null;
  },
});

/** Crée une conversation (parité `conversation_repo.create`). */
export const create = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    productId: v.id("products"),
    clientPhone: v.string(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const id = await ctx.db.insert("conversations", {
      merchantId: args.merchantId,
      productId: args.productId,
      clientPhone: args.clientPhone,
      status: "active",
      updatedAt: Date.now(),
    });
    return await withProduct(ctx, (await ctx.db.get(id))!);
  },
});

/** Met à jour une conversation (parité `conversation_repo.update`). */
export const update = mutation({
  args: {
    internalKey: v.string(),
    conversationId: v.id("conversations"),
    status: v.optional(v.string()),
    currentOffer: v.optional(v.union(v.number(), v.null())),
    selectedVariantId: v.optional(v.id("products")),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const existing = await ctx.db.get(args.conversationId);
    if (!existing) return { updated: false };
    const patch: Record<string, unknown> = { updatedAt: Date.now() };
    if (args.status !== undefined) patch.status = args.status;
    if (args.currentOffer !== undefined)
      patch.currentOffer = args.currentOffer === null ? undefined : args.currentOffer;
    if (args.selectedVariantId !== undefined)
      patch.selectedVariantId = args.selectedVariantId;
    await ctx.db.patch(args.conversationId, patch);
    return { updated: true };
  },
});

/** Ajoute un message + bump updatedAt (parité `conversation_repo.add_message`). */
export const addMessage = mutation({
  args: {
    internalKey: v.string(),
    conversationId: v.id("conversations"),
    content: v.string(),
    isFromClient: v.boolean(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const id = await ctx.db.insert("messages", {
      conversationId: args.conversationId,
      content: args.content,
      isFromClient: args.isFromClient,
    });
    await ctx.db.patch(args.conversationId, { updatedAt: Date.now() });
    const m = (await ctx.db.get(id))!;
    return {
      id: m._id,
      conversation_id: m.conversationId,
      content: m.content,
      is_from_client: m.isFromClient,
      created_at: m._creationTime,
    };
  },
});

/**
 * Conversations d'un marchand par statut (parité `get_by_merchant`).
 * `status` = "all" | "active" (exclut dead) | statut précis. Tri updatedAt desc.
 */
export const getByMerchant = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    status: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const status = args.status ?? "active";
    let convs = await ctx.db
      .query("conversations")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();

    if (status === "active") {
      convs = convs.filter((c) => !DEAD_STATUSES.has(c.status));
    } else if (status !== "all") {
      convs = convs.filter((c) => c.status === status);
    }
    convs.sort(
      (a, b) => (b.updatedAt ?? b._creationTime) - (a.updatedAt ?? a._creationTime),
    );
    return await Promise.all(convs.map((c) => withProduct(ctx, c)));
  },
});

/** Conversations en attente (pending_delivery/pickup, parité `get_pending`). */
export const getPending = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const convs = await ctx.db
      .query("conversations")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    const pending = convs.filter(
      (c) =>
        c.status === "pending_delivery" || c.status === "pending_pickup",
    );
    pending.sort(
      (a, b) => (b.updatedAt ?? b._creationTime) - (a.updatedAt ?? a._creationTime),
    );
    return await Promise.all(pending.map((c) => withProduct(ctx, c)));
  },
});

/** Messages d'une conversation, ordre chronologique (parité `get_messages`). */
export const getMessages = query({
  args: {
    internalKey: v.string(),
    conversationId: v.id("conversations"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const msgs = await ctx.db
      .query("messages")
      .withIndex("by_conversation", (q) =>
        q.eq("conversationId", args.conversationId),
      )
      .collect();
    msgs.sort((a, b) => a._creationTime - b._creationTime);
    return msgs.map((m) => ({
      id: m._id,
      conversation_id: m.conversationId,
      content: m.content,
      is_from_client: m.isFromClient,
      created_at: m._creationTime,
    }));
  },
});

/**
 * Marque expirées les conversations vivantes inactives depuis `cutoffMs`
 * (parité `cleanup_expired` + `db.cleanup_expired_conversations`).
 * `cutoffMs` = epoch ms (now - days) fourni par Python. Renvoie le compte.
 */
export const cleanupExpired = mutation({
  args: {
    internalKey: v.string(),
    cutoffMs: v.number(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    let count = 0;
    for (const status of ["active", "negotiating"] as const) {
      const convs = await ctx.db
        .query("conversations")
        .withIndex("by_status", (q) => q.eq("status", status))
        .collect();
      for (const c of convs) {
        if ((c.updatedAt ?? c._creationTime) < args.cutoffMs) {
          await ctx.db.patch(c._id, { status: "expired" });
          count += 1;
        }
      }
    }
    return { cleaned: count };
  },
});

/**
 * Enregistre un feedback de conversation (parité chat.py INSERT direct
 * conversation_feedback). Renvoie l'id inséré.
 */
export const addFeedback = mutation({
  args: {
    internalKey: v.string(),
    conversationId: v.id("conversations"),
    merchantId: v.id("merchants"),
    clientPhone: v.string(),
    clientMessage: v.string(),
    botResponse: v.string(),
    feedbackType: v.union(
      v.literal("bad_response"),
      v.literal("good_response"),
      v.literal("auto_flagged"),
    ),
    notes: v.optional(v.string()),
    kbEntryId: v.optional(v.id("knowledgeBase")),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const id = await ctx.db.insert("conversationFeedback", {
      conversationId: args.conversationId,
      merchantId: args.merchantId,
      clientPhone: args.clientPhone,
      clientMessage: args.clientMessage,
      botResponse: args.botResponse,
      feedbackType: args.feedbackType,
      notes: args.notes,
      kbEntryId: args.kbEntryId,
    });
    return { feedbackId: id };
  },
});
