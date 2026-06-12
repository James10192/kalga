import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

/**
 * KALGA — Schéma Convex (17 tables métier).
 *
 * Transposition du schéma SQLite (`kalga-api/app/database/connection.py`) vers Convex.
 * Convex devient la source de vérité unique (décision D3).
 *
 * Conventions :
 * - Les `id` auto-increment SQLite deviennent le `_id` natif Convex (non déclaré).
 * - Chaque document a automatiquement `_id` et `_creationTime` (epoch ms) — non déclarés.
 * - FK SQLite -> `v.id("table")`.
 * - Enums de statut -> `v.union(v.literal(...))` avec les VRAIES valeurs trouvées dans les repos/services.
 * - Timestamps applicatifs -> `v.number()` (epoch ms) ; on ne redéclare pas created_at (cf. `_creationTime`).
 * - Scoping tenant : chaque table métier porte `merchantId` + un index `by_merchant`.
 *
 * EXCLUES (gérées par Better Auth, plan 003) : `users`, `active_sessions`.
 */
export default defineSchema({
  // ───────────────────────────────────────────────────────────────────────────
  // 1. merchants — tenant / business
  // ───────────────────────────────────────────────────────────────────────────
  merchants: defineTable({
    name: v.string(),
    phone: v.string(), // numéro WhatsApp du bot — le bridge identifie le marchand par là (UNIQUE)
    // Pont multi-tenant Better Auth (peuplé en 003) + sous-domaine {slug}.kalga.app (D2)
    slug: v.string(), // UNIQUE (index by_slug)
    organizationId: v.optional(v.string()), // peuplé en 003
    businessName: v.optional(v.string()),
    address: v.optional(v.string()),
    latitude: v.optional(v.number()),
    longitude: v.optional(v.number()),
    awayModeEnabled: v.optional(v.boolean()), // DEFAULT 0
    workingHours: v.optional(v.string()), // JSON
    awayMessage: v.optional(v.string()),
    // Storefront [MIGR]
    logoPath: v.optional(v.string()),
    about: v.optional(v.string()),
    tagline: v.optional(v.string()),
    bannerPath: v.optional(v.string()),
    // Bot personnalisation [MIGR]
    botTone: v.optional(
      v.union(
        v.literal("casual"),
        v.literal("formal"),
        v.literal("friendly"),
        v.literal("professional"),
      ),
    ), // DEFAULT 'casual'
    botStyle: v.optional(
      v.union(
        v.literal("flexible"),
        v.literal("firm"),
        v.literal("playful"),
      ),
    ), // DEFAULT 'flexible'
    botCatchphrase: v.optional(v.string()),
    paymentMethods: v.optional(v.string()), // JSON
    // Stock alerts [MIGR]
    stockAlertDays: v.optional(v.number()), // DEFAULT 3
    stockAlertsEnabled: v.optional(v.boolean()), // DEFAULT 1
    waitlistEnabled: v.optional(v.boolean()), // DEFAULT 1
    lowStockAlertGlobal: v.optional(v.number()), // DEFAULT 5
  })
    .index("by_phone", ["phone"])
    .index("by_slug", ["slug"])
    .index("by_organization", ["organizationId"]),

  // ───────────────────────────────────────────────────────────────────────────
  // 2. products — catalogue
  // ───────────────────────────────────────────────────────────────────────────
  products: defineTable({
    merchantId: v.id("merchants"),
    name: v.string(),
    code: v.string(), // UNIQUE
    price: v.number(),
    minPrice: v.number(), // prix plancher négo
    description: v.optional(v.string()),
    imagePath: v.optional(v.string()),
    groupId: v.optional(v.string()), // regroupement variantes
    variantName: v.optional(v.string()),
    isActive: v.optional(v.boolean()), // DEFAULT 1
    // Embedding CLIP recherche visuelle (piège 1) :
    // - PAS de BLOB binaire, on stocke le vecteur en array de float64.
    // - PAS d'index vectoriel ici : le plan 004 ajoutera `.vectorIndex("by_embedding", ...)`.
    imageEmbedding: v.optional(v.array(v.float64())),
    // Stock [MIGR]
    outOfStockMode: v.optional(
      v.union(
        v.literal("waitlist"),
        v.literal("alert"),
        v.literal("suspend"),
        v.literal("preorder"),
      ),
    ), // DEFAULT 'waitlist'
    lastStockAlertAt: v.optional(v.number()),
    // stock_quantity : -1 = illimité (pas de décrément), 0 = rupture,
    // 0 < q <= lowStockThreshold = stock bas, q > seuil = ok.
    stockQuantity: v.optional(v.number()), // DEFAULT -1 (illimité)
    lowStockThreshold: v.optional(v.number()), // DEFAULT 5
    isAvailable: v.optional(v.boolean()), // DEFAULT 1
  })
    .index("by_merchant", ["merchantId"])
    .index("by_code", ["code"])
    .index("by_group", ["groupId"]),

  // ───────────────────────────────────────────────────────────────────────────
  // 3. categories — catalogue
  // ───────────────────────────────────────────────────────────────────────────
  categories: defineTable({
    merchantId: v.id("merchants"),
    name: v.string(),
    icon: v.optional(v.string()), // DEFAULT '📦'
    color: v.optional(v.string()), // DEFAULT '#667eea'
  })
    .index("by_merchant", ["merchantId"])
    .index("by_merchant_name", ["merchantId", "name"]), // UNIQUE(merchant_id, name)

  // ───────────────────────────────────────────────────────────────────────────
  // 4. conversations — chat
  // ───────────────────────────────────────────────────────────────────────────
  conversations: defineTable({
    merchantId: v.id("merchants"),
    productId: v.id("products"),
    clientPhone: v.string(),
    status: v.union(
      v.literal("active"), // default, initial
      v.literal("negotiating"), // négo prix en cours
      v.literal("agreed"), // accord trouvé
      v.literal("pending_delivery"), // vente conclue, livraison à venir (VIVANT)
      v.literal("pending_pickup"), // vente conclue, retrait boutique (VIVANT)
      v.literal("completed"), // vente finalisée (comptabilisée en stats)
      v.literal("abandoned"), // abandonnée par marchand
      v.literal("ended"), // clôturée par le bot
      v.literal("expired"), // cleanup auto après 7j
    ),
    currentOffer: v.optional(v.number()), // dernière offre prix en cours
    updatedAt: v.optional(v.number()), // epoch ms
  })
    .index("by_merchant", ["merchantId"])
    .index("by_client", ["clientPhone"])
    .index("by_status", ["status"]),

  // ───────────────────────────────────────────────────────────────────────────
  // 5. messages — chat
  // ───────────────────────────────────────────────────────────────────────────
  messages: defineTable({
    conversationId: v.id("conversations"),
    content: v.string(),
    isFromClient: v.boolean(), // true=client, false=bot/marchand
  }).index("by_conversation", ["conversationId"]),

  // ───────────────────────────────────────────────────────────────────────────
  // 6. clientHistory — mémoire LTM
  // ───────────────────────────────────────────────────────────────────────────
  clientHistory: defineTable({
    merchantId: v.id("merchants"),
    clientPhone: v.string(),
    totalConversations: v.optional(v.number()), // DEFAULT 0
    totalPurchases: v.optional(v.number()), // DEFAULT 0
    totalSpent: v.optional(v.number()), // DEFAULT 0
    avgNegotiationDiscount: v.optional(v.number()), // DEFAULT 0
    lastPurchaseDate: v.optional(v.number()),
    lastInteractionDate: v.optional(v.number()),
    preferredCategories: v.optional(v.string()), // JSON
    negotiationStyle: v.optional(v.string()), // DEFAULT 'normal' (dérivé dynamiquement, pas un enum fixe)
    notes: v.optional(v.string()),
    updatedAt: v.optional(v.number()),
    // Mémoire 3 couches (STM/LTM/épisodique) [MIGR]
    memoryFacts: v.optional(v.string()), // JSON — LTM faits sémantiques
    lastSessionSummary: v.optional(v.string()),
    preferences: v.optional(v.string()), // JSON
    conversationSummaries: v.optional(v.string()), // JSON — résumés épisodiques
  })
    .index("by_merchant", ["merchantId"])
    .index("by_client", ["clientPhone"])
    .index("by_merchant_client", ["merchantId", "clientPhone"]), // UNIQUE(merchant_id, client_phone)

  // ───────────────────────────────────────────────────────────────────────────
  // 7. knowledgeBase — mémoire
  // ───────────────────────────────────────────────────────────────────────────
  knowledgeBase: defineTable({
    merchantId: v.id("merchants"),
    question: v.string(),
    answer: v.string(),
    keywords: v.optional(v.string()), // mots-clés matching
    source: v.optional(v.string()), // DEFAULT 'human_reply'
    usageCount: v.optional(v.number()), // DEFAULT 0
  }).index("by_merchant", ["merchantId"]),

  // ───────────────────────────────────────────────────────────────────────────
  // 8. followUps — scheduler (réécrit en scheduler Convex en 004)
  // ───────────────────────────────────────────────────────────────────────────
  followUps: defineTable({
    conversationId: v.id("conversations"),
    merchantId: v.id("merchants"),
    clientPhone: v.string(),
    scheduledAt: v.number(), // NOT NULL — epoch ms
    message: v.string(),
    status: v.union(
      v.literal("pending"), // default — en attente d'envoi
      v.literal("sent"), // envoyée
      v.literal("cancelled"), // annulée car conv reprise
      v.literal("failed"), // échec envoi
    ),
    sentAt: v.optional(v.number()),
  })
    .index("by_merchant", ["merchantId"])
    .index("by_conversation", ["conversationId"])
    .index("by_scheduled", ["scheduledAt", "status"]),

  // ───────────────────────────────────────────────────────────────────────────
  // 9. conversationFeedback — chat
  // ───────────────────────────────────────────────────────────────────────────
  conversationFeedback: defineTable({
    conversationId: v.id("conversations"),
    merchantId: v.id("merchants"),
    clientPhone: v.string(),
    clientMessage: v.string(),
    botResponse: v.string(),
    feedbackType: v.union(
      v.literal("bad_response"), // default
      v.literal("good_response"),
      v.literal("auto_flagged"), // détecté automatiquement
    ),
    notes: v.optional(v.string()),
    kbEntryId: v.optional(v.id("knowledgeBase")), // lien vers knowledgeBase si corrigé
  })
    .index("by_merchant", ["merchantId"])
    .index("by_conversation", ["conversationId"]),

  // ───────────────────────────────────────────────────────────────────────────
  // 10. productWaitlist — catalogue
  // ───────────────────────────────────────────────────────────────────────────
  productWaitlist: defineTable({
    merchantId: v.id("merchants"),
    productId: v.id("products"),
    clientPhone: v.string(),
    clientName: v.optional(v.string()),
    status: v.union(
      v.literal("waiting"), // default — en file d'attente
      v.literal("notified"), // client notifié du restock
    ),
    conversationId: v.optional(v.id("conversations")),
    offeredPrice: v.optional(v.number()),
    notifiedAt: v.optional(v.number()),
    expiresAt: v.optional(v.number()),
    updatedAt: v.optional(v.number()),
  })
    .index("by_merchant", ["merchantId"])
    .index("by_product_status", ["productId", "status"])
    .index("by_client", ["clientPhone"]),

  // ───────────────────────────────────────────────────────────────────────────
  // 11. stockEvents — analytics (journal append-only)
  // ───────────────────────────────────────────────────────────────────────────
  stockEvents: defineTable({
    merchantId: v.id("merchants"),
    productId: v.id("products"),
    eventType: v.union(
      v.literal("restock"), // réappro
      v.literal("out_of_stock"), // passage rupture
      v.literal("sale"), // vente
    ),
    quantityDelta: v.number(), // variation signée
    quantityAfter: v.number(), // stock résultant
    conversationId: v.optional(v.id("conversations")),
    notes: v.optional(v.string()),
  })
    .index("by_merchant", ["merchantId"])
    .index("by_product", ["productId"]),

  // ───────────────────────────────────────────────────────────────────────────
  // 12. dailyStats — analytics
  // ───────────────────────────────────────────────────────────────────────────
  dailyStats: defineTable({
    merchantId: v.id("merchants"),
    date: v.string(), // ISO date (YYYY-MM-DD)
    conversationsCount: v.optional(v.number()), // DEFAULT 0
    messagesCount: v.optional(v.number()), // DEFAULT 0
    salesCount: v.optional(v.number()), // DEFAULT 0
    revenue: v.optional(v.number()), // DEFAULT 0
    uniqueClients: v.optional(v.number()), // DEFAULT 0
    avgResponseTime: v.optional(v.number()),
  })
    .index("by_merchant", ["merchantId"])
    .index("by_merchant_date", ["merchantId", "date"]), // UNIQUE(merchant_id, date)

  // ───────────────────────────────────────────────────────────────────────────
  // 13. analyticsEvents — analytics
  // ───────────────────────────────────────────────────────────────────────────
  analyticsEvents: defineTable({
    merchantId: v.id("merchants"),
    eventType: v.string(), // champ libre (NOT NULL) : new_conversation, sale, out_of_stock, out_of_stock_inquiry, ...
    productId: v.optional(v.id("products")), // pas de FK contrainte côté SQLite
    conversationId: v.optional(v.id("conversations")),
    clientPhone: v.optional(v.string()),
    data: v.optional(v.string()), // JSON payload
  })
    .index("by_merchant", ["merchantId"])
    .index("by_type", ["eventType"]),

  // ───────────────────────────────────────────────────────────────────────────
  // 14. subscriptions — abonnement (table métier, distincte de Better Auth)
  // ───────────────────────────────────────────────────────────────────────────
  subscriptions: defineTable({
    merchantId: v.id("merchants"), // UNIQUE (1:1)
    plan: v.union(
      v.literal("trial"), // default
      v.literal("starter"),
      v.literal("pro"),
      v.literal("enterprise"),
    ),
    status: v.union(
      v.literal("active"), // default
      v.literal("expired"),
    ),
    startDate: v.optional(v.number()),
    endDate: v.optional(v.number()),
    trialEndsAt: v.optional(v.number()),
    messagesLimit: v.optional(v.number()), // DEFAULT 500
    messagesUsed: v.optional(v.number()), // DEFAULT 0
    productsLimit: v.optional(v.number()), // DEFAULT 10
    features: v.optional(v.string()), // JSON
    updatedAt: v.optional(v.number()),
    paymentMethod: v.optional(v.string()), // [MIGR]
    paymentReference: v.optional(v.string()), // [MIGR]
    activatedBy: v.optional(v.string()), // [MIGR] — user id Better Auth (string)
  })
    .index("by_merchant", ["merchantId"])
    .index("by_status", ["status"]),

  // ───────────────────────────────────────────────────────────────────────────
  // 15. activationCodes — abonnement
  // ───────────────────────────────────────────────────────────────────────────
  activationCodes: defineTable({
    merchantId: v.id("merchants"),
    code: v.string(), // VARCHAR(8) UNIQUE
    status: v.union(
      v.literal("pending"), // default — code émis, non utilisé
      v.literal("used"), // consommé
      v.literal("expired"), // expiré ou remplacé
    ),
    usedAt: v.optional(v.number()),
    expiresAt: v.optional(v.number()),
    createdBy: v.optional(v.string()), // user id Better Auth (string)
  })
    .index("by_merchant", ["merchantId"])
    .index("by_code", ["code"])
    .index("by_status", ["status"]),

  // ───────────────────────────────────────────────────────────────────────────
  // 16. adminAuditLogs — admin
  // ───────────────────────────────────────────────────────────────────────────
  adminAuditLogs: defineTable({
    adminUserId: v.string(), // user id Better Auth (string)
    action: v.string(), // champ libre
    targetType: v.optional(v.string()), // ex: 'merchant', 'subscription'
    targetId: v.optional(v.string()),
    details: v.optional(v.string()), // JSON
    ipAddress: v.optional(v.string()),
  }).index("by_admin", ["adminUserId"]),

  // ───────────────────────────────────────────────────────────────────────────
  // 17. storefrontOrders — storefront
  // ───────────────────────────────────────────────────────────────────────────
  storefrontOrders: defineTable({
    merchantId: v.id("merchants"),
    productId: v.id("products"),
    clientName: v.string(),
    clientPhone: v.string(),
    message: v.optional(v.string()),
    // 'new' à l'insertion ; pas de whitelist d'enum côté backend SQLite -> champ libre.
    status: v.string(), // DEFAULT 'new'
  })
    .index("by_merchant", ["merchantId"])
    .index("by_status", ["status"]),
});
