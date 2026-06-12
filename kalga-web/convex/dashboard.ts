import { query } from "./_generated/server";
import { v } from "convex/values";
import type { Doc } from "./_generated/dataModel";

/**
 * Lectures agrégées pour l'accueil du dashboard marchand (plan 006, read-only).
 *
 * Grain GROSSIER volontaire : l'accueil (flagship-home) a besoin, en un seul
 * round-trip, de la liste des conversations enrichie (dernier message, produit,
 * ligne argent) + de l'encaisse du jour + des compteurs de pills. On évite ainsi
 * le N+1 côté client (un useQuery par conversation pour son dernier message).
 *
 * Scoping tenant : tout passe par `merchantId` + index `by_merchant`.
 * NB : pas d'auth gating ici (l'OTP live + withOrg viendront en 003/004). La
 * signature `{ merchantId }` se branchera plus tard derrière withOrg sans casser
 * le contrat de lecture.
 */

/** Statuts considérés comme une vente comptabilisée (encaisse du jour). */
const SOLD_STATUSES = new Set<Doc<"conversations">["status"]>([
  "agreed",
  "pending_delivery",
  "pending_pickup",
  "completed",
]);

/** Statuts d'une conversation "vivante" en négociation. */
const NEGOTIATING_STATUSES = new Set<Doc<"conversations">["status"]>([
  "active",
  "negotiating",
]);

/** Statuts d'une vente conclue mais pas encore remise au client. */
const TO_DELIVER_STATUSES = new Set<Doc<"conversations">["status"]>([
  "agreed",
  "pending_delivery",
  "pending_pickup",
]);

/** Montant "argent" d'une conversation : offre courante sinon prix produit. */
function conversationAmount(
  conv: Doc<"conversations">,
  product: Doc<"products"> | null,
): number | null {
  if (typeof conv.currentOffer === "number") return conv.currentOffer;
  if (product && typeof product.price === "number") return product.price;
  return null;
}

/**
 * Fil de conversations enrichi pour l'accueil.
 * Trie par récence (updatedAt ou _creationTime), limite `limit`.
 */
export const feedForMerchant = query({
  args: {
    merchantId: v.id("merchants"),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = args.limit ?? 20;

    const conversations = await ctx.db
      .query("conversations")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();

    // Tri récence décroissante.
    conversations.sort(
      (a, b) =>
        (b.updatedAt ?? b._creationTime) - (a.updatedAt ?? a._creationTime),
    );

    const sliced = conversations.slice(0, limit);

    // Cache produit pour éviter les relectures répétées.
    const productCache = new Map<string, Doc<"products"> | null>();
    async function getProduct(id: Doc<"conversations">["productId"]) {
      const key = String(id);
      if (productCache.has(key)) return productCache.get(key) ?? null;
      const p = await ctx.db.get(id);
      productCache.set(key, p);
      return p;
    }

    const rows = await Promise.all(
      sliced.map(async (conv) => {
        const product = await getProduct(conv.productId);

        // Dernier message de la conversation.
        const lastMessage = await ctx.db
          .query("messages")
          .withIndex("by_conversation", (q) =>
            q.eq("conversationId", conv._id),
          )
          .order("desc")
          .first();

        const amount = conversationAmount(conv, product);

        return {
          conversationId: conv._id,
          clientPhone: conv.clientPhone,
          status: conv.status,
          currentOffer: conv.currentOffer ?? null,
          updatedAt: conv.updatedAt ?? conv._creationTime,
          productName: product?.name ?? null,
          productPrice: product?.price ?? null,
          amount,
          lastMessage: lastMessage
            ? {
                content: lastMessage.content,
                isFromClient: lastMessage.isFromClient,
              }
            : null,
        };
      }),
    );

    return rows;
  },
});

/**
 * Synthèse "argent du jour" + compteurs de pills pour l'accueil.
 * - encaisse du jour : somme des montants des ventes conclues aujourd'hui ;
 * - compteurs : en négo / à livrer / en rupture.
 *
 * "Aujourd'hui" est calculé côté serveur (epoch ms, minuit local serveur). Les
 * stats restent volontairement simples (vue registre, pas analytics — DIRECTION.md).
 */
