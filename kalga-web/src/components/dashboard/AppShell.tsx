import type { ReactNode } from "react"
import { Link } from "@tanstack/react-router"
import { useQuery } from "convex/react"
import { cn } from "@/lib/utils"
import { LiquidGlassBottomBar, type TabKey } from "./LiquidGlassBottomBar"
import { DesktopSidebar } from "./DesktopSidebar"
import { api } from "../../../convex/_generated/api"

/**
 * Coquille responsive de l'app marchand.
 *
 * - `< lg` : layout mobile natif (DIRECTION.md) INCHANGE. Colonne centree
 *   `max-w-[440px]` sur fond #F1EFE9, zone de contenu seule scrollable, et la
 *   `LiquidGlassBottomBar` FIXE en bas (onglets au pouce).
 * - `>= lg` : `DesktopSidebar` (w-64) a gauche + top bar (nom boutique + statut
 *   WhatsApp) + zone de contenu fluide (max-w-6xl). PAS de bottom bar.
 *
 * Les deux branches sont rendues en parallele et bascule par media query
 * (`lg:hidden` / `hidden lg:flex`) : aucune regression du mobile possible.
 */
export function AppShell({
  children,
  activeTab,
}: {
  children: ReactNode
  activeTab: TabKey
}) {
  return (
    <>
      {/* ---- Mobile (< lg) : layout actuel, inchange. ---- */}
      <div className="flex h-dvh justify-center bg-[#F1EFE9] lg:hidden">
        <div className="relative flex h-dvh w-full max-w-[440px] flex-col bg-page sm:border-x sm:border-line">
          {/* Zone de contenu : seule scrollable. pb degage barre (84) + debord FAB. */}
          <div
            className="no-scrollbar flex-1 overflow-y-auto"
            style={{ paddingBottom: "calc(104px + env(safe-area-inset-bottom))" }}
          >
            {children}
          </div>
          {/* Barre fixe en bas du shell (hors zone scrollable). */}
          <LiquidGlassBottomBar active={activeTab} />
        </div>
      </div>

      {/* ---- Desktop (>= lg) : sidebar + top bar + contenu fluide. ---- */}
      <div className="hidden h-dvh bg-page lg:flex">
        <DesktopSidebar active={activeTab} />
        <div className="flex h-dvh min-w-0 flex-1 flex-col">
          <DesktopTopBar />
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto w-full max-w-6xl px-6 py-6 xl:px-10 xl:py-8">
              {children}
            </div>
          </main>
        </div>
      </div>
    </>
  )
}

/**
 * Top bar desktop : nom de la boutique a gauche, puce statut WhatsApp a droite.
 * Le statut (vert Connecte / ambre Non connecte) est cliquable vers
 * /app/connexion. Donnees resolues via `currentMerchant` (withOrg, anti-fuite).
 */
function DesktopTopBar() {
  const merchant = useQuery(api.merchants.currentMerchant, {})
  const linked = Boolean(merchant?.whatsappLinkedAt)
  const name = merchant?.name ?? "Boutique"

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-line bg-surface/80 px-6 backdrop-blur xl:px-10">
      <h1 className="truncate font-display text-base font-semibold tracking-tight text-ink">
        {name}
      </h1>
      <WhatsappStatusChip linked={linked} />
    </header>
  )
}

/**
 * Puce statut WhatsApp (desktop top bar). Point colore + libelle, cliquable
 * vers l'ecran de connexion WhatsApp (reprise onboarding / re-appairage).
 */
function WhatsappStatusChip({ linked }: { linked: boolean }) {
  return (
    <Link
      to="/app/connexion"
      aria-label={
        linked
          ? "WhatsApp connecté, gérer la connexion"
          : "WhatsApp non connecté, connecter maintenant"
      }
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
        linked
          ? "bg-primary-tint text-primary-deep hover:bg-primary-tint/80"
          : "bg-[#FAF1E4] text-[#B45309] hover:bg-[#FAF1E4]/80",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "size-2 rounded-full",
          linked ? "bg-primary" : "bg-[#B45309]",
        )}
      />
      {linked ? "Connecté" : "Non connecté"}
    </Link>
  )
}
