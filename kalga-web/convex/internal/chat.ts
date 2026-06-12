import { query, mutation } from "../_generated/server";
import { v } from "convex/values";
import type { Doc, Id } from "../_generated/dataModel";
import { assertInternalKey } from "./guard";

// Visibilité : voir note dans `inventory.ts`. Fonctions publiques gardées par
// l'argument secret `internalKey` (pas `internalQuery`, qui exigerait une deploy
// key côté client Python). Le secret partagé EST la garde (contrat plan 004).

/**
 * Fonctions internes chat (hot-path), appelées par le backend Python.
 *
 * Principe directeur (plan 004) : grain GROSSIER. Au lieu des ~10-15 appels DB
 * séquentiels du `chat_service.py` SQLite, on expose :
 *  - `getContext`  : un seul round-trip read renvoyant marchand + produit +
 *                    conversation + historique + statut stock + faits mémoire.
 *  - `commitTurn`  : une seule transaction write (message client + message bot +
 *                    maj statut/offre + stats messages) — atomique côté Convex.
 *
 * Le moteur de dialogue (DeepSeek v2) reste côté Python ; Convex ne porte que la
 * persistance. La résolution de la conversation (création/réouverture) est faite
 * dans `getContext` pour minimiser les allers-retours.
 */

const LIVE_STATUSES = ["pending_pickup", "pending_delivery"] as const;
const CLOSED_FOR_REOPEN = ["completed", "ended"] as const;

/** Statut stock (parité `product_repo.check_stock_status`). */
function stockStatus(product: Doc<"products">) {
  const quantity = product.stockQuantity ?? -1;
  const threshold = product.lowStockThreshold ?? 5;
  const isUnlimited = quantity === -1;
  return {
    available: isUnlimited || quantity > 0,
    quantity,
    isLow: !isUnlimited && quantity > 0 && quantity <= threshold,
    isOutOfStock: !isUnlimited && quantity === 0,
    isUnlimited,
    threshold,
  };
}

/** Identifie le marchand par téléphone, avec fallback numéro ivoirien (225 -> 2250). */
async function resolveMerchant(
  ctx: { db: any },
  phone: string,
): Promise<Doc<"merchants"> | null> {
  let merchant = await ctx.db
    .query("merchants")
    .withIndex("by_phone", (q: any) => q.eq("phone", phone))
    .unique();
  if (!merchant && phone.startsWith("225") && phone.length === 12) {
    const corrected = "225" + "0" + phone.slice(3);
    merchant = await ctx.db
      .query("merchants")
      .withIndex("by_phone", (q: any) => q.eq("phone", corrected))
      .unique();
  }
  return merchant;
}

/**
 * Contexte complet d'un tour de chat (parité de l'amont de
 * `chat_service.handle_incoming_message` + `_get_or_create_conversation`).
 *
 * Renvoie en un seul appel : marchand (+ disponibilité), produit (par code,
 * enrichi du statut stock), conversation (active ou récemment clôturée), tous
 * les messages, et les faits mémoire LTM du client.
 *
 * Lecture seule : la CRÉATION de conversation se fait dans `commitTurn`
 * (transactionnel) pour ne pas créer une conversation si aucun message n'est
 * finalement persisté. `getContext` renvoie `conversation: null` quand il faut
 * créer (le Python passe `productCode` à `commitTurn`).
 */
export const getContext = query({
  args: {
    internalKey: v.string(),
    merchantPhone: v.string(),
    clientPhone: v.string(),
    productCode: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);

    const merchant = await resolveMerchant(ctx, args.merchantPhone);
    if (!merchant) return { merchant: null };

    // Disponibilité (mode absence) — parité `is_merchant_available`.
    const away = merchant.awayModeEnabled === true;

    let product: Doc<"products"> | null = null;
    let conversation: Doc<"conversations"> | null = null;

    if (args.productCode) {
      product = await ctx.db
        .query("products")
        .withIndex("by_code", (q) => q.eq("code", args.productCode!.toUpperCase()))
        .unique();
      if (product && product.merchantId === merchant._id) {
        conversation = await ctx.db
          .query("conversations")
          .withIndex("by_merchant", (q) => q.eq("merchantId", merchant._id))
          .filter((q) =>
            q.and(
              q.eq(q.field("clientPhone"), args.clientPhone),
              q.eq(q.field("productId"), product!._id),
            ),
          )
          .order("desc")
          .first();
        if (
          conversation &&
          ["ended", "completed", "abandoned"].includes(conversation.status)
        ) {
          conversation = null; // close & recreate côté commitTurn
        }
      } else {
        product = null;
      }
    } else {
      // Pas de code : conversation active la plus récente du client.
      conversation = await ctx.db
        .query("conversations")
        .withIndex("by_merchant", (q) => q.eq("merchantId", merchant._id))
        .filter((q) =>
          q.and(
            q.eq(q.field("clientPhone"), args.clientPhone),
            q.neq(q.field("status"), "ended"),
            q.neq(q.field("status"), "completed"),
            q.neq(q.field("status"), "abandoned"),
          ),
        )
        .order("desc")
        .first();
      if (conversation) {
        product = await ctx.db.get(conversation.productId);
      }
    }

    let history: Doc<"messages">[] = [];
    if (conversation) {
      history = await ctx.db
        .query("messages")
        .withIndex("by_conversation", (q) =>
          q.eq("conversationId", conversation!._id),
        )
        .collect();
    }

    // Faits mémoire LTM (parité `client_history.get_memory_facts`).
    const clientHistory = await ctx.db
      .query("clientHistory")
      .withIndex("by_merchant_client", (q) =>
        q.eq("merchantId", merchant._id).eq("clientPhone", args.clientPhone),
      )
      .unique();

    const productPublic = product
      ? (() => {
          const { imageEmbedding: _omit, ...rest } = product;
          return rest;
        })()
      : null;

    return {
      merchant,
      away,
      product: productPublic,
      stockStatus: product ? stockStatus(product) : null,
      conversation,
      history,
      memoryFacts: clientHistory?.memoryFacts ?? null,
      clientHistory,
    };
  },
});

