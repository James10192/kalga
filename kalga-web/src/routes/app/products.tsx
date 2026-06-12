import { createFileRoute } from "@tanstack/react-router"
import { useQuery } from "convex/react"
import { Plus, PackageOpen } from "lucide-react"
import { api } from "../../../convex/_generated/api"
import {
  ProductCard,
  ProductCardSkeleton,
  stockState,
} from "@/components/dashboard"
import type { Doc } from "../../../convex/_generated/dataModel"

/**
 * Écran Produits du dashboard marchand (DIRECTION.md : les produits sont
 * visuels). Grille de ProductCard câblée aux données Convex LIVE du marchand
 * démo (slug `demo`) via api.products.listByMerchant. Pastille de stock dérivée
 * de stockQuantity / lowStockThreshold (illimité / bas / rupture). FAB
 * « + Ajouter ». État vide soigné. Skeletons pendant le chargement.
 *
 * Pas d'auth gating pour l'instant (OTP live + withOrg en 003/004) : la
 * résolution passe par le slug démo, exactement comme l'accueil. Structuré pour
 * brancher withOrg plus tard (remplacer la résolution par slug par le scoping
 * organisation active).
 */
export const Route = createFileRoute("/app/products")({
  component: ProductsPage,
})

const DEMO_SLUG = "demo"

type Product = Doc<"products">

/**
 * Résout l'URL d'image d'un produit. Le démo n'a pas d'images (placeholder
 * affiché). Si imagePath est une URL absolue on la passe telle quelle ; les
 * chemins relatifs (legacy /uploads) restent à brancher avec la base CDN/API.
 */
function resolveImageUrl(imagePath: string | undefined): string | null {
  if (!imagePath) return null
  if (/^https?:\/\//.test(imagePath)) return imagePath
  return null
}

function ProductsPage() {
  const merchant = useQuery(api.merchants.getBySlug, { slug: DEMO_SLUG })

  if (merchant === undefined) {
    return (
      <>
        <Header count={undefined} />
        <ProductsGridSkeleton />
        <AddFab />
      </>
    )
  }
  if (merchant === null) return <MerchantMissing />

  return <ProductsContent merchantId={merchant._id} />
}

function ProductsContent({ merchantId }: { merchantId: string }) {
  const products = useQuery(api.products.listByMerchant, {
    merchantId: merchantId as never,
  })

  // Catalogue actif uniquement (un produit désactivé n'apparaît pas en boutique).
  const visible =
    products?.filter((p) => p.isActive !== false) ?? products

  return (
    <>
      <Header count={visible?.length} />

      {visible === undefined ? (
        <ProductsGridSkeleton />
      ) : visible.length === 0 ? (
        <ProductsEmpty />
      ) : (
        <ProductsGrid products={visible} />
      )}

      <AddFab />
    </>
  )
}

function ProductsGrid({ products }: { products: Product[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 px-5 pb-28 pt-1">
      {products.map((p) => (
        <ProductCard
          key={p._id}
          name={p.name}
          price={p.price}
          imageUrl={resolveImageUrl(p.imagePath)}
          stock={stockState(p.stockQuantity, p.lowStockThreshold)}
        />
      ))}
    </div>
  )
}

function ProductsGridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 px-5 pb-28 pt-1">
      {[0, 1, 2, 3].map((i) => (
        <ProductCardSkeleton key={i} />
      ))}
    </div>
  )
}

function Header({ count }: { count: number | undefined }) {
  return (
    <header className="flex items-end justify-between px-5 pb-3 pt-5">
      <div>
        <h1 className="font-display text-[24px] font-bold leading-tight tracking-tight">
          Produits
        </h1>
        <p className="mt-0.5 text-[13px] text-ink-muted">
          {count === undefined
            ? "Votre catalogue"
            : count === 0
              ? "Votre catalogue"
              : count === 1
                ? "1 article en boutique"
                : `${count} articles en boutique`}
        </p>
      </div>
    </header>
  )
}

/** Bouton flottant « + Ajouter » (action primaire unique de l'écran). */
function AddFab() {
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-10 flex justify-center">
      <div className="w-full max-w-[440px] px-5 pb-24">
        <div className="flex justify-end">
          <button
            type="button"
            aria-label="Ajouter un produit"
            className="pointer-events-auto inline-flex h-14 items-center gap-2 rounded-full bg-primary px-6 font-display text-[15px] font-bold text-primary-foreground shadow-[0_8px_24px_-6px_rgba(22,163,74,.45)] transition active:scale-[0.97]"
          >
            <Plus className="h-5 w-5" strokeWidth={2.5} />
            Ajouter
          </button>
        </div>
      </div>
    </div>
  )
}

/** État vide soigné : aucun produit dans le catalogue. */
function ProductsEmpty() {
  return (
    <div className="px-5 pb-28 pt-6">
      <div className="rounded-2xl border border-line bg-surface p-8 text-center shadow-soft">
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-primary-tint">
          <PackageOpen className="h-6 w-6 text-primary-deep" />
        </div>
        <p className="mt-3 font-display text-[16px] font-bold">
          Aucun produit pour l'instant
        </p>
        <p className="mt-1 text-[13.5px] text-ink-muted">
          Ajoutez votre premier article pour que le bot puisse le proposer et le
          vendre sur WhatsApp.
        </p>
        <button
          type="button"
          className="mt-4 inline-flex h-12 items-center gap-2 rounded-full bg-primary px-5 font-display text-[14px] font-bold text-primary-foreground transition active:scale-[0.98]"
        >
          <Plus className="h-4.5 w-4.5" strokeWidth={2.5} />
          Ajouter un produit
        </button>
      </div>
    </div>
  )
}

/** Le marchand démo est introuvable (seed pas lancé). */
function MerchantMissing() {
  return (
    <div className="px-5 py-16 text-center">
      <p className="font-display text-[18px] font-bold">Marchand introuvable</p>
      <p className="mt-2 text-[14px] text-ink-muted">
        Le marchand de démonstration n'existe pas encore. Lancez le seed Convex :
      </p>
      <code className="mt-3 inline-block rounded-md bg-line px-2 py-1 font-mono text-[13px] text-ink">
        npx convex run seed:run
      </code>
    </div>
  )
}
