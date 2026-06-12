import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"

type Dot = "nego" | "livrer" | "danger"

const DOT_COLORS: Record<Dot, string> = {
  nego: "bg-nego",
  livrer: "bg-livrer",
  danger: "bg-danger",
}

/**
 * Pill statistique quiète (DIRECTION.md : 2-3 pills, zéro carte KPI).
 * Pastille colorée discrète + nombre Bricolage + label muted.
 */
export function StatPill({
  count,
  label,
  dot,
  onClick,
}: {
  count: number
  label: string
  dot: Dot
  onClick?: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-xl border border-line bg-surface p-3 text-left shadow-soft transition active:scale-[0.98]"
    >
      <span className={cn("mb-2 block h-2 w-2 rounded-full", DOT_COLORS[dot])} />
      <span className="font-display text-[18px] font-bold tabular">{count}</span>
      <span className="block text-[12px] leading-tight text-ink-muted">
        {label}
      </span>
    </button>
  )
}

/** Skeleton d'une rangée de 3 pills. */
export function StatPillsSkeleton() {
  return (
    <div className="grid grid-cols-3 gap-2.5">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="rounded-xl border border-line bg-surface p-3 shadow-soft"
        >
          <Skeleton className="mb-2 h-2 w-2 rounded-full" />
          <Skeleton className="h-5 w-6" />
          <Skeleton className="mt-1.5 h-3 w-14" />
        </div>
      ))}
    </div>
  )
}
