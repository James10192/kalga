import { ImageIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { formatAmount } from "./format"

export type StockState = "ok" | "low_stock" | "out_of_stock" | "unlimited"

const STOCK_LABEL: Record<StockState, string> = {
  ok: "En stock",
  unlimited: "Illimité",
  low_stock: "Stock bas",
  out_of_stock: "Rupture",
}

const STOCK_DOT: Record<StockState, string> = {
  ok: "bg-primary",
  unlimited: "bg-primary",
  low_stock: "bg-nego",
  out_of_stock: "bg-danger",
}

/** Dérive l'état de stock d'un produit (parité statut backend). */
export function stockState(
  stockQuantity: number | null | undefined,
  threshold: number | null | undefined,
): StockState {
  const q = stockQuantity ?? -1
  const t = threshold ?? 5
  if (q === -1) return "unlimited"
  if (q === 0) return "out_of_stock"
  if (q <= t) return "low_stock"
  return "ok"
}

/**
 * Carte produit (DIRECTION.md : grille visuelle, pastille stock discrète).
 * Image grande en haut, nom + prix FCFA, pastille de stock.
 */
export function ProductCard({
  name,
  price,
  imageUrl,
  stock,
  onClick,
}: {
  name: string
  price: number
  imageUrl?: string | null
  stock: StockState
  onClick?: () => void
}) {
  return (
    <button
      type="button"
      data-testid="product-card"
      onClick={onClick}
      className="group overflow-hidden rounded-2xl border border-line bg-surface text-left shadow-soft transition active:scale-[0.99]"
    >
      <div className="relative aspect-square w-full bg-page">
        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt={name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="grid h-full w-full place-items-center text-ink-faint">
            <ImageIcon className="h-8 w-8" />
          </div>
        )}
        <span className="absolute left-2 top-2 inline-flex items-center gap-1.5 rounded-full bg-surface/90 px-2 py-1 text-[11px] font-medium text-ink-muted backdrop-blur">
          <span className={cn("h-1.5 w-1.5 rounded-full", STOCK_DOT[stock])} />
          {STOCK_LABEL[stock]}
        </span>
      </div>
      <div className="p-3">
        <p className="truncate text-[14px] font-semibold">{name}</p>
        <p className="mt-0.5 font-display text-[16px] font-bold tabular">
          {formatAmount(price)}{" "}
          <span className="text-[12px] font-semibold text-ink-muted">FCFA</span>
        </p>
      </div>
    </button>
  )
}

/** Skeleton d'une carte produit. */
export function ProductCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-soft">
      <Skeleton className="aspect-square w-full" />
      <div className="space-y-2 p-3">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-16" />
      </div>
    </div>
  )
}
