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
  // Fallback : le bridge envoie le numero REEL du compte WhatsApp connecte,
  // qui peut differer du `phone` d'inscription (cf. internal/merchant:getByPhone).
  if (!merchant) {
    merchant = await ctx.db
      .query("merchants")
      .withIndex("by_whatsapp_real_phone", (q: any) =>
        q.eq("whatsappRealPhone", phone),
      )
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
    // Variante sélectionnée (reply photo) — parité
    // `_find_and_save_selected_variant`. `null` autorisé pour effacer.
    selectedVariantId: v.optional(v.union(v.id("products"), v.null())),
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
    // Variante sélectionnée : `undefined` -> on ne touche pas ; `null` -> efface ;
    // un id -> on mémorise. (parité du dict local Python qui pose/efface le champ.)
    if (args.selectedVariantId !== undefined) {
      patch.selectedVariantId = args.selectedVariantId ?? undefined;
    }
    await ctx.db.patch(conversationId, patch);

    return { conversationId, created, messagesPersisted: persisted };
  },
});

/**
 * Comptabilisation ATOMIQUE d'une vente (parité du write-path de vente dans
 * `chat_service` : `stats.record_sale` + `stats.log_event('sale')` +
 * `client_history.record_purchase`). En une seule transaction :
 *   - bumpDailyStat salesCount +1 ET revenue + amount ;
 *   - upsert clientHistory (totalPurchases, totalSpent, moyenne mobile du
 *     discount, lastPurchaseDate / lastInteractionDate, catégories préférées) ;
 *   - insert analyticsEvents eventType "sale".
 */
export const recordSale = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    conversationId: v.id("conversations"),
    productId: v.id("products"),
    clientPhone: v.string(),
    amount: v.number(), // montant payé (= finalPrice en pratique)
    originalPrice: v.number(),
    finalPrice: v.number(),
    category: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const now = Date.now();

    // 1. Stats du jour : salesCount + revenue (parité `stats.record_sale`).
    await bumpDailyStat(ctx, args.merchantId, "salesCount", 1);
    await bumpDailyStat(ctx, args.merchantId, "revenue", args.amount);

    // 2. Historique client (parité `client_history.record_purchase`).
    // Discount % de cette vente (moyenne mobile côté historique).
    let discountPercent = 0;
    if (args.originalPrice > 0 && args.finalPrice < args.originalPrice) {
      discountPercent =
        ((args.originalPrice - args.finalPrice) / args.originalPrice) * 100;
    }

    const history = await ctx.db
      .query("clientHistory")
      .withIndex("by_merchant_client", (q) =>
        q.eq("merchantId", args.merchantId).eq("clientPhone", args.clientPhone),
      )
      .unique();

    if (history) {
      const prevPurchases = history.totalPurchases ?? 0;
      const newPurchases = prevPurchases + 1;
      const newSpent = (history.totalSpent ?? 0) + args.amount;
      // Moyenne mobile du discount (parité Python : (old*count + new)/newCount).
      const oldAvg = history.avgNegotiationDiscount ?? 0;
      const newAvg = (oldAvg * prevPurchases + discountPercent) / newPurchases;

      // Catégories préférées (JSON array de strings).
      let preferred: string[] = [];
      if (history.preferredCategories) {
        try {
          preferred = JSON.parse(history.preferredCategories) as string[];
        } catch {
          preferred = [];
        }
      }
      if (args.category && !preferred.includes(args.category)) {
        preferred.push(args.category);
      }

      await ctx.db.patch(history._id, {
        totalPurchases: newPurchases,
        totalSpent: newSpent,
        avgNegotiationDiscount: newAvg,
        lastPurchaseDate: now,
        lastInteractionDate: now,
        preferredCategories: preferred.length
          ? JSON.stringify(preferred)
          : history.preferredCategories,
        updatedAt: now,
      });
    } else {
      // Nouveau client (parité branche else `record_purchase`).
      const preferred = args.category ? [args.category] : [];
      await ctx.db.insert("clientHistory", {
        merchantId: args.merchantId,
        clientPhone: args.clientPhone,
        totalConversations: 1,
        totalPurchases: 1,
        totalSpent: args.amount,
        avgNegotiationDiscount: discountPercent,
        lastPurchaseDate: now,
        lastInteractionDate: now,
        preferredCategories: preferred.length
          ? JSON.stringify(preferred)
          : undefined,
        updatedAt: now,
      });
    }

    // 3. Event analytics (parité `stats.log_event('sale')`).
    await ctx.db.insert("analyticsEvents", {
      merchantId: args.merchantId,
      eventType: "sale",
      productId: args.productId,
      conversationId: args.conversationId,
      clientPhone: args.clientPhone,
      data: JSON.stringify({ price: args.finalPrice }),
    });

    return { recorded: true };
  },
});

/**
 * Flag automatique d'une question restée sans réponse adéquate
 * (parité `chat_service._auto_flag_unanswered`). Insère une ligne
 * conversationFeedback `auto_flagged`. Anti-spam : une seule entrée
 * `auto_flagged` par conversation.
 */
export const flagUnanswered = mutation({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    conversationId: v.id("conversations"),
    clientPhone: v.string(),
    question: v.string(), // message client non traité
    botResponse: v.optional(v.string()),
    notes: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);

    // Anti-spam : une seule entrée auto_flagged par conversation.
    const existing = await ctx.db
      .query("conversationFeedback")
      .withIndex("by_conversation", (q) =>
        q.eq("conversationId", args.conversationId),
      )
      .filter((q) => q.eq(q.field("feedbackType"), "auto_flagged"))
      .first();
    if (existing) return { flaggedId: null };

    const flaggedId = await ctx.db.insert("conversationFeedback", {
      conversationId: args.conversationId,
      merchantId: args.merchantId,
      clientPhone: args.clientPhone,
      clientMessage: args.question,
      botResponse: args.botResponse ?? "",
      feedbackType: "auto_flagged",
      notes: args.notes ?? "Auto-détecté: question sans réponse adéquate",
    });
    return { flaggedId };
  },
});

/**
 * Conversation récemment clôturée d'un client (parité
 * `conversation_repo.get_recent_closed`). Renvoie la conversation la plus
 * récente avec statut completed/ended dont `updatedAt` est dans la fenêtre
 * `withinHours` (défaut 48), sinon null. Permet au bot de rouvrir au lieu de
 * toujours recréer (le client qui revient retrouve son contexte).
 */
export const getRecentClosed = query({
  args: {
    internalKey: v.string(),
    merchantId: v.id("merchants"),
    clientPhone: v.string(),
    withinHours: v.optional(v.number()), // DEFAULT 48
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const withinHours = args.withinHours ?? 48;
    const cutoff = Date.now() - withinHours * 60 * 60 * 1000;

    const recent = await ctx.db
      .query("conversations")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .filter((q) =>
        q.and(
          q.eq(q.field("clientPhone"), args.clientPhone),
          q.or(
            q.eq(q.field("status"), "completed"),
            q.eq(q.field("status"), "ended"),
          ),
          q.gte(q.field("updatedAt"), cutoff),
        ),
      )
      .order("desc")
      .first();

    return recent ?? null;
  },
});

/**
 * Incrémente (ou crée) une stat quotidienne du marchand pour le jour courant.
 * Parité `stats.increment_messages` / `increment_conversations` / `record_sale`
 * mais sans race : un seul upsert dans la transaction.
 */
async function bumpDailyStat(
  ctx: { db: any },
  merchantId: Id<"merchants">,
  field: "messagesCount" | "conversationsCount" | "salesCount" | "revenue",
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
