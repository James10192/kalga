import { CircleCheckBig, TrendingUp } from "lucide-react"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { formatAmount } from "./format"

/**
 * Héros argent du jour (DIRECTION.md : argent toujours lisible, first-class).
 * Montant en Bricolage Grotesque, grand, tabular-nums. Vert chirurgical pour
 * le delta positif et le badge WhatsApp connecté.
 */
export function MoneyHero({
  amount,
  sales,
  deltaPct,
  whatsappConnected = true,
}: {
  amount: number
  sales: number
  deltaPct: number | null
  whatsappConnected?: boolean
}) {
  const positive = deltaPct !== null && deltaPct >= 0
  return (
    <div className="rounded-2xl border border-line bg-surface p-5 shadow-card">
      <div className="flex items-center justify-between">
        <p className="text-[13px] font-medium text-ink-muted">
          Encaissé aujourd'hui
        </p>
        {whatsappConnected && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-tint px-2 py-1 text-[12px] font-medium text-primary-deep">
            <CircleCheckBig className="h-3.5 w-3.5" /> WhatsApp connecté
          </span>
        )}
      </div>

      <div className="mt-2 flex items-end gap-2">
        <span className="font-display text-[38px] font-extrabold leading-none tracking-tight tabular">
          {formatAmount(amount)}
        </span>
        <span className="mb-1 font-display text-[18px] font-semibold text-ink-muted">
          FCFA
        </span>
      </div>

      <div className="mt-3 flex items-center gap-3 text-[13px]">
        {deltaPct !== null && (
          <>
            <span
              className={cn(
                "inline-flex items-center gap-1 font-medium",
                positive ? "text-primary-deep" : "text-ink-muted",
              )}
            >
              <TrendingUp
                className={cn("h-4 w-4", !positive && "rotate-180")}
              />
              {positive ? "+" : ""}
              {deltaPct}% vs hier
            </span>
            <span className="text-ink-faint">·</span>
          </>
        )}
        <span className="text-ink-muted">
          {sales} {sales > 1 ? "ventes" : "vente"}
        </span>
      </div>
    </div>
  )
}

/** Skeleton du héros argent pendant le chargement Convex. */
export function MoneyHeroSkeleton() {
  return (
    <div className="rounded-2xl border border-line bg-surface p-5 shadow-card">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-36" />
        <Skeleton className="h-6 w-32 rounded-full" />
      </div>
      <Skeleton className="mt-3 h-10 w-44" />
      <Skeleton className="mt-3 h-4 w-40" />
    </div>
  )
}
