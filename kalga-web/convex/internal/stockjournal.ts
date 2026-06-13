import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import type { Doc } from "../_generated/dataModel";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts` — fonctions publiques gardées par
// l'argument secret `internalKey` (server-to-server Python sans deploy key).

/**
 * Fonctions internes waitlist/journal stock NON hot-path (backend Python).
 * Parité `waitlist_repo` côté dashboard + scheduler d'alertes. Les opérations
 * hot-path (addToWaitlist/getWaitlistCount/isClientInWaitlist/logStockEvent)
 * sont déjà dans `internal/waitlist.ts`.
 * Couvre : get_waitlist_for_product, get_merchant_waitlist_summary,
 * mark_notified, clear_waitlist, get_stock_history, get_lost_revenue_estimate,
 * get_products_out_of_stock_since + la query marchands pour le poll d'alertes.
 */

const WAITING = "waiting" as const;
const NOTIFIED = "notified" as const;

/** Doc productWaitlist -> dict snake_case (parité dict(row)). */
function waitDict(w: Doc<"productWaitlist">) {
  return {
    id: w._id,
    merchant_id: w.merchantId,
    product_id: w.productId,
    client_phone: w.clientPhone,
    client_name: w.clientName ?? null,
    status: w.status,
    conversation_id: w.conversationId ?? null,
    offered_price: w.offeredPrice ?? null,
    expires_at: w.expiresAt ?? null,
    notified_at: w.notifiedAt ?? null,
    created_at: w._creationTime,
    updated_at: w.updatedAt ?? w._creationTime,
  };
}

/** File d'attente d'un produit (parité `get_waitlist_for_product`). Ordre ancienneté. */
export const getWaitlistForProduct = query({
  args: {
    internalKey: v.string(),
    productId: v.id("products"),
    status: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const status = args.status ?? WAITING;
    const rows = await ctx.db
      .query("productWaitlist")
      .withIndex("by_product_status", (q) =>
        q.eq("productId", args.productId).eq("status", status as any),
      )
      .collect();
    rows.sort((a, b) => a._creationTime - b._creationTime);
    return rows.map(waitDict);
  },
});

/**
 * Résumé waitlist par produit pour un marchand (parité `get_merchant_waitlist_summary`).
 * SQLite : JOIN products + GROUP BY. Convex : agrégat JS.
 */
export const getMerchantWaitlistSummary = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const waiting = await ctx.db
      .query("productWaitlist")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    const byProduct = new Map<
      string,
      { count: number; oldest: number; entries: Doc<"productWaitlist">[] }
    >();
    for (const w of waiting) {
      if (w.status !== WAITING) continue;
      const key = w.productId as string;
      const agg = byProduct.get(key) ?? {
        count: 0,
        oldest: w._creationTime,
        entries: [],
      };
      agg.count += 1;
      agg.oldest = Math.min(agg.oldest, w._creationTime);
      byProduct.set(key, agg);
    }
    const out = [];
    for (const [pid, agg] of byProduct.entries()) {
      const p = await ctx.db.get(pid as Doc<"products">["_id"]);
      out.push({
        product_id: pid,
        product_name: p?.name ?? null,
        product_code: p?.code ?? null,
        product_price: p?.price ?? null,
        waiting_count: agg.count,
        oldest_wait_date: agg.oldest,
      });
    }
    out.sort((a, b) => b.waiting_count - a.waiting_count);
    return out;
  },
});

/** Marque des entrées waitlist comme notifiées (parité `mark_notified`). */
export const markNotified = mutation({
  args: {
    internalKey: v.string(),
    waitlistIds: v.array(v.id("productWaitlist")),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const now = Date.now();
    let count = 0;
    for (const id of args.waitlistIds) {
      const w = await ctx.db.get(id);
      if (w) {
        await ctx.db.patch(id, {
          status: NOTIFIED,
          notifiedAt: now,
          updatedAt: now,
        });
        count += 1;
      }
    }
    return { updated: count };
  },
});

/** Vide la waitlist d'un produit après broadcast (parité `clear_waitlist`). */
export const clearWaitlist = mutation({
  args: {
    internalKey: v.string(),
    productId: v.id("products"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const now = Date.now();
    const waiting = await ctx.db
      .query("productWaitlist")
      .withIndex("by_product_status", (q) =>
        q.eq("productId", args.productId).eq("status", WAITING),
      )
      .collect();
    for (const w of waiting) {
      await ctx.db.patch(w._id, {
        status: NOTIFIED,
        notifiedAt: now,
        updatedAt: now,
      });
    }
    return { cleared: waiting.length };
  },
});

/** Historique des événements de stock d'un produit (parité `get_stock_history`). */
export const getStockHistory = query({
  args: {
    internalKey: v.string(),
    productId: v.id("products"),
    sinceMs: v.number(), // epoch ms (now - days), calculé par Python
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const rows = await ctx.db
      .query("stockEvents")
      .withIndex("by_product", (q) => q.eq("productId", args.productId))
      .collect();
    return rows
      .filter((e) => e._creationTime >= args.sinceMs)
      .sort((a, b) => a._creationTime - b._creationTime)
      .map((e) => ({
        id: e._id,
        merchant_id: e.merchantId,
        product_id: e.productId,
        event_type: e.eventType,
        quantity_delta: e.quantityDelta,
        quantity_after: e.quantityAfter,
        conversation_id: e.conversationId ?? null,
        notes: e.notes ?? null,
        created_at: e._creationTime,
      }));
  },
});

/**
 * Estimation des revenus perdus (parité `get_lost_revenue_estimate`).
 * SQLite : JOIN conversations/products WHERE stock=0. Convex : agrégat JS.
 */
export const getLostRevenueEstimate = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    sinceMs: v.number(),
    days: v.number(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const convs = await ctx.db
      .query("conversations")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    const counted = ["active", "ended", "abandoned"];
    let lost = 0;
    let priceSum = 0;
    const convIds = new Set<string>();
    for (const c of convs) {
      if (c._creationTime < args.sinceMs) continue;
      if (!counted.includes(c.status)) continue;
      const p = await ctx.db.get(c.productId);
      if (!p || (p.stockQuantity ?? -1) !== 0) continue;
      convIds.add(c._id as string);
      priceSum += p.price ?? 0;
    }
    const lostInquiries = convIds.size;
    const avgPrice = lostInquiries ? priceSum / lostInquiries : 0;
    return {
      lost_inquiries: lostInquiries,
      avg_price: avgPrice,
      estimated_lost: priceSum * 0.5,
      days: args.days,
    };
  },
});

/**
 * Produits épuisés depuis >= N jours pour le dialogue proactif marchand
 * (parité `get_products_out_of_stock_since`). `sinceMs` = now - days (Python).
 * `alertCooldownMs` = seuil last_stock_alert_at (now - 1 jour).
 */
export const getProductsOutOfStockSince = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    sinceMs: v.number(),
    alertCooldownMs: v.number(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const products = await ctx.db
      .query("products")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    const out = [];
    for (const p of products) {
      if (p.isAvailable === false || (p.stockQuantity ?? -1) !== 0) continue;
      // last_stock_alert_at cooldown (NULL ou <= now-1j).
      if (p.lastStockAlertAt != null && p.lastStockAlertAt > args.alertCooldownMs)
        continue;
      // Date du dernier passage à 0 via stockEvents out_of_stock <= sinceMs.
      const events = await ctx.db
        .query("stockEvents")
        .withIndex("by_product", (q) => q.eq("productId", p._id))
        .collect();
      const outEvents = events.filter(
        (e) => e.eventType === "out_of_stock" && e._creationTime <= args.sinceMs,
      );
      if (outEvents.length === 0) continue;
      const outSince = Math.min(...outEvents.map((e) => e._creationTime));
      const waitlistCount = (
        await ctx.db
          .query("productWaitlist")
          .withIndex("by_product_status", (q) =>
            q.eq("productId", p._id).eq("status", WAITING),
          )
          .collect()
      ).length;
      out.push({
        id: p._id,
        name: p.name,
        code: p.code,
        price: p.price,
        last_stock_alert_at: p.lastStockAlertAt ?? null,
        out_since: outSince,
        waitlist_count: waitlistCount,
      });
    }
    return out;
  },
});

/** Marchands avec alertes stock activées (parité poll `stock_alert_service`). */
export const getMerchantsWithAlerts = query({
  args: { internalKey: v.string() },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const merchants = await ctx.db.query("merchants").collect();
    return merchants
      .filter((m) => m.stockAlertsEnabled !== false)
      .map((m) => ({
        id: m._id,
        phone: m.phone,
        name: m.name,
        stock_alert_days: m.stockAlertDays ?? null,
        stock_alerts_enabled: m.stockAlertsEnabled ?? null,
      }));
  },
});
