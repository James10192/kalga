import { internalMutation } from "./_generated/server";
import type { Id } from "./_generated/dataModel";

/**
 * Seed démo idempotent (plan 002, décision D10 : pas de migration, on re-seed).
 *
 * Crée un marchand démo (slug `demo`) avec un catalogue, des conversations et
 * les enregistrements d'abonnement/activation. Relançable : si le marchand
 * `demo` existe déjà, toutes ses données scopées sont supprimées puis recréées.
 *
 * Lancer : `npx convex run seed:run`
 */
export const run = internalMutation({
  args: {},
  handler: async (ctx) => {
    const now = Date.now();
    const day = 24 * 60 * 60 * 1000;

    // ── Idempotence : purge du marchand `demo` et de toutes ses données ────────
    const existing = await ctx.db
      .query("merchants")
      .withIndex("by_slug", (q) => q.eq("slug", "demo"))
      .unique();

    if (existing) {
      const mId = existing._id;

      // Messages d'abord (scopés par conversation, pas par merchant) :
      // on supprime les messages de chaque conversation du marchand avant
      // de supprimer les conversations elles-mêmes (pas d'orphelins).
      const convs = await ctx.db
        .query("conversations")
        .withIndex("by_merchant", (q) => q.eq("merchantId", mId))
        .collect();
      for (const conv of convs) {
        const msgs = await ctx.db
          .query("messages")
          .withIndex("by_conversation", (q) =>
            q.eq("conversationId", conv._id),
          )
          .collect();
        for (const msg of msgs) await ctx.db.delete(msg._id);
      }

      // Tables scopées par merchantId via index by_merchant
      for (const table of [
        "products",
        "categories",
        "conversations",
        "clientHistory",
        "knowledgeBase",
        "followUps",
        "conversationFeedback",
        "productWaitlist",
        "stockEvents",
        "dailyStats",
        "analyticsEvents",
        "subscriptions",
        "activationCodes",
        "storefrontOrders",
      ] as const) {
        const rows = await ctx.db
          .query(table)
          .withIndex("by_merchant", (q) => q.eq("merchantId", mId))
          .collect();
        for (const row of rows) await ctx.db.delete(row._id);
      }

      await ctx.db.delete(mId);
    }

    // ── Marchand démo ─────────────────────────────────────────────────────────
    const merchantId = await ctx.db.insert("merchants", {
      name: "Boutique Démo",
      phone: "2250700000000",
      slug: "demo",
      businessName: "Boutique Démo KALGA",
      address: "Cocody, Abidjan",
      awayModeEnabled: false,
      botTone: "casual",
      botStyle: "flexible",
      botCatchphrase: "On trouve toujours un terrain d'entente !",
      paymentMethods: JSON.stringify(["wave", "orange_money", "cash"]),
      stockAlertDays: 3,
      stockAlertsEnabled: true,
      waitlistEnabled: true,
      lowStockAlertGlobal: 5,
      tagline: "La mode à petit prix",
      about: "Boutique de démonstration pour la plateforme KALGA.",
    });

    // ── Catégories ────────────────────────────────────────────────────────────
    await ctx.db.insert("categories", {
      merchantId,
      name: "Chaussures",
      icon: "👟",
      color: "#16a34a",
    });
    await ctx.db.insert("categories", {
      merchantId,
      name: "Vêtements",
      icon: "👕",
      color: "#667eea",
    });

    // ── Produits (4 dont 1 out_of_stock, 1 low_stock) ─────────────────────────
    // Sneakers : stock ok (illimité = -1)
    const sneakers = await ctx.db.insert("products", {
      merchantId,
      name: "Sneakers Blanches",
      code: "SNK01",
      price: 25000,
      minPrice: 20000,
      description: "Baskets blanches tendance, toutes tailles.",
      isActive: true,
      outOfStockMode: "waitlist",
      stockQuantity: -1, // illimité
      lowStockThreshold: 5,
      isAvailable: true,
      imageEmbedding: undefined, // rempli par le pipeline vision en 004
    });

    // Sac à main : stock bas (2 <= seuil 5)
    await ctx.db.insert("products", {
      merchantId,
      name: "Sac à Main Cuir",
      code: "SAC01",
      price: 18000,
      minPrice: 14000,
      description: "Sac à main en cuir véritable, marron.",
      isActive: true,
      outOfStockMode: "waitlist",
      stockQuantity: 2, // low_stock
      lowStockThreshold: 5,
      isAvailable: true,
    });

    // Montre : rupture (0)
    const watch = await ctx.db.insert("products", {
      merchantId,
      name: "Montre Classique",
      code: "MTR01",
      price: 35000,
      minPrice: 30000,
      description: "Montre élégante à bracelet métallique.",
      isActive: true,
      outOfStockMode: "waitlist",
      stockQuantity: 0, // out_of_stock
      lowStockThreshold: 5,
      isAvailable: false,
    });

    // T-shirt : stock ok (quantité finie au-dessus du seuil)
    await ctx.db.insert("products", {
      merchantId,
      name: "T-shirt Coton Bio",
      code: "TSH01",
      price: 8000,
      minPrice: 6500,
      description: "T-shirt 100% coton bio, plusieurs coloris.",
      isActive: true,
      outOfStockMode: "alert",
      stockQuantity: 40, // ok
      lowStockThreshold: 5,
      isAvailable: true,
    });

    // ── Conversations + messages ──────────────────────────────────────────────
    const conv1: Id<"conversations"> = await ctx.db.insert("conversations", {
      merchantId,
      productId: sneakers,
      clientPhone: "2250500000001",
      status: "negotiating",
      currentOffer: 22000,
      updatedAt: now,
    });
    await ctx.db.insert("messages", {
      conversationId: conv1,
      content: "Bonjour, c'est combien les sneakers SNK01 ?",
      isFromClient: true,
    });
    await ctx.db.insert("messages", {
      conversationId: conv1,
      content: "Bonjour ! Les Sneakers Blanches sont à 25 000 FCFA.",
      isFromClient: false,
    });
    await ctx.db.insert("messages", {
      conversationId: conv1,
      content: "Tu peux faire 22 000 ?",
      isFromClient: true,
    });

    const conv2: Id<"conversations"> = await ctx.db.insert("conversations", {
      merchantId,
      productId: watch,
      clientPhone: "2250500000002",
      status: "completed",
      currentOffer: 32000,
      updatedAt: now - day,
    });
    await ctx.db.insert("messages", {
      conversationId: conv2,
      content: "La montre MTR01 est dispo ?",
      isFromClient: true,
    });
    await ctx.db.insert("messages", {
      conversationId: conv2,
      content: "Oui, je vous la fais à 32 000 FCFA. Marché conclu !",
      isFromClient: false,
    });

    // ── Abonnement (trial) ────────────────────────────────────────────────────
    await ctx.db.insert("subscriptions", {
      merchantId,
      plan: "trial",
      status: "active",
      startDate: now,
      trialEndsAt: now + 14 * day,
      messagesLimit: 500,
      messagesUsed: 5,
      productsLimit: 10,
      updatedAt: now,
    });

    // ── Code d'activation (pending) ───────────────────────────────────────────
    await ctx.db.insert("activationCodes", {
      merchantId,
      code: "DEMO2026",
      status: "pending",
      expiresAt: now + 30 * day,
    });

    return {
      merchantId,
      slug: "demo",
      products: 4,
      conversations: 2,
    };
  },
});