export const todaySummaryForMerchant = query({
  args: { merchantId: v.id("merchants") },
  handler: async (ctx, args) => {
    const now = new Date();
    const startOfDay = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
    ).getTime();
    const startOfYesterday = startOfDay - 24 * 60 * 60 * 1000;

    const conversations = await ctx.db
      .query("conversations")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();

    const productCache = new Map<string, Doc<"products"> | null>();
    async function getProduct(id: Doc<"conversations">["productId"]) {
      const key = String(id);
      if (productCache.has(key)) return productCache.get(key) ?? null;
      const p = await ctx.db.get(id);
      productCache.set(key, p);
      return p;
    }

    let todayRevenue = 0;
    let todaySales = 0;
    let yesterdayRevenue = 0;
    let negotiating = 0;
    let toDeliver = 0;

    for (const conv of conversations) {
      const when = conv.updatedAt ?? conv._creationTime;
      const isSold = SOLD_STATUSES.has(conv.status);

      if (isSold && when >= startOfDay) {
        const product = await getProduct(conv.productId);
        const amount = conversationAmount(conv, product);
        if (amount !== null) {
          todayRevenue += amount;
          todaySales += 1;
        }
      } else if (isSold && when >= startOfYesterday && when < startOfDay) {
        const product = await getProduct(conv.productId);
        const amount = conversationAmount(conv, product);
        if (amount !== null) yesterdayRevenue += amount;
      }

      if (NEGOTIATING_STATUSES.has(conv.status)) negotiating += 1;
      if (TO_DELIVER_STATUSES.has(conv.status)) toDeliver += 1;
    }

    // Rupture : produits actifs en stock 0 (parité statut "out_of_stock").
    const products = await ctx.db
      .query("products")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    const outOfStock = products.filter(
      (p) => (p.isActive ?? true) && (p.stockQuantity ?? -1) === 0,
    ).length;

    // Delta vs hier (en %), arrondi. Null si pas de base de comparaison.
    let deltaPct: number | null = null;
    if (yesterdayRevenue > 0) {
      deltaPct = Math.round(
        ((todayRevenue - yesterdayRevenue) / yesterdayRevenue) * 100,
      );
    }

    return {
      todayRevenue,
      todaySales,
      deltaPct,
      pills: { negotiating, toDeliver, outOfStock },
    };
  },
});

/** Début du jour calendaire (minuit local serveur) pour `epochMs`. */
function startOfDayMs(epochMs: number): number {
  const d = new Date(epochMs);
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

/**
 * Registre des ventes du marchand (écran "Argent" — vue registre, pas analytics).
 *
 * Une vente comptabilisée = conversation au statut `completed` avec un montant.
 * Renvoie, en un seul round-trip :
 *  - `todayTotal` : encaisse du jour calendaire courant ;
 *  - `weekTotal` : encaisse des 7 derniers jours glissants (lundi-agnostique, simple) ;
 *  - `sales` : la liste des ventes récentes (montant, client, produit, horodatage),
 *    triée par récence décroissante, limitée à `limit`.
 *
 * Scoping tenant via `merchantId` + index `by_merchant` (se branchera derrière
 * withOrg avec l'OTP live, sans casser ce contrat de lecture).
 */
export const salesRegistryForMerchant = query({
  args: {
    merchantId: v.id("merchants"),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = args.limit ?? 30;
    const now = Date.now();
    const startToday = startOfDayMs(now);
    // Semaine = 7 jours glissants à partir du début du jour courant.
    const startWeek = startToday - 6 * 24 * 60 * 60 * 1000;

    const conversations = await ctx.db
      .query("conversations")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .filter((q) => q.eq(q.field("status"), "completed"))
      .collect();

    const productCache = new Map<string, Doc<"products"> | null>();
    async function getProduct(id: Doc<"conversations">["productId"]) {
      const key = String(id);
      if (productCache.has(key)) return productCache.get(key) ?? null;
      const p = await ctx.db.get(id);
      productCache.set(key, p);
      return p;
    }

    let todayTotal = 0;
    let weekTotal = 0;
    let todayCount = 0;
    let weekCount = 0;

    type Sale = {
      conversationId: string;
      clientPhone: string;
      amount: number;
      productName: string | null;
      soldAt: number;
    };
    const sales: Sale[] = [];

    for (const conv of conversations) {
      const product = await getProduct(conv.productId);
      const amount = conversationAmount(conv, product);
      if (amount === null) continue;

      const soldAt = conv.updatedAt ?? conv._creationTime;
      if (soldAt >= startToday) {
        todayTotal += amount;
        todayCount += 1;
      }
      if (soldAt >= startWeek) {
        weekTotal += amount;
        weekCount += 1;
      }

      sales.push({
        conversationId: conv._id,
        clientPhone: conv.clientPhone,
        amount,
        productName: product?.name ?? null,
        soldAt,
      });
    }

    sales.sort((a, b) => b.soldAt - a.soldAt);

    return {
      todayTotal,
      weekTotal,
      todayCount,
      weekCount,
      sales: sales.slice(0, limit),
    };
  },
});
