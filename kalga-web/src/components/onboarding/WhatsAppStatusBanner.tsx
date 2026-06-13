import { Link } from "@tanstack/react-router"
import { MessageCircleWarning, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * Banniere « WhatsApp non connecte » (plan 010 §E).
 *
 * Reutilisable : affichee sur /app (accueil) et dans les Reglages tant que le
 * marchand n'a pas lie sa session WhatsApp (`whatsappLinkedAt` absent). Tap ->
 * /app/connexion pour reprendre l'onboarding.
 *
 * Ton ambre (semantique « attention » de la direction), jamais le vert (reserve
 * au succes/argent). Cible tactile pleine largeur >= 48px.
 */
export function WhatsAppStatusBanner({ className }: { className?: string }) {
  return (
    <Link
      to="/app/connexion"
      className={cn(
        "flex items-center gap-3 rounded-2xl border border-nego/25 bg-nego-tint px-4 py-3",
        "min-h-12 transition-colors hover:bg-nego-tint/70",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-nego/40",
        className,
      )}
    >
      <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-nego/12 text-nego">
        <MessageCircleWarning className="size-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium text-ink">
          WhatsApp non connecte
        </span>
        <span className="block truncate text-[13px] text-ink-muted">
          Connectez votre WhatsApp pour activer le bot.
        </span>
      </span>
      <ChevronRight className="size-5 shrink-0 text-nego" />
    </Link>
  )
}
