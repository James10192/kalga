import { mutation, internalMutation, internalAction } from "../_generated/server";
import { internal } from "../_generated/api";
import { v } from "convex/values";
import type { Doc, Id } from "../_generated/dataModel";
import { assertInternalKey } from "./guard";

// `scheduleFollowup` / `cancelFollowups` : publiques, gardées par `internalKey`
// (appelées par Python). Les helpers `sendFollowup` (action scheduler),
// `finalizeFollowup`, `prepareFollowup` restent en visibilité interne : ils ne
// sont déclenchés que par le scheduler Convex, jamais par un client externe.

/**
 * Relances automatiques via le SCHEDULER Convex (`ctx.scheduler.runAfter`).
 *
 * Remplace `followup_service.py` :
 *  - plus de boucle `while True: asyncio.sleep(60)` (le scheduler Convex déclenche
 *    l'envoi à l'échéance exacte) ;
 *  - plus de race SELECT-puis-INSERT : le dédup + insert + planification sont dans
 *    UNE seule mutation transactionnelle (`scheduleFollowup`).
 *
 * Délais (h) : step 1 -> 2h, step 2 -> 24h, step 3 -> 48h.
 * Messages : templates aléatoires par step (parité des templates Python).
 */

const DELAYS_MS: Record<number, number> = {
  1: 2 * 60 * 60 * 1000,
  2: 24 * 60 * 60 * 1000,
  3: 48 * 60 * 60 * 1000,
};

const TEMPLATES: Record<number, string[]> = {
  1: [
    "Hey ! Tu as vu le {product} ? Il te plaît ?",
    "Salut ! Tu réfléchis encore pour le {product} ?",
    "Coucou ! Des questions sur le {product} ?",
    "Hello ! Le {product} est toujours dispo si ça t'intéresse !",
  ],
  2: [
    "Juste pour te dire, le {product} part vite ! Tu veux qu'on en parle ?",
    "Hello ! Je peux te faire un prix spécial sur le {product} si tu te décides aujourd'hui !",
    "Salut ! Le {product} est encore disponible mais j'ai d'autres clients intéressés...",
  ],
  3: [
    "Dernière chance pour le {product} ! Après je ne pourrai plus garantir le prix.",
    "C'est ma dernière relance pour le {product}. Fais-moi signe si t'es toujours intéressé !",
  ],
};

function pickMessage(step: number, productName: string): string {
  const pool = TEMPLATES[step] ?? TEMPLATES[1];
  const tpl = pool[Math.floor(Math.random() * pool.length)];
  return tpl.replace("{product}", productName);
}

/**
 * Planifie une relance (parité `schedule_follow_up`), sans race.
 * Dédup atomique : si une relance `pending` existe déjà pour la conversation, on
 * renvoie sans rien créer. Sinon insert + `scheduler.runAfter(delay, sendFollowup)`.
 */
export const scheduleFollowup = mutation({
  args: {
    internalKey: v.string(),
    conversationId: v.id("conversations"),
    merchantId: v.id("merchants"),
    merchantPhone: v.string(),
    clientPhone: v.string(),
    productName: v.string(),
    step: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const step = args.step ?? 1;
    if (step > 3) return { scheduled: false, reason: "max_step" };

    // Dédup atomique : une seule relance pending par conversation.
    const existing = await ctx.db
      .query("followUps")
      .withIndex("by_conversation", (q) =>
        q.eq("conversationId", args.conversationId),
      )
      .filter((q) => q.eq(q.field("status"), "pending"))
      .first();
    if (existing) return { scheduled: false, reason: "already_pending" };

    const delay = DELAYS_MS[step] ?? DELAYS_MS[1];
    const scheduledAt = Date.now() + delay;
    const message = pickMessage(step, args.productName);

    const followUpId = await ctx.db.insert("followUps", {
      conversationId: args.conversationId,
      merchantId: args.merchantId,
      clientPhone: args.clientPhone,
      scheduledAt,
      message,
      status: "pending",
    });

    // Le scheduler Convex déclenche l'envoi à l'échéance exacte (pas de polling).
    await ctx.scheduler.runAfter(delay, internal.internal.followups.sendFollowup, {
      followUpId,
      merchantPhone: args.merchantPhone,
      step,
    });

    return { scheduled: true, followUpId };
  },
});

/**
 * Annule les relances pending d'une conversation (parité `cancel_follow_ups`),
 * appelé quand le client répond. Les tâches scheduler déjà programmées
 * vérifieront le statut `cancelled` avant d'envoyer (no-op).
 */
