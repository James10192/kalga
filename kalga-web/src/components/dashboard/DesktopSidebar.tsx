import { Link } from "@tanstack/react-router"
import {
  Home,
  MessagesSquare,
  ShoppingBag,
  Wallet,
  Settings,
  type LucideIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { TabKey } from "./LiquidGlassBottomBar"

type NavItem = {
  key: TabKey
  label: string
  icon: LucideIcon
  to: string
}

// Memes routes que la LiquidGlassBottomBar (mobile), ordre Accueil en tete.
const NAV_ITEMS: NavItem[] = [
  { key: "accueil", label: "Accueil", icon: Home, to: "/app" },
  { key: "conversations", label: "Conversations", icon: MessagesSquare, to: "/app/conversations" },
  { key: "produits", label: "Produits", icon: ShoppingBag, to: "/app/products" },
  { key: "argent", label: "Argent", icon: Wallet, to: "/app/money" },
  { key: "reglages", label: "Réglages", icon: Settings, to: "/app/settings" },
]

/**
 * Barre laterale desktop (>= lg) du dashboard marchand (TOKENS.md §4).
 * Largeur w-64, logo KALGA en tete, rangees icone + label h-11.
 * Actif = `bg-primary-tint text-primary-deep` + barre accent 3px a gauche.
 * Rendue UNIQUEMENT >= lg par l'AppShell ; n'affecte pas le mobile.
 */
export function DesktopSidebar({ active }: { active: TabKey }) {
  return (
    <aside className="flex h-dvh w-64 shrink-0 flex-col border-r border-line bg-surface">
      {/* Marque KALGA. */}
      <div className="flex h-16 items-center gap-2 px-5">
        <span className="grid size-8 place-items-center rounded-lg bg-primary text-sm font-semibold text-white">
          K
        </span>
        <span className="font-display text-lg font-semibold tracking-tight text-ink">
          KALGA
        </span>
      </div>

      {/* Navigation principale. */}
      <nav aria-label="Navigation principale" className="flex flex-1 flex-col gap-1 px-3 py-2">
        {NAV_ITEMS.map((item) => (
          <SidebarItem key={item.key} item={item} active={item.key === active} />
        ))}
      </nav>
    </aside>
  )
}

function SidebarItem({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon
  return (
    <Link
      to={item.to}
      aria-current={active ? "page" : undefined}
      // `/app` (Accueil) matche aussi ses sous-routes par defaut : on borne en
      // exact pour ne pas garder Accueil actif sur /app/products etc.
      activeOptions={item.to === "/app" ? { exact: true } : undefined}
      className={cn(
        "relative flex h-11 items-center gap-3 rounded-lg px-3 text-sm transition-colors",
        active
          ? "bg-primary-tint font-medium text-primary-deep"
          : "text-ink-muted hover:bg-line/60 hover:text-ink",
      )}
    >
      {/* Barre accent 3px a gauche (active uniquement). */}
      {active && (
        <span
          aria-hidden
          className="absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-full bg-primary"
        />
      )}
      <Icon className="size-5 shrink-0" strokeWidth={active ? 2.2 : 1.9} />
      <span>{item.label}</span>
    </Link>
  )
}
