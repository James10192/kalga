import { Link } from "@tanstack/react-router"
import {
  MessagesSquare,
  ShoppingBag,
  Wallet,
  Settings,
  type LucideIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"

type TabKey = "conversations" | "produits" | "argent" | "reglages"

type Tab = {
  key: TabKey
  label: string
  icon: LucideIcon
  to: string
}

const TABS: Tab[] = [
  { key: "conversations", label: "Conversations", icon: MessagesSquare, to: "/app" },
  { key: "produits", label: "Produits", icon: ShoppingBag, to: "/app/products" },
  { key: "argent", label: "Argent", icon: Wallet, to: "/app/money" },
  { key: "reglages", label: "Réglages", icon: Settings, to: "/app/settings" },
]

/**
 * Barre d'onglets bas (DIRECTION.md : mobile natif au pouce, cibles >= 48px).
 * Onglet actif en vert (pastille tint). Les routes filles seront ajoutées plus
 * tard ; on garde `to` pour brancher la navigation TanStack.
 */
export function BottomTabBar({ active }: { active: TabKey }) {
  return (
    <nav className="shrink-0 border-t border-line bg-surface px-2 pb-6 pt-2">
      <div className="grid grid-cols-4">
        {TABS.map((tab) => {
          const isActive = tab.key === active
          const Icon = tab.icon
          const content = (
            <span
              className={cn(
                "flex flex-col items-center gap-1 py-1",
                isActive ? "text-primary-deep" : "text-ink-muted",
              )}
            >
              <span
                className={cn(
                  "grid h-8 w-12 place-items-center rounded-full",
                  isActive && "bg-primary-tint",
                )}
              >
                <Icon className="h-[22px] w-[22px]" />
              </span>
              <span
                className={cn(
                  "text-[11px]",
                  isActive ? "font-semibold" : "font-medium",
                )}
              >
                {tab.label}
              </span>
            </span>
          )

          // Tous les onglets pointent vers une route livrée (Link TanStack).
          return (
            <Link key={tab.key} to={tab.to} aria-label={tab.label}>
              {content}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}

export type { TabKey }