/**
 * Persistance ATOMIQUE d'un tour de chat (parité du write-path de
 * `handle_incoming_message`). En une seule transaction :
 *   - upsert conversation (création si `productId` fourni et pas de
 *     `conversationId`) ;
 *   - insert message client + message bot ;
 *   - maj statut + offre courante ;
 *   - incrément stats messages du jour.
 *
 * Renvoie l'`_id` de conversation (utile quand elle vient d'être créée) et le
 * nombre de messages persistés.
 */
export const commitTurn = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    conversationId: v.optional(v.id("conversations")),
    // Pour création de conversation si conversationId absent :
    productId: v.optional(v.id("products")),
    clientPhone: v.string(),
    clientMessage: v.string(),
    botMessage: v.optional(v.string()),
    newStatus: v.optional(v.string()),
    currentOffer: v.optional(v.number()),
    // Fermer une ancienne conversation pending et en recréer une (re-mention #code).
    closeConversationId: v.optional(v.id("conversations")),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const now = Date.now();

    // Fermeture éventuelle d'une conversation pending re-mentionnée.
    if (args.closeConversationId) {
      await ctx.db.patch(args.closeConversationId, {
        status: "completed",
        updatedAt: now,
      });
    }

    // Résolution / création de la conversation.
    let conversationId = args.conversationId ?? null;
    let created = false;
    if (!conversationId) {
      if (!args.productId) {
        throw new Error("commitTurn : productId requis pour créer une conversation");
      }
      conversationId = await ctx.db.insert("conversations", {
        merchantId: args.merchantId,
        productId: args.productId,
        clientPhone: args.clientPhone,
        status: "active",
        updatedAt: now,
      });
      created = true;
      // Stats : nouvelle conversation + event analytics.
      await bumpDailyStat(ctx, args.merchantId, "conversationsCount", 1);
      await ctx.db.insert("analyticsEvents", {
        merchantId: args.merchantId,
        eventType: "new_conversation",
        productId: args.productId,
        conversationId,
        clientPhone: args.clientPhone,
      });
    }

    // Message client.
    await ctx.db.insert("messages", {
      conversationId,
      content: args.clientMessage,
      isFromClient: true,
    });
    let persisted = 1;

    // Stats messages.
    await bumpDailyStat(ctx, args.merchantId, "messagesCount", 1);

    // Message bot (optionnel : pas de message si conversation terminée muette).
    if (args.botMessage) {
      await ctx.db.insert("messages", {
        conversationId,
        content: args.botMessage,
        isFromClient: false,
      });
      persisted += 1;
    }

    // Maj statut / offre.
    const patch: Partial<Doc<"conversations">> = { updatedAt: now };
    if (args.newStatus) patch.status = args.newStatus as Doc<"conversations">["status"];
    if (args.currentOffer !== undefined) patch.currentOffer = args.currentOffer;
    await ctx.db.patch(conversationId, patch);

    return { conversationId, created, messagesPersisted: persisted };
  },
});

/**
 * Incrémente (ou crée) une stat quotidienne du marchand pour le jour courant.
 * Parité `stats.increment_messages` / `increment_conversations` mais sans race :
 * un seul upsert dans la transaction.
 */
async function bumpDailyStat(
  ctx: { db: any },
  merchantId: Id<"merchants">,
  field: "messagesCount" | "conversationsCount" | "salesCount",
  delta: number,
): Promise<void> {
  const date = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  const existing = await ctx.db
    .query("dailyStats")
    .withIndex("by_merchant_date", (q: any) =>
      q.eq("merchantId", merchantId).eq("date", date),
    )
    .unique();
  if (existing) {
    await ctx.db.patch(existing._id, {
      [field]: (existing[field] ?? 0) + delta,
    });
  } else {
    await ctx.db.insert("dailyStats", {
      merchantId,
      date,
      [field]: delta,
    });
  }
}
