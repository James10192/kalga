import { query } from "./_generated/server";
import { v } from "convex/values";

/**
 * Lectures publiques pour le STOREFRONT (plan 007), {slug}.kalga.app.
 *
 * Toutes les queries ici sont PUBLIQUES (page boutique, pas d'auth) et
 * read-only. Elles n'exposent que ce qui doit être visible d'un client :
 * identité boutique + catalogue actif. Jamais de prix plancher (minPrice),
 * de marge, de coordonnées privées ou d'embeddings.
 *
 * Résolution tenant : ici par {slug} (dev path-based /boutique/:slug).
 * En prod (plan 009), le wildcard {slug}.kalga.app mappera le hostname
 * (x-forwarded-host) vers ce même slug : la query reste identique.
 */

/** Forme publique d'un produit (catalogue) — pas de minPrice ni d'embedding. */
const toPublicProduct = (p: {
  _id: string;
  name: string;
  code: string;
  price: number;
  description?: string;
  imagePath?: string;
  groupId?: string;
  variantName?: string;
  stockQuantity?: number;
  lowStockThreshold?: number;
}) => ({
  id: p._id,
  name: p.name,
  code: p.code,
  price: p.price,
  description: p.description ?? null,
  imagePath: p.imagePath ?? null,
  groupId: p.groupId ?? null,
  variantName: p.variantName ?? null,
  stockQuantity: p.stockQuantity ?? -1,
  lowStockThreshold: p.lowStockThreshold ?? 5,
});

/** Forme publique d'un marchand — uniquement la vitrine (pas de coords privées). */
const toPublicMerchant = (m: {
  _id: string;
  name: string;
  phone: string;
  slug: string;
  businessName?: string;
  tagline?: string;
  about?: string;
  logoPath?: string;
  bannerPath?: string;
  paymentMethods?: string;
}) => ({
  id: m._id,
  name: m.businessName ?? m.name,
  phone: m.phone,
  slug: m.slug,
  tagline: m.tagline ?? null,
  about: m.about ?? null,
  logoPath: m.logoPath ?? null,
  bannerPath: m.bannerPath ?? null,
  paymentMethods: m.paymentMethods ?? null,
});

/**
 * Vitrine complète d'une boutique par slug : marchand public + catalogue actif.
 * Une seule query pour la page catalogue (SSR, payload léger).
 * Renvoie `null` si le slug n'existe pas (la route affichera un 404 soigné).
 */
export const getStorefront = query({
  args: { slug: v.string() },
  handler: async (ctx, args) => {
    const merchant = await ctx.db
      .query("merchants")
      .withIndex("by_slug", (q) => q.eq("slug", args.slug))
      .unique();
    if (!merchant) return null;

    const products = await ctx.db
      .query("products")
      .withIndex("by_merchant", (q) => q.eq("merchantId", merchant._id))
      .collect();

    const active = products
      .filter((p) => p.isActive !== false)
      .map(toPublicProduct);

    return {
      merchant: toPublicMerchant(merchant),
      products: active,
    };
  },
});

/**
 * Détail d'un produit pour la page produit publique, scopé au slug du marchand
 * (empêche d'accéder à un produit d'un autre marchand via un id deviné).
 * Renvoie aussi quelques produits similaires (même boutique, hors variantes
 * du même produit) et le marchand public (pour le bouton WhatsApp + header).
 * `null` si introuvable / hors boutique.
 */
export const getProduct = query({
  // productId en string (pas v.id) : un id malformé dans l'URL ne doit PAS
  // crasher le SSR (validator), mais afficher la page « introuvable » soignée.
  args: { slug: v.string(), productId: v.string() },
  handler: async (ctx, args) => {
    const merchant = await ctx.db
      .query("merchants")
      .withIndex("by_slug", (q) => q.eq("slug", args.slug))
      .unique();
    if (!merchant) return null;

    const productId = ctx.db.normalizeId("products", args.productId);
    if (!productId) return null;

    const product = await ctx.db.get(productId);
    if (
      !product ||
      product.merchantId !== merchant._id ||
      product.isActive === false
    ) {
      return null;
    }

    const all = await ctx.db
      .query("products")
      .withIndex("by_merchant", (q) => q.eq("merchantId", merchant._id))
      .collect();

    // Variantes du même produit (même groupId, hors lui-même).
    const variants = product.groupId
      ? all.filter(
          (p) =>
            p.isActive !== false &&
            p.groupId === product.groupId &&
            p._id !== product._id,
        )
      : [];

    // Produits similaires : autres groupes / autres produits actifs.
    const seenGroup = new Set<string>();
    const similar = all
      .filter(
        (p) =>
          p.isActive !== false &&
          p._id !== product._id &&
          (!product.groupId || p.groupId !== product.groupId),
      )
      .filter((p) => {
        const key = p.groupId ?? p._id;
        if (seenGroup.has(key)) return false;
        seenGroup.add(key);
        return true;
      })
      .slice(0, 6)
      .map(toPublicProduct);

    return {
      merchant: toPublicMerchant(merchant),
      product: toPublicProduct(product),
      variants: variants.map(toPublicProduct),
      similar,
    };
  },
});
