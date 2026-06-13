import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import type { Doc } from "../_generated/dataModel";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts` — fonctions publiques gardées par
// l'argument secret `internalKey` (server-to-server Python sans deploy key).

/**
 * Fonctions internes statistiques / analytics (appelées par le backend Python).
 * Parité `stats_repo` (kalga-api). Convex n'a PAS d'agrégat SQL : SUM/AVG/GROUP
 * BY sont recalculés en JS sur les docs collectés.
 *
 * Dates : SQLite stockait `daily_stats.date` en ISO 'YYYY-MM-DD'. On garde le
 * même contrat — Python passe les bornes en ISO, on compare lexicographiquement.
 */

/** Champs numériques d'une ligne `dailyStats` avec défaut 0. */
function statRow(d: Doc<"dailyStats">) {
  return {
    id: d._id,
    merchant_id: d.merchantId,
    date: d.date,
    conversations_count: d.conversationsCount ?? 0,
    messages_count: d.messagesCount ?? 0,
    sales_count: d.salesCount ?? 0,
    revenue: d.revenue ?? 0,
    unique_clients: d.uniqueClients ?? 0,
    avg_response_time: d.avgResponseTime ?? null,
  };
}

/**
 * Récupère (ou crée) la ligne de stats du jour (parité `get_or_create_daily_stats`).
 * `date` = ISO 'YYYY-MM-DD' fourni par Python (today côté serveur Python).
 */
export const getOrCreateDailyStats = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    date: v.string(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const existing = await ctx.db
      .query("dailyStats")
      .withIndex("by_merchant_date", (q) =>
        q.eq("merchantId", args.merchantId).eq("date", args.date),
      )
      .unique();
    if (existing) return statRow(existing);

    const id = await ctx.db.insert("dailyStats", {
      merchantId: args.merchantId,
      date: args.date,
    });
    const created = await ctx.db.get(id);
    return statRow(created!);
  },
});

/** Upsert atomique d'un delta sur la ligne du jour (parité increment_x / record_sale). */
async function bumpDay(
  ctx: { db: any },
  merchantId: Doc<"merchants">["_id"],
  date: string,
  patch: Partial<{
    conversationsDelta: number;
    messagesDelta: number;
    salesDelta: number;
    revenueDelta: number;
    uniqueClients: number;
  }>,
) {
  const existing = await ctx.db
    .query("dailyStats")
    .withIndex("by_merchant_date", (q: any) =>
      q.eq("merchantId", merchantId).eq("date", date),
    )
    .unique();
  if (existing) {
    const upd: Record<string, number> = {};
    if (patch.conversationsDelta)
      upd.conversationsCount =
        (existing.conversationsCount ?? 0) + patch.conversationsDelta;
    if (patch.messagesDelta)
      upd.messagesCount = (existing.messagesCount ?? 0) + patch.messagesDelta;
    if (patch.salesDelta)
      upd.salesCount = (existing.salesCount ?? 0) + patch.salesDelta;
    if (patch.revenueDelta)
      upd.revenue = (existing.revenue ?? 0) + patch.revenueDelta;
    if (patch.uniqueClients !== undefined)
      upd.uniqueClients = patch.uniqueClients;
    await ctx.db.patch(existing._id, upd);
    return;
  }
  await ctx.db.insert("dailyStats", {
    merchantId,
    date,
    conversationsCount: patch.conversationsDelta ?? 0,
    messagesCount: patch.messagesDelta ?? 0,
    salesCount: patch.salesDelta ?? 0,
    revenue: patch.revenueDelta ?? 0,
    uniqueClients: patch.uniqueClients ?? 0,
  });
}

/** Incrémente conversations / messages / ventes du jour (parité increment_x / record_sale). */
export const bumpDailyStats = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    date: v.string(),
    conversationsDelta: v.optional(v.number()),
    messagesDelta: v.optional(v.number()),
    salesDelta: v.optional(v.number()),
    revenueDelta: v.optional(v.number()),
    uniqueClients: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    await bumpDay(ctx, args.merchantId, args.date, {
      conversationsDelta: args.conversationsDelta,
      messagesDelta: args.messagesDelta,
      salesDelta: args.salesDelta,
      revenueDelta: args.revenueDelta,
      uniqueClients: args.uniqueClients,
    });
    return { ok: true };
  },
});

/** Lignes de stats sur une plage de dates ISO (parité `get_stats_range`). */
export const getStatsRange = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    startDate: v.string(),
    endDate: v.string(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const rows = await ctx.db
      .query("dailyStats")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    return rows
      .filter((r) => r.date >= args.startDate && r.date <= args.endDate)
      .sort((a, b) => a.date.localeCompare(b.date))
      .map(statRow);
  },
});

/** Top produits par conversations/ventes (parité `get_top_products`). */
export const getTopProducts = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const products = await ctx.db
      .query("products")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    const convs = await ctx.db
      .query("conversations")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();

    const byProduct = new Map<
      string,
      { conversation_count: number; sales_count: number; revenue: number }
    >();
    for (const c of convs) {
      const key = c.productId as string;
      const agg = byProduct.get(key) ?? {
        conversation_count: 0,
        sales_count: 0,
        revenue: 0,
      };
      agg.conversation_count += 1;
      if (c.status === "completed") {
        agg.sales_count += 1;
        agg.revenue += c.currentOffer ?? 0;
      }
      byProduct.set(key, agg);
    }

    const rows = products.map((p) => {
      const agg = byProduct.get(p._id as string) ?? {
        conversation_count: 0,
        sales_count: 0,
        revenue: 0,
      };
      return { id: p._id, name: p.name, code: p.code, ...agg };
    });
    rows.sort(
      (a, b) =>
        b.sales_count - a.sales_count ||
        b.conversation_count - a.conversation_count,
    );
    return rows.slice(0, args.limit ?? 5);
  },
});

/** Taux de conversion sur N jours (parité `get_conversion_rate`). */
export const getConversionRate = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    startMs: v.number(), // borne basse epoch ms (today - days)
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const convs = await ctx.db
      .query("conversations")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    const inRange = convs.filter((c) => c._creationTime >= args.startMs);
    const total = inRange.length;
    const completed = inRange.filter((c) => c.status === "completed").length;
    const pending = inRange.filter(
      (c) =>
        c.status === "pending_delivery" || c.status === "pending_pickup",
    ).length;
    const rate = total > 0 ? Math.round((completed / total) * 1000) / 10 : 0;
    return {
      total_conversations: total,
      completed_sales: completed,
      pending_sales: pending,
      conversion_rate: rate,
    };
  },
});

/**
 * Activité par heure de la journée sur N jours (parité `get_hourly_activity`).
 * SQLite groupait `strftime('%H', messages.created_at)`. Convex : on collecte
 * les conversations du marchand, puis les messages de chaque conversation sur
 * la fenêtre, et on bucketise par heure locale du `_creationTime`.
 *
 * `tzOffsetMinutes` = décalage local (ex: Abidjan = 0). Python le passe pour
 * que l'heure corresponde au fuseau marchand (SQLite stockait l'heure locale).
 */
export const getHourlyActivity = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    startMs: v.number(),
    tzOffsetMinutes: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const convs = await ctx.db
      .query("conversations")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    const offsetMs = (args.tzOffsetMinutes ?? 0) * 60 * 1000;
    const buckets = new Map<number, number>();
    for (const c of convs) {
      const msgs = await ctx.db
        .query("messages")
        .withIndex("by_conversation", (q) => q.eq("conversationId", c._id))
        .collect();
      for (const m of msgs) {
        if (m._creationTime < args.startMs) continue;
        const hour = new Date(m._creationTime + offsetMs).getUTCHours();
        buckets.set(hour, (buckets.get(hour) ?? 0) + 1);
      }
    }
    return [...buckets.entries()]
      .map(([hour, count]) => ({ hour, count }))
      .sort((a, b) => a.hour - b.hour);
  },
});

/** Enregistre un événement analytics (parité `log_event`). `data` = JSON string. */
export const logEvent = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    eventType: v.string(),
    productId: v.optional(v.id("products")),
    conversationId: v.optional(v.id("conversations")),
    clientPhone: v.optional(v.string()),
    data: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const id = await ctx.db.insert("analyticsEvents", {
      merchantId: args.merchantId,
      eventType: args.eventType,
      productId: args.productId,
      conversationId: args.conversationId,
      clientPhone: args.clientPhone,
      data: args.data,
    });
    return { eventId: id };
  },
});

/** Événements analytics récents (parité `get_recent_events`). */
export const getRecentEvents = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    eventType: v.optional(v.string()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    let rows = await ctx.db
      .query("analyticsEvents")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    if (args.eventType)
      rows = rows.filter((r) => r.eventType === args.eventType);
    rows.sort((a, b) => b._creationTime - a._creationTime);
    return rows.slice(0, args.limit ?? 50);
  },
});
