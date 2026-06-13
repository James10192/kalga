import { cn } from "@/lib/utils"

/**
 * Marque KALGA : pastille verte "K" + wordmark.
 * Réutilisée dans la nav et le pied de page de la landing.
 */
export function Brand({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2", className)}>
      <span className="grid size-8 place-items-center rounded-lg bg-primary font-display font-bold text-white">
        K
      </span>
      <span className="font-display text-lg font-semibold tracking-tight text-ink">
        KALGA
      </span>
    </span>
  )
}
