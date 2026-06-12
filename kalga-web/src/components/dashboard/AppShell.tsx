import type { ReactNode } from "react"
import { BottomTabBar, type TabKey } from "./BottomTabBar"

/**
 * Coquille de l'app marchand (DIRECTION.md : mobile natif, onglets bas).
 * Colonne pleine hauteur : zone scrollable + barre d'onglets fixe en bas.
 * Sur grand écran, l'app reste cadrée en colonne mobile (calme, pas étalée).
 */
export function AppShell({
  children,
  activeTab,
}: {
  children: ReactNode
  activeTab: TabKey
}) {
  return (
    <div className="flex min-h-dvh justify-center bg-[#F1EFE9]">
      <div className="flex min-h-dvh w-full max-w-[440px] flex-col bg-page sm:my-0 sm:border-x sm:border-line">
        <div className="no-scrollbar flex-1 overflow-y-auto">{children}</div>
        <BottomTabBar active={activeTab} />
      </div>
    </div>
  )
}
