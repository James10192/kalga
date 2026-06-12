import { query } from "./_generated/server";
import { v } from "convex/values";
import type { Doc } from "./_generated/dataModel";

/**
 * Lectures pour l'écran Réglages du dashboard marchand (plan 006, read-only).
 *
 * Agrège, en un seul round-trip, ce dont l'écran Réglages a besoin :
 * abonnement (état actif/expiré, plan, échéance) + dernier code d'activation
 * (état du code émis). Les sections persona/boutique/connexion lisent
 * directement le doc `merchants` (via merchants.getBySlug côté route).
 *
 * Scoping tenant : tout passe par `merchantId` + index `by_merchant`.
 * NB : pas d'auth gating ici (OTP live + withOrg viendront en 003/004). La
 * signature `{ merchantId }` se branchera derrière withOrg sans casser le contrat.
 */

/** Abonnement le plus récent du marchand (1:1 logique, on prend le dernier créé). */
function pickSubscription(
  subs: Doc<"subscriptions">[],
): Doc<"subscriptions"> | null {
  if (subs.length === 0) return null;
  return [...subs].sort((a, b) => b._creationTime - a._creationTime)[0];
}

/** Dernier code d'activation émis (le plus récent). */
function pickActivationCode(
  codes: Doc<"activationCodes">[],
): Doc<"activationCodes"> | null {
  if (codes.length === 0) return null;
  return [...codes].sort((a, b) => b._creationTime - a._creationTime)[0];
}

/**
 * Synthèse abonnement + code d'activation pour l'écran Réglages.
 * Renvoie des objets aplatis (pas les docs bruts) pour un contrat de lecture stable.
 */
export const billingForMerchant = query({
  args: { merchantId: v.id("merchants") },
  handler: async (ctx, args) => {
    const subs = await ctx.db
      .query("subscriptions")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();
    const codes = await ctx.db
      .query("activationCodes")
      .withIndex("by_merchant", (q) => q.eq("merchantId", args.merchantId))
      .collect();

    const sub = pickSubscription(subs);
    const code = pickActivationCode(codes);

    return {
      subscription: sub
        ? {
            plan: sub.plan,
            status: sub.status,
            startDate: sub.startDate ?? null,
            endDate: sub.endDate ?? null,
            trialEndsAt: sub.trialEndsAt ?? null,
            messagesLimit: sub.messagesLimit ?? null,
            messagesUsed: sub.messagesUsed ?? null,
            productsLimit: sub.productsLimit ?? null,
          }
        : null,
      activationCode: code
        ? {
            code: code.code,
            status: code.status,
            usedAt: code.usedAt ?? null,
            expiresAt: code.expiresAt ?? null,
          }
        : null,
    };
  },
});
