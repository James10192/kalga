import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { authComponent, createAuth } from "./auth";
import { withOrg } from "./lib/withOrg";

/**
 * Lectures de base sur les marchands (read-only, plan 002).
 * L'écriture et le scoping multi-tenant Better Auth arrivent en 003/004.
 */

/** Normalise un nom en slug ASCII (a-z0-9-), pour {slug}.kalga.app. */
function slugify(input: string): string {
  return input
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "") // retire les accents (diacritiques combinants)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
}

/** Récupère un marchand par son slug ({slug}.kalga.app). */
export const getBySlug = query({
  args: { slug: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("merchants")
      .withIndex("by_slug", (q) => q.eq("slug", args.slug))
      .unique();
  },
});

/** Récupère un marchand par son numéro WhatsApp (le bridge identifie le marchand par là). */
export const getByPhone = query({
  args: { phone: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("merchants")
      .withIndex("by_phone", (q) => q.eq("phone", args.phone))
      .unique();
  },
});

/** Récupère un marchand par son _id. */
export const get = query({
  args: { merchantId: v.id("merchants") },
  handler: async (ctx, args) => {
    return await ctx.db.get(args.merchantId);
  },
});

/** Génère un slug unique dérivé de `base` (suffixe -2, -3... si déjà pris). */
async function uniqueSlug(
  ctx: { db: { query: (t: "merchants") => any } },
  base: string,
): Promise<string> {
  const root = slugify(base) || "boutique";
  let candidate = root;
  let i = 1;
  // boucle bornée : on cherche un slug libre
  while (i < 1000) {
    const existing = await ctx.db
      .query("merchants")
      .withIndex("by_slug", (q: any) => q.eq("slug", candidate))
      .unique();
    if (!existing) return candidate;
    i += 1;
    candidate = `${root}-${i}`;
  }
  throw new Error("Impossible de générer un slug unique");
}

/**
 * Pont marchand <-> organisation Better Auth.
 * Au signup d'un marchand (utilisateur authentifié), crée :
 *  1. une organization Better Auth (le créateur devient `owner`),
 *  2. la définit comme organisation active (active sur la session),
 *  3. un doc `merchants` lié (`organizationId` = id de l'org, `slug` unique).
 *
 * À appeler juste après la vérification OTP, depuis le client authentifié.
 * Idempotent : si un merchant existe déjà pour cet utilisateur/numéro, on le renvoie.
 *
 * Rappel client : recharger la page après cet appel (le JWT doit re-porter
 * `activeOrganizationId`).
 */
export const provisionMerchantOrg = mutation({
  args: {
    name: v.string(),
    phone: v.string(),
  },
  handler: async (ctx, args) => {
    const phone = args.phone.replace(/[^\d]/g, "");
    if (!phone) throw new Error("Numéro de téléphone invalide");

    // Idempotence : un marchand existe déjà pour ce numéro ?
    const existing = await ctx.db
      .query("merchants")
      .withIndex("by_phone", (q) => q.eq("phone", phone))
      .unique();
    if (existing) return { merchantId: existing._id, organizationId: existing.organizationId };

    const { auth, headers } = await authComponent.getAuth(createAuth, ctx);

    const slug = await uniqueSlug(ctx, args.name);

    // 1. Crée l'organisation (le user courant devient owner).
    const org = await auth.api.createOrganization({
      body: { name: args.name, slug },
      headers,
    });
    if (!org) throw new Error("Création de l'organisation échouée");
    const organizationId = org.id as string;

    // 2. La définit comme organisation active sur la session.
    await auth.api.setActiveOrganization({
      body: { organizationId },
      headers,
    });

    // 3. Crée le doc merchant lié.
    const merchantId = await ctx.db.insert("merchants", {
      name: args.name,
      phone,
      slug,
      organizationId,
    });

    return { merchantId, organizationId };
  },
});

/**
 * Marchand courant (scopé par l'organisation active via withOrg).
 * Sert de query de validation du flow auth (Step 8). Renvoie le statut
 * plutôt que de jeter, pour que la page de test puisse l'afficher sans crash.
 * Le scoping dur reste via withOrg (qui lève « No active organization »).
 */
export const current = query({
  args: {},
  handler: async (ctx) => {
    try {
      return await withOrg(ctx, async (octx) => ({
        status: "ok" as const,
        merchant: await octx.db.get(octx.merchantId),
      }));
    } catch (e) {
      return {
        status: "no-org" as const,
        reason: e instanceof Error ? e.message : String(e),
      };
    }
  },
});
