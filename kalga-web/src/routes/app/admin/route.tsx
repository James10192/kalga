import { createFileRoute, Outlet, Link, useMatches } from "@tanstack/react-router"

/**
 * Layout ADMIN KALGA (plan 008) — équipe KALGA, pas le marchand.
 *
 * Surface DENSE, desktop-leaning : header admin sombre-mat distinct du dashboard
 * marchand (PAS la bottombar liquid-glass). Mêmes tokens KALGA. Pleine largeur,
 * conteneur centré large. Mode démo : pas d'auth gating réel (le plugin admin
 * Better Auth gatera plus tard).
 */
export const Route = createFileRoute("/app/admin")({
  component: AdminLayout,
})

type NavKey = "merchants" | "codes" | "audit"

function useActiveNav(): NavKey {
  const matches = useMatches()
  const path = matches[matches.length - 1]?.pathname ?? "/app/admin"
  if (path.startsWith("/app/admin/codes")) return "codes"
  if (path.startsWith("/app/admin/audit")) return "audit"
  return "merchants"
}

const NAV: { key: NavKey; label: string; to: string }[] = [
  { key: "merchants", label: "Marchands", to: "/app/admin" },
  { key: "codes", label: "Codes d'activation", to: "/app/admin/codes" },
  { key: "audit", label: "Journal d'audit", to: "/app/admin/audit" },
]

function AdminLayout() {
  const active = useActiveNav()
  return (
    <div className="min-h-dvh bg-page">
      <header className="sticky top-0 z-20 border-b border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-[1200px] items-center gap-6 px-5">
          <Link to="/app/admin" className="flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-primary text-[13px] font-bold text-primary-foreground">
              K
            </span>
            <span className="font-display text-[16px] font-bold tracking-tight">
              KALGA <span className="text-ink-muted">Admin</span>
            </span>
          </Link>
          <nav className="ml-2 hidden items-center gap-1 sm:flex">
            {NAV.map((item) => (
              <Link
                key={item.key}
                to={item.to}
                className={
                  "rounded-lg px-3 py-1.5 text-[13.5px] font-medium transition-colors " +
                  (active === item.key
                    ? "bg-secondary text-ink"
                    : "text-ink-muted hover:bg-secondary/60 hover:text-ink")
                }
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <span className="hidden rounded-full bg-secondary px-2.5 py-1 text-[11.5px] font-medium text-ink-muted sm:inline">
              Mode démo
            </span>
            <Link
              to="/app"
              className="text-[13px] font-medium text-ink-muted hover:text-ink"
            >
              Dashboard
            </Link>
          </div>
        </div>
        {/* Nav mobile (sous le header, scroll horizontal). */}
        <nav className="flex items-center gap-1 overflow-x-auto px-5 pb-2 sm:hidden">
          {NAV.map((item) => (
            <Link
              key={item.key}
              to={item.to}
              className={
                "shrink-0 rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors " +
                (active === item.key
                  ? "bg-secondary text-ink"
                  : "text-ink-muted hover:bg-secondary/60")
              }
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </header>

      <main className="mx-auto w-full max-w-[1200px] px-5 py-6">
        <Outlet />
      </main>
    </div>
  )
}
