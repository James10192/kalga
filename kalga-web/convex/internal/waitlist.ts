import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import type { Doc } from "../_generated/dataModel";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts` — fonctions publiques gardées par
// l'argument secret `internalKey` (server-to-server Python sans deploy key).

/**
 * Fonctions internes waitlist / journal stock (appelées par le backend Python).
 * Parité `waitlist_repo` (kalga-api). Branche out-of-stock du hot-path chat :
 * inscription en file d'attente quand un produit est en rupture, et journal
 * append-only des événements de stock.
 *
 * Grain grossier : un seul appel par opération métier, idempotence côté serveur.
 */

const WAITING = "waiting" as const; // statut "en attente" (parité 'waiting' SQLite)

/**
 * Nombre de clients en attente pour un produit
 * (parité `waitlist_repo.get_waitlist_count`).
 */
export const getWaitlistCount = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    productId: v.id("products"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const waiting = await ctx.db
      .query("productWaitlist")
      .withIndex("by_product_status", (q) =>
        q.eq("productId", args.productId).eq("status", WAITING),
      )
      .collect();
    return waiting.length;
  },
});

/**
 * Vérifie si un client est déjà en file d'attente pour un produit
 * (parité `waitlist_repo.is_client_in_waitlist`).
 */
export const isClientInWaitlist = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    productId: v.id("products"),
    clientPhone: v.string(),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const existing = await ctx.db
      .query("productWaitlist")
      .withIndex("by_product_status", (q) =>
        q.eq("productId", args.productId).eq("status", WAITING),
      )
      .filter((q) => q.eq(q.field("clientPhone"), args.clientPhone))
      .first();
    return existing !== null;
  },
});

/**
 * Inscrit un client en file d'attente (parité `waitlist_repo.add_to_waitlist`).
 * IDEMPOTENT : si le client est déjà en attente pour ce produit, renvoie sa
 * position existante sans dupliquer. `position` = rang (1-based) dans la file.
 */
export const addToWaitlist = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    productId: v.id("products"),
    clientPhone: v.string(),
    clientName: v.optional(v.string()),
    conversationId: v.optional(v.id("conversations")),
    offeredPrice: v.optional(v.number()),
    expiresDays: v.optional(v.number()), // DEFAULT 7 (parité)
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);

    // File d'attente courante (ordonnée par ancienneté = ordre d'insertion).
    const waiting = await ctx.db
      .query("productWaitlist")
      .withIndex("by_product_status", (q) =>
        q.eq("productId", args.productId).eq("status", WAITING),
      )
      .collect();

    // Idempotence : déjà inscrit -> renvoie sa position existante.
    const existingIdx = waiting.findIndex(
      (e) => e.clientPhone === args.clientPhone,
    );
    if (existingIdx !== -1) {
      return { added: false, position: existingIdx + 1 };
    }

    const now = Date.now();
    const expiresDays = args.expiresDays ?? 7;
    const expiresAt = now + expiresDays * 24 * 60 * 60 * 1000;

    await ctx.db.insert("productWaitlist", {
      merchantId: args.merchantId,
      productId: args.productId,
      clientPhone: args.clientPhone,
      clientName: args.clientName,
      status: WAITING,
      conversationId: args.conversationId,
      offeredPrice: args.offeredPrice,
      expiresAt,
      updatedAt: now,
    });

    // Nouvelle position = en fin de file.
    return { added: true, position: waiting.length + 1 };
  },
});

/**
 * Journalise un événement de stock (parité `waitlist_repo.log_stock_event`).
 * Journal append-only. `eventType` ∈ restock | out_of_stock | sale.
 * `quantityDelta` = variation signée ; `quantityAfter` = stock résultant.
 */
export const logStockEvent = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    productId: v.id("products"),
    eventType: v.union(
      v.literal("restock"),
      v.literal("out_of_stock"),
      v.literal("sale"),
    ),
    quantityDelta: v.number(),
    quantityAfter: v.number(),
    conversationId: v.optional(v.id("conversations")),
    notes: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const eventId = await ctx.db.insert("stockEvents", {
      merchantId: args.merchantId,
      productId: args.productId,
      eventType: args.eventType,
      quantityDelta: args.quantityDelta,
      quantityAfter: args.quantityAfter,
      conversationId: args.conversationId,
      notes: args.notes,
    });
    return { eventId } as { eventId: Doc<"stockEvents">["_id"] };
  },
});
