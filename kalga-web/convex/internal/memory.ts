import { mutation } from "../_generated/server";
import { v } from "convex/values";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts` — fonctions publiques gardées par
// l'argument secret `internalKey` (server-to-server Python sans deploy key).

/**
 * Fonctions internes mémoire (appelées par le backend Python).
 * Remplacent `client_history_repo` (LTM/épisodique) + `knowledge_repo` côté
 * écriture. Grain grossier : un seul appel persiste l'ensemble des faits
 * mémoire d'un client OU une entrée de base de connaissances.
 */

/**
 * Upsert des faits mémoire LTM + résumés épisodiques d'un client
 * (parité `client_history.save_memory_facts` / `save_session_summary`).
 * Tous les champs JSON sont passés déjà sérialisés (string) par Python.
 */
export const upsertMemory = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    clientPhone: v.string(),
    memoryFacts: v.optional(v.string()), // JSON LTM
    lastSessionSummary: v.optional(v.string()),
    conversationSummaries: v.optional(v.string()), // JSON épisodique
    preferences: v.optional(v.string()), // JSON
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const now = Date.now();

    const existing = await ctx.db
      .query("clientHistory")
      .withIndex("by_merchant_client", (q) =>
        q.eq("merchantId", args.merchantId).eq("clientPhone", args.clientPhone),
      )
      .unique();

    const patch: Record<string, unknown> = { updatedAt: now };
    if (args.memoryFacts !== undefined) patch.memoryFacts = args.memoryFacts;
    if (args.lastSessionSummary !== undefined)
      patch.lastSessionSummary = args.lastSessionSummary;
    if (args.conversationSummaries !== undefined)
      patch.conversationSummaries = args.conversationSummaries;
    if (args.preferences !== undefined) patch.preferences = args.preferences;

    if (existing) {
      await ctx.db.patch(existing._id, patch);
      return { clientHistoryId: existing._id, created: false };
    }
    const id = await ctx.db.insert("clientHistory", {
      merchantId: args.merchantId,
      clientPhone: args.clientPhone,
      ...patch,
    });
    return { clientHistoryId: id, created: true };
  },
});

/**
 * Enregistre une entrée de base de connaissances (parité `knowledge.save_entry`)
 * — auto-learn deal, feedback correction, réponse humaine, import FAQ.
 */
export const saveKnowledgeEntry = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    question: v.string(),
    answer: v.string(),
    source: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const id = await ctx.db.insert("knowledgeBase", {
      merchantId: args.merchantId,
      question: args.question,
      answer: args.answer,
      source: args.source ?? "human_reply",
      usageCount: 0,
    });
    return { knowledgeBaseId: id };
  },
});