export const cancelFollowups = mutation({
  args: {
    internalKey: v.string(),
    conversationId: v.id("conversations"),
  },
  handler: async (ctx, args) => {
    assertInternalKey(args.internalKey);
    const pending = await ctx.db
      .query("followUps")
      .withIndex("by_conversation", (q) =>
        q.eq("conversationId", args.conversationId),
      )
      .filter((q) => q.eq(q.field("status"), "pending"))
      .collect();
    for (const fu of pending) {
      await ctx.db.patch(fu._id, { status: "cancelled" });
    }
    return { cancelled: pending.length };
  },
});

/**
 * Mutation interne appelée par l'action d'envoi : (re)vérifie le statut conv,
 * persiste le message bot + marque la relance, planifie le step suivant.
 * Renvoie le payload d'envoi (ou null si la relance ne doit pas partir).
 */
export const finalizeFollowup = internalMutation({
  args: {
    followUpId: v.id("followUps"),
    sent: v.boolean(),
    step: v.number(),
    merchantPhone: v.string(),
  },
  handler: async (ctx, args) => {
    const fu = await ctx.db.get(args.followUpId);
    if (!fu || fu.status !== "pending") return null;

    if (!args.sent) {
      await ctx.db.patch(args.followUpId, { status: "failed" });
      return null;
    }

    await ctx.db.patch(args.followUpId, {
      status: "sent",
      sentAt: Date.now(),
    });
    await ctx.db.insert("messages", {
      conversationId: fu.conversationId,
      content: fu.message,
      isFromClient: false,
    });

    // Chaîne le step suivant (les conversations encore vivantes).
    const conv = await ctx.db.get(fu.conversationId);
    if (conv && args.step < 3) {
      const product = await ctx.db.get(conv.productId);
      const productName = product?.name ?? "ce produit";
      await ctx.scheduler.runAfter(
        DELAYS_MS[args.step + 1],
        internal.internal.followups.sendFollowup,
        {
          followUpId: await ctx.db.insert("followUps", {
            conversationId: fu.conversationId,
            merchantId: fu.merchantId,
            clientPhone: fu.clientPhone,
            scheduledAt: Date.now() + DELAYS_MS[args.step + 1],
            message: pickMessage(args.step + 1, productName),
            status: "pending",
          }),
          merchantPhone: args.merchantPhone,
          step: args.step + 1,
        },
      );
    }
    return { sent: true };
  },
});

/**
 * Action d'envoi déclenchée par le scheduler à l'échéance. Re-vérifie le statut
 * conv (vivant), appelle le bridge WhatsApp (`X-Internal-Key`), puis finalise.
 * Les actions n'accèdent pas à `ctx.db` : tout passe par mutations internes.
 */
export const sendFollowup = internalAction({
  args: {
    followUpId: v.id("followUps"),
    merchantPhone: v.string(),
    step: v.number(),
  },
  handler: async (ctx, args) => {
    // Charge la relance + vérifie que la conversation est encore vivante.
    const ready = await ctx.runMutation(
      internal.internal.followups.prepareFollowup,
      { followUpId: args.followUpId },
    );
    if (!ready) return; // annulée / conv terminée / inexistante

    const bridgeUrl = process.env.KALGA_WHATSAPP_URL ?? "http://localhost:3001";
    const internalKey = process.env.INTERNAL_API_KEY ?? "";
    let sent = false;
    try {
      const res = await fetch(`${bridgeUrl}/send`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(internalKey ? { "X-Internal-Key": internalKey } : {}),
        },
        body: JSON.stringify({
          merchant_phone: args.merchantPhone,
          to: ready.clientPhone,
          message: ready.message,
        }),
      });
      sent = res.ok;
    } catch {
      sent = false;
    }

    await ctx.runMutation(internal.internal.followups.finalizeFollowup, {
      followUpId: args.followUpId,
      sent,
      step: args.step,
      merchantPhone: args.merchantPhone,
    });
  },
});

/**
 * Vérifie qu'une relance peut partir (statut pending + conversation vivante).
 * Renvoie {clientPhone, message} ou null. Annule la relance si conv terminée.
 */
export const prepareFollowup = internalMutation({
  args: { followUpId: v.id("followUps") },
  handler: async (ctx, args) => {
    const fu = await ctx.db.get(args.followUpId);
    if (!fu || fu.status !== "pending") return null;
    const conv = await ctx.db.get(fu.conversationId);
    const alive = conv && ["active", "negotiating", "agreed"].includes(conv.status);
    if (!alive) {
      await ctx.db.patch(args.followUpId, { status: "cancelled" });
      return null;
    }
    return { clientPhone: fu.clientPhone, message: fu.message };
  },
});
