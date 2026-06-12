import { createFileRoute, Link } from "@tanstack/react-router"
import { useMemo, useState } from "react"
import { useQuery } from "convex/react"
import { PackageOpen, Store } from "lucide-react"
import { api } from "../../convex/_generated/api"
import {
  ImagePlaceholder,
  Price,
  StockBadge,
  StoreFooter,
  StoreHeader,
  resolveImageUrl,
  storeStock,
  type PublicMerchant,
  type PublicProduct,
} from "@/components/storefront"

/**
 * STOREFRONT public — catalogue d'une boutique. /boutique/:slug
 *
 * Page PUBLIQUE (aucun provider auth, aucun chrome d'app). SSR pour le SEO :
 * le marchand + le catalogue sont résolus côté serveur via le provider Convex
 * (useQuery est rendu au SSR par TanStack Start + nitro).
 *
 * Résolution tenant : par {slug} en dev (path-based, testable en local).
 * En prod (plan 009), le wildcard {slug}.kalga.app mappera le hostname
 * (x-forwarded-host) vers ce même slug ; la query getStorefront ne change pas.
 */
export const Route = createFileRoute("/boutique/$slug")({
  head: ({ params }) => ({
    meta: [
      { title: `Boutique ${params.slug} · KALGA` },
      {
        name: "description",
        content: `Découvrez le catalogue de la boutique ${params.slug} et commandez sur WhatsApp.`,
      },
    ],
  }),
  component: StorefrontCatalogue,
})

function StorefrontCatalogue() {
  const { slug } = Route.useParams()
  const data = useQuery(api.storefront.getStorefront, { slug })

  if (data === undefined) return <CatalogueSkeleton />
  if (data === null) return <StoreNotFound slug={slug} />

  return <CatalogueContent merchant={data.merchant} products={data.products} />
}

function CatalogueContent({
  merchant,
  products,
}: {
  merchant: PublicMerchant
  products: PublicProduct[]
}) {
  // Une carte par produit "tête de groupe" : on replie les variantes (groupId)
  // sur le moins cher du groupe, et on garde les produits sans groupe tels quels.
  const cards = useMemo(() => collapseVariants(products), [products])

  // Filtres réels : "Tous" + "Disponibles" (dérivés du stock, pas de fake data).
  const [onlyAvailable, setOnlyAvailable] = useState(false)
  const visible = onlyAvailable
    ? cards.filter((c) => storeStock(c) !== "out_of_stock")
    : cards

  return (
    <div className="min-h-dvh bg-page">
      <StoreHeader merchant={merchant} />

      <main className="mx-auto max-w-[960px] px-5 pb-2 pt-5">
        {cards.length > 0 && (
          <div className="mb-4 flex gap-2 overflow-x-auto pb-1">
            <FilterChip active={!onlyAvailable} onClick={() => setOnlyAvailable(false)}>
              Tous les articles
            </FilterChip>
            <FilterChip active={onlyAvailable} onClick={() => setOnlyAvailable(true)}>
              Disponibles
            </FilterChip>
          </div>
        )}

        {cards.length === 0 ? (
          <CatalogueEmpty />
        ) : visible.length === 0 ? (
          <CatalogueEmpty available />
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {visible.map((p) => (
              <ProductGridCard key={p.id} merchantSlug={merchant.slug} product={p} />
            ))}
          </div>
        )}
      </main>

      <StoreFooter merchant={merchant} />
    </div>
  )
}

/** Réduit les variantes (même groupId) à une seule carte (le moins cher). */
function collapseVariants(products: PublicProduct[]): PublicProduct[] {
  const heads = new Map<string, PublicProduct>()
  const singles: PublicProduct[] = []
  for (const p of products) {
    if (!p.groupId) {
      singles.push(p)
      continue
    }
    const existing = heads.get(p.groupId)
    if (!existing || p.price < existing.price) heads.set(p.groupId, p)
  }
  return [...singles, ...heads.values()]
}

function ProductGridCard({
  merchantSlug,
  product,
}: {
  merchantSlug: string
  product: PublicProduct
}) {
  const url = resolveImageUrl(product.imagePath)
  const stock = storeStock(product)
  return (
    <Link
      to="/boutique/$slug/$productId"
      params={{ slug: merchantSlug, productId: product.id }}
      className="group overflow-hidden rounded-2xl border border-line bg-surface text-left shadow-soft transition active:scale-[0.99]"
    >
      <div className="relative aspect-square w-full">
        {url ? (
          <img src={url} alt={product.name} className="h-full w-full object-cover" />
        ) : (
          <ImagePlaceholder className="h-full w-full" />
        )}
        <span className="absolute left-2 top-2">
          <StockBadge stock={stock} />
        </span>
      </div>
      <div className="p-3">
        <p className="truncate text-[14px] font-semibold">{product.name}</p>
        <p className="mt-0.5">
          <Price value={product.price} />
        </p>
      </div>
    </Link>
  )
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        active
          ? "inline-flex h-11 min-h-[48px] shrink-0 items-center rounded-full bg-ink px-4 text-[13.5px] font-semibold text-surface transition"
          : "inline-flex h-11 min-h-[48px] shrink-0 items-center rounded-full border border-line bg-surface px-4 text-[13.5px] font-medium text-ink-muted transition active:scale-[0.98]"
      }
    >
      {children}
    </button>
  )
}

function CatalogueEmpty({ available = false }: { available?: boolean }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-10 text-center shadow-soft">
      <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-primary-tint">
        <PackageOpen className="h-6 w-6 text-primary-deep" />
      </div>
      <p className="mt-3 font-display text-[16px] font-bold">
        {available ? "Aucun article disponible" : "Boutique en préparation"}
      </p>
      <p className="mt-1 text-[13.5px] text-ink-muted">
        {available
          ? "Tous les articles sont en rupture pour le moment. Revenez bientôt."
          : "Cette boutique n'a pas encore publié d'articles. Revenez bientôt."}
      </p>
    </div>
  )
}

function StoreNotFound({ slug }: { slug: string }) {
  return (
    <div className="grid min-h-dvh place-items-center bg-page px-6">
      <div className="max-w-sm text-center">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-primary-tint">
          <Store className="h-7 w-7 text-primary-deep" />
        </div>
        <p className="mt-4 font-display text-[20px] font-bold">Boutique introuvable</p>
        <p className="mt-2 text-[14px] text-ink-muted">
          Aucune boutique ne correspond à « {slug} ». Vérifiez le lien.
        </p>
      </div>
    </div>
  )
}

function CatalogueSkeleton() {
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
      <div className="mx-auto max-w-[960px] px-5 pt-5">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="overflow-hidden rounded-2xl border border-line bg-surface shadow-soft"
            >
              <div className="aspect-square w-full animate-pulse bg-line" />
              <div className="space-y-2 p-3">
                <div className="h-4 w-24 animate-pulse rounded bg-line" />
                <div className="h-4 w-16 animate-pulse rounded bg-line" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
