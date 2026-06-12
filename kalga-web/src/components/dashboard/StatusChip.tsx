import { Check } from "lucide-react"
import { cn } from "@/lib/utils"
import type { StatusKind } from "./format"

const LABELS: Record<StatusKind, string> = {
  nego: "Négociation",
  livrer: "À livrer",
  paye: "Payé",
  rupture: "Rupture",
  nouveau: "Nouveau",
}

const STYLES: Record<StatusKind, string> = {
  nego: "text-nego bg-nego-tint",
  livrer: "text-livrer bg-livrer-tint",
  paye: "text-primary-deep bg-primary-tint",
  rupture: "text-danger bg-danger-tint",
  nouveau: "text-ink-muted bg-line",
}

/**
 * Puce de statut conversation (DIRECTION.md sémantiques mats).
 * Pill arrondie (radius 999), tons mats premium, vert seulement pour "payé".
 */
export function StatusChip({
  kind,
  className,
}: {
  kind: StatusKind
  className?: string
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11.5px] font-medium",
        STYLES[kind],
        className,
      )}
    >
      {kind === "paye" && <Check className="h-3 w-3" />}
      {LABELS[kind]}
    </span>
  )
}
