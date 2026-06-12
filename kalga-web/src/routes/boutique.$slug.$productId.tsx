import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"
import { useQuery } from "convex/react"
import { ArrowLeft, MessageCircle, Store } from "lucide-react"
import { api } from "../../convex/_generated/api"
import {
  ImagePlaceholder,
  Price,
  StockBadge,
  StoreFooter,
  StoreHeader,
  resolveImageUrl,
  storeStock,
  waLink,
  type PublicMerchant,
  type PublicProduct,
} from "@/components/storefront"

/**
 * STOREFRONT public — détail d'un produit. /boutique/:slug/:productId
 *
 * Page PUBLIQUE, SSR, zéro chrome d'app. Grandes photos (placeholder si pas
 * d'image), prix FCFA, description, variantes éventuelles, GROS bouton vert
 * « Commander sur WhatsApp » (lien wa.me vers le numéro du marchand avec un
 * message pré-rempli mentionnant le produit). Section produits similaires.
 *
 * Résolution tenant par {slug} (dev path-based). En prod (009), le wildcard
 * {slug}.kalga.app mappera le hostname vers ce slug ; getProduct ne change pas.
 */
export const Route = createFileRoute("/boutique/$slug/$productId")({
  head: () => ({
    meta: [{ title: "Produit · KALGA" }],
  }),
  component: ProductDetail,
})

function ProductDetail() {
  const { slug, productId } = Route.useParams()
  const data = useQuery(api.storefront.getProduct, {
    slug,
    productId,
  })

  if (data === undefined) return <DetailSkeleton />
  if (data === null) return <ProductNotFound slug={slug} />

  return (
    <DetailContent
      merchant={data.merchant}
      product={data.product}
      variants={data.variants}
      similar={data.similar}
    />
  )
}

