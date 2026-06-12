import type { ReactNode } from "react"
import { LiquidGlassBottomBar, type TabKey } from "./LiquidGlassBottomBar"

/**
 * Coquille de l'app marchand (DIRECTION.md : mobile natif, onglets bas).
 * Conteneur pleine hauteur (h-dvh) cadré en colonne mobile sur fond #F1EFE9.
 * Modèle de scroll : la ZONE DE CONTENU est seule scrollable (flex-1
 * overflow-y-auto) avec un padding-bas suffisant pour dégager la barre et le
 * débord du FAB. La LiquidGlassBottomBar est FIXE en bas, hors du flux
 * scrollable : elle reste visible même sur les pages longues (Réglages).
 */
export function AppShell({
  children,
  activeTab,
}: {
  children: ReactNode
  activeTab: TabKey
}) {
  return (
    <div className="flex h-dvh justify-center bg-[#F1EFE9]">
      <div className="relative flex h-dvh w-full max-w-[440px] flex-col bg-page sm:border-x sm:border-line">
        {/* Zone de contenu : seule scrollable. pb dégage barre (84) + débord FAB. */}
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
  )
}
