import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts` — fonctions publiques gardées par
// l'argument secret `internalKey` (server-to-server Python sans deploy key).

/**
 * Fonctions internes base de connaissances NON hot-path (backend Python).
 * Parité `knowledge_repo` côté lecture/admin. L'écriture d'une entrée unique
 * (save_entry) passe déjà par `internal/memory:saveKnowledgeEntry`.
 * Couvre : get_all, delete_entry, seed_defaults, get_insights, search.
 *
 * Le scoring `search` (chevauchement de mots-clés) reste côté Python : Convex
 * renvoie les entrées brutes, Python score + incrémente usage via `bumpUsage`.
 */

/** Toutes les entrées KB paginées (parité `knowledge_repo.get_all`). */
export const getAll = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    limit: v.optional(v.number()),
    offset: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const rows = await ctx.db
      .query("knowledgeBase")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    rows.sort(
      (a, b) =>
        (b.usageCount ?? 0) - (a.usageCount ?? 0) ||
        b._creationTime - a._creationTime,
    );
    const offset = args.offset ?? 0;
    const limit = args.limit ?? 50;
    return rows.slice(offset, offset + limit).map((r) => ({
      id: r._id,
      question: r.question,
      answer: r.answer,
      keywords: r.keywords ?? null,
      source: r.source ?? null,
      usage_count: r.usageCount ?? 0,
      created_at: r._creationTime,
    }));
  },
});

/**
 * Entrées brutes pour le scoring `search` côté Python (parité SELECT LIMIT 200).
 * Python filtre/score par mots-clés puis appelle `bumpUsage` sur les retenues.
 */
export const listForSearch = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const rows = await ctx.db
      .query("knowledgeBase")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    rows.sort((a, b) => b._creationTime - a._creationTime);
    return rows.slice(0, args.limit ?? 200).map((r) => ({
      id: r._id,
      question: r.question,
      answer: r.answer,
      keywords: r.keywords ?? null,
      usage_count: r.usageCount ?? 0,
    }));
  },
});

/** Incrémente le compteur d'usage de plusieurs entrées (parité search side-effect). */
export const bumpUsage = mutation({
  args: {
    internalKey: v.string(),
    entryIds: v.array(v.id("knowledgeBase")),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    for (const id of args.entryIds) {
      const e = await ctx.db.get(id);
      if (e) await ctx.db.patch(id, { usageCount: (e.usageCount ?? 0) + 1 });
    }
    return { bumped: args.entryIds.length };
  },
});

/** Supprime une entrée KB avec garde merchantId (parité `delete_entry`). */
export const deleteEntry = mutation({
  args: {
    internalKey: v.string(),
    entryId: v.id("knowledgeBase"),
    merchantId: v.id("merchants"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const e = await ctx.db.get(args.entryId);
    if (!e || e.merchantId !== args.merchantId) return { deleted: false };
    await ctx.db.delete(args.entryId);
    return { deleted: true };
  },
});

/**
 * Insère les FAQ par défaut SI la KB du marchand est vide (parité `seed_defaults`).
 * Idempotent. `entries` (question/answer) fournies par Python (DEFAULT_FAQ_ENTRIES).
 * `keywords` calculés côté Python (extract_keywords) et passés par entrée.
 */
export const seedDefaults = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    entries: v.array(
      v.object({
        question: v.string(),
        answer: v.string(),
        keywords: v.optional(v.string()),
      }),
    ),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const existing = await ctx.db
      .query("knowledgeBase")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .first();
    if (existing) return { created: 0 };

    let count = 0;
    for (const e of args.entries) {
      await ctx.db.insert("knowledgeBase", {
        merchantId: args.merchantId,
        question: e.question,
        answer: e.answer,
        keywords: e.keywords,
        source: "default_faq",
        usageCount: 0,
      });
      count += 1;
    }
    return { created: count };
  },
});

/**
 * Insights de la boucle d'apprentissage (parité `get_insights`).
 * Agrège par source + top 5 + question gaps (auto_flagged feedback groupés).
 */
export const getInsights = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const entries = await ctx.db
      .query("knowledgeBase")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();

    const sources: Record<string, number> = {};
    for (const e of entries) {
      const src = e.source ?? "human_reply";
      sources[src] = (sources[src] ?? 0) + 1;
    }

    const top = [...entries]
      .sort((a, b) => (b.usageCount ?? 0) - (a.usageCount ?? 0))
      .slice(0, 5)
      .map((e) => ({
        question: e.question,
        answer: e.answer,
        usage_count: e.usageCount ?? 0,
        source: e.source ?? null,
      }));

    const feedback = await ctx.db
      .query("conversationFeedback")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    const gapCounts = new Map<string, number>();
    for (const f of feedback) {
      if (f.feedbackType !== "auto_flagged") continue;
      gapCounts.set(f.clientMessage, (gapCounts.get(f.clientMessage) ?? 0) + 1);
    }
    const gaps = [...gapCounts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([client_message, occurrence]) => ({ client_message, occurrence }));

    const total = entries.length;
    return {
      total_kb_entries: total,
      sources_breakdown: sources,
      auto_learned_deals: sources["auto_learned_deal"] ?? 0,
      feedback_corrections: sources["feedback_correction"] ?? 0,
      default_faq: sources["default_faq"] ?? 0,
      top_entries: top,
      question_gaps: gaps,
      gap_count: gaps.length,
    };
  },
});