function DetailContent({
  merchant,
  product,
  variants,
  similar,
}: {
  merchant: PublicMerchant
  product: PublicProduct
  variants: PublicProduct[]
  similar: PublicProduct[]
}) {
  // Variante sélectionnée : le produit affiché par défaut, ou une variante.
  const options = [product, ...variants]
  const [selectedId, setSelectedId] = useState(product.id)
  const selected = options.find((o) => o.id === selectedId) ?? product

  const stock = storeStock(selected)
  const soldOut = stock === "out_of_stock"
  const url = resolveImageUrl(selected.imagePath)

  const orderText = buildOrderMessage(merchant, selected)

  return (
    <div className="min-h-dvh bg-page">
      <StoreHeader merchant={merchant} />

      <main className="mx-auto max-w-[960px] px-5 pt-4">
        <Link
          to="/boutique/$slug"
          params={{ slug: merchant.slug }}
          className="inline-flex h-11 min-h-[48px] items-center gap-1.5 text-[14px] font-medium text-ink-muted transition active:scale-[0.98]"
        >
          <ArrowLeft className="h-4.5 w-4.5" strokeWidth={2.5} />
          Retour à la boutique
        </Link>

        <div className="mt-2 grid gap-6 md:grid-cols-2">
          {/* Grande photo */}
          <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-soft">
            <div className="relative aspect-square w-full">
              {url ? (
                <img
                  src={url}
                  alt={selected.name}
                  className="h-full w-full object-cover"
                />
              ) : (
                <ImagePlaceholder className="h-full w-full" />
              )}
              <span className="absolute left-3 top-3">
                <StockBadge stock={stock} />
              </span>
            </div>
          </div>

          {/* Infos + commande */}
          <div className="flex flex-col">
            <h2 className="font-display text-[24px] font-bold leading-tight tracking-tight">
              {selected.name}
            </h2>
            <p className="mt-2">
              <Price value={selected.price} size={32} />
            </p>

            {variants.length > 0 && (
              <div className="mt-5">
                <p className="text-[13px] font-medium text-ink-muted">
                  Variantes
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {options.map((o) => (
                    <button
                      key={o.id}
                      type="button"
                      onClick={() => setSelectedId(o.id)}
                      className={
                        o.id === selected.id
                          ? "inline-flex h-11 min-h-[48px] items-center rounded-full bg-ink px-4 text-[13.5px] font-semibold text-surface"
                          : "inline-flex h-11 min-h-[48px] items-center rounded-full border border-line bg-surface px-4 text-[13.5px] font-medium text-ink transition active:scale-[0.98]"
                      }
                    >
                      {o.variantName ?? o.name}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {selected.description && (
              <p className="mt-5 whitespace-pre-line text-[15px] leading-relaxed text-ink">
                {selected.description}
              </p>
            )}

            {/* GROS bouton vert WhatsApp (action primaire unique) */}
            <div className="mt-6 md:mt-auto md:pt-6">
              <a
                href={waLink(merchant.phone, orderText)}
                target="_blank"
                rel="noopener noreferrer"
                aria-disabled={soldOut}
                className={
                  soldOut
                    ? "pointer-events-none flex h-14 min-h-[48px] w-full items-center justify-center gap-2 rounded-full bg-line font-display text-[16px] font-bold text-ink-faint"
                    : "flex h-14 min-h-[48px] w-full items-center justify-center gap-2 rounded-full bg-primary font-display text-[16px] font-bold text-primary-foreground shadow-[0_8px_24px_-6px_rgba(22,163,74,.45)] transition active:scale-[0.98]"
                }
              >
                <MessageCircle className="h-5 w-5" strokeWidth={2.5} />
                {soldOut ? "Article en rupture" : "Commander sur WhatsApp"}
              </a>
              <p className="mt-2 text-center text-[12.5px] text-ink-faint">
                Vous discutez directement avec la boutique. Paiement Wave, Orange
                Money ou espèces.
              </p>
            </div>
          </div>
        </div>

        {similar.length > 0 && (
          <section className="mt-12">
            <h3 className="font-display text-[18px] font-bold tracking-tight">
              Articles similaires
            </h3>
            <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {similar.map((p) => (
                <SimilarCard key={p.id} merchantSlug={merchant.slug} product={p} />
              ))}
            </div>
          </section>
        )}
      </main>

      <StoreFooter merchant={merchant} />
    </div>
  )
}

/** Message WhatsApp pré-rempli mentionnant le produit. */
function buildOrderMessage(merchant: PublicMerchant, product: PublicProduct): string {
  return (
    `Bonjour ${merchant.name}, je suis intéressé(e) par « ${product.name} »` +
    ` (réf. ${product.code}) à ${formatFcfa(product.price)} FCFA.` +
    ` Est-il disponible ?`
  )
}

function formatFcfa(value: number): string {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 })
    .format(value)
    .replace(/ /g, " ")
}

function SimilarCard({
  merchantSlug,
  product,
}: {
  merchantSlug: string
  product: PublicProduct
}) {
  const url = resolveImageUrl(product.imagePath)
  return (
    <Link
      to="/boutique/$slug/$productId"
      params={{ slug: merchantSlug, productId: product.id }}
      className="overflow-hidden rounded-2xl border border-line bg-surface text-left shadow-soft transition active:scale-[0.99]"
    >
      <div className="aspect-square w-full">
        {url ? (
          <img src={url} alt={product.name} className="h-full w-full object-cover" />
        ) : (
          <ImagePlaceholder className="h-full w-full" />
        )}
      </div>
      <div className="p-3">
        <p className="truncate text-[13.5px] font-semibold">{product.name}</p>
        <p className="mt-0.5">
          <Price value={product.price} size={14} />
        </p>
      </div>
    </Link>
  )
}

function ProductNotFound({ slug }: { slug: string }) {
  return (
    <div className="grid min-h-dvh place-items-center bg-page px-6">
      <div className="max-w-sm text-center">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-primary-tint">
          <Store className="h-7 w-7 text-primary-deep" />
        </div>
        <p className="mt-4 font-display text-[20px] font-bold">Article introuvable</p>
        <p className="mt-2 text-[14px] text-ink-muted">
          Cet article n'existe plus ou n'appartient pas à cette boutique.
        </p>
        <Link
          to="/boutique/$slug"
          params={{ slug }}
          className="mt-5 inline-flex h-12 min-h-[48px] items-center rounded-full bg-primary px-5 font-display text-[14px] font-bold text-primary-foreground transition active:scale-[0.98]"
        >
          Retour à la boutique
        </Link>
      </div>
    </div>
  )
}

function DetailSkeleton() {
  return (
    <div className="min-h-dvh bg-page">
      <div className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-[960px] items-center gap-4 px-5 py-5">
          <div className="h-14 w-14 animate-pulse rounded-2xl bg-line" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-40 animate-pulse rounded bg-line" />
            <div className="h-3 w-28 animate-pulse rounded bg-line" />
          </div>
        </div>
      </div>
      <div className="mx-auto max-w-[960px] px-5 pt-6">
        <div className="grid gap-6 md:grid-cols-2">
          <div className="aspect-square w-full animate-pulse rounded-2xl bg-line" />
          <div className="space-y-4">
            <div className="h-7 w-56 animate-pulse rounded bg-line" />
            <div className="h-9 w-40 animate-pulse rounded bg-line" />
            <div className="h-4 w-full animate-pulse rounded bg-line" />
            <div className="h-14 w-full animate-pulse rounded-full bg-line" />
          </div>
        </div>
      </div>
    </div>
  )
}
