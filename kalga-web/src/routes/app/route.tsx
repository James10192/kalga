import { createFileRoute, Outlet, useMatches } from "@tanstack/react-router"
import { AppShell, type TabKey } from "@/components/dashboard"

/**
 * Layout des routes /app/* (dashboard marchand).
 * Rend la coquille mobile (AppShell + barre d'onglets bas). Les providers
 * Convex/Auth sont déjà montés dans __root.tsx (ConvexBetterAuthProvider),
 * useQuery fonctionne donc directement dans les enfants.
 *
 * L'auth gating (withOrg / OTP live) viendra ici via beforeLoad en 003/004.
 */
export const Route = createFileRoute("/app")({
  component: AppLayout,
})

/** Déduit l'onglet actif depuis le chemin courant. */
function useActiveTab(): TabKey {
  const matches = useMatches()
  const path = matches[matches.length - 1]?.pathname ?? "/app"
  if (path.startsWith("/app/products")) return "produits"
  if (path.startsWith("/app/money")) return "argent"
  if (path.startsWith("/app/settings")) return "reglages"
  return "conversations"
}

function AppLayout() {
  const activeTab = useActiveTab()
  return (
    <AppShell activeTab={activeTab}>
      <Outlet />
    </AppShell>
  )
}
