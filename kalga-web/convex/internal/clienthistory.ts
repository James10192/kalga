import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts` — fonctions publiques gardées par
// l'argument secret `internalKey` (server-to-server Python sans deploy key).

/**
 * Fonctions internes historique client NON hot-path (backend Python).
 * Parité `client_history_repo` côté lecture + upsert générique. Les écritures
 * mémoire dédiées (faits/résumés/préférences) passent par
 * `internal/memory:upsertMemory` ; l'enregistrement d'achat hot-path passe par
 * `internal/chat:recordSale`. Ici : get_client_history, create_or_update
 * générique (record_conversation), get_top_clients, et les reads JSON
 * (get_memory_facts/get_conversation_summaries/get_preferences se déduisent du
 * doc renvoyé par `get`).
 *
 * Les champs JSON (preferred_categories, memory_facts, conversation_summaries,
 * preferences) sont renvoyés en string brut ; Python les parse comme avec SQLite.
 */

const HISTORY_FIELDS = new Set([
  "totalConversations",
  "totalPurchases",
  "totalSpent",
  "avgNegotiationDiscount",
  "lastPurchaseDate",
  "lastInteractionDate",
  "preferredCategories",
  "negotiationStyle",
  "notes",
  "memoryFacts",
  "lastSessionSummary",
  "preferences",
  "conversationSummaries",
]);

/** Doc clientHistory -> dict snake_case (parité `get_client_history`). */
function toDict(h: any) {
  return {
    id: h._id,
    merchant_id: h.merchantId,
    client_phone: h.clientPhone,
    total_conversations: h.totalConversations ?? 0,
    total_purchases: h.totalPurchases ?? 0,
    total_spent: h.totalSpent ?? 0,
    avg_negotiation_discount: h.avgNegotiationDiscount ?? 0,
    negotiation_style: h.negotiationStyle ?? "normal",
    last_purchase_date: h.lastPurchaseDate ?? null,
    last_interaction_date: h.lastInteractionDate ?? null,
    preferred_categories: h.preferredCategories ?? null,
    memory_facts: h.memoryFacts ?? null,
    conversation_summaries: h.conversationSummaries ?? null,
    last_session_summary: h.lastSessionSummary ?? null,
    preferences: h.preferences ?? null,
    notes: h.notes ?? null,
    updated_at: h.updatedAt ?? h._creationTime,
  };
}

/** Historique d'un client (parité `get_client_history`). */
export const get = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    clientPhone: v.string(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const h = await ctx.db
      .query("clientHistory")
      .withIndex("by_merchant_client", (q) =>
        q.eq("merchantId", args.merchantId).eq("clientPhone", args.clientPhone),
      )
      .unique();
    return h ? toDict(h) : null;
  },
});

/**
 * Crée ou met à jour l'historique d'un client (parité `create_or_update`).
 * `patch` = champs camelCase (l'adaptateur Python convertit). À la création,
 * les défauts (total_conversations=1 etc.) sont posés par Python dans le patch.
 */
export const createOrUpdate = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    clientPhone: v.string(),
    patch: v.any(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const raw = (args.patch ?? {}) as Record<string, unknown>;
    const clean: Record<string, unknown> = {};
    for (const [k, val] of Object.entries(raw)) {
      if (HISTORY_FIELDS.has(k) && val !== undefined && val !== null)
        clean[k] = val;
    }

    const existing = await ctx.db
      .query("clientHistory")
      .withIndex("by_merchant_client", (q) =>
        q.eq("merchantId", args.merchantId).eq("clientPhone", args.clientPhone),
      )
      .unique();

    if (existing) {
      await ctx.db.patch(existing._id, { ...clean, updatedAt: Date.now() });
      return toDict((await ctx.db.get(existing._id))!);
    }
    const id = await ctx.db.insert("clientHistory", {
      merchantId: args.merchantId,
      clientPhone: args.clientPhone,
      ...clean,
      updatedAt: Date.now(),
    });
    return toDict((await ctx.db.get(id))!);
  },
});

/** Meilleurs clients par total dépensé (parité `get_top_clients`). */
export const getTopClients = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const rows = await ctx.db
      .query("clientHistory")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    rows.sort((a, b) => (b.totalSpent ?? 0) - (a.totalSpent ?? 0));
    return rows.slice(0, args.limit ?? 10).map(toDict);
  },
});
