import {
  createFileRoute,
  Outlet,
  redirect,
  useMatches,
} from "@tanstack/react-router"
import { convexQuery } from "@convex-dev/react-query"
import { AppShell, type TabKey } from "@/components/dashboard"
import { api } from "../../../convex/_generated/api"

/**
 * Layout des routes /app/* (dashboard marchand).
 *
 * Gating (plan 010 C) :
 *  1. Auth requise : pas de session -> redirect /login.
 *  2. Reprise onboarding : marchand sans `whatsappLinkedAt` -> redirect
 *     /app/connexion (sauf si on y est deja, ou sur /app/admin/*).
 *
 * Les providers Convex/Auth sont montes dans __root.tsx
 * (ConvexBetterAuthProvider) ; useQuery fonctionne dans les enfants.
 */
export const Route = createFileRoute("/app")({
  beforeLoad: async ({ context, location }) => {
    // 1. Session obligatoire.
    if (!context.isAuthenticated) {
      throw redirect({ to: "/login" })
    }

    const path = location.pathname
    // L'admin a son propre layout/onboarding : pas de gate WhatsApp dessus.
    const onConnexion = path === "/app/connexion"
    const onAdmin = path.startsWith("/app/admin")
    if (onConnexion || onAdmin) return

    // 2. Reprise onboarding : si le marchand courant n'a pas encore lie son
    //    WhatsApp, rediriger vers l'ecran de connexion. Resolu via withOrg
    //    cote serveur/Convex (jamais un id client). Tolerant aux erreurs.
    try {
      const merchant = await context.queryClient.ensureQueryData(
        convexQuery(api.merchants.currentMerchant, {}),
      )
      if (merchant && !merchant.whatsappLinkedAt) {
        throw redirect({ to: "/app/connexion" })
      }
    } catch (e) {
      // Une redirection levee ci-dessus doit se propager.
      if (e && typeof e === "object" && "isRedirect" in e) throw e
      // Sinon (query indisponible au 1er render) : on laisse passer, la page
      // affichera ses propres etats ; la gate se re-jouera a la navigation.
    }
  },
  component: AppLayout,
})

/** Déduit l'onglet actif depuis le chemin courant (5 zones). */
function useActiveTab(): TabKey {
  const matches = useMatches()
  const path = matches[matches.length - 1]?.pathname ?? "/app"
  if (path.startsWith("/app/conversations")) return "conversations"
  if (path.startsWith("/app/products")) return "produits"
  if (path.startsWith("/app/money")) return "argent"
  if (path.startsWith("/app/settings")) return "reglages"
  // Accueil (FAB central) : actif sur /app exact uniquement.
  return "accueil"
}

function AppLayout() {
  const activeTab = useActiveTab()
  const matches = useMatches()
  const path = matches[matches.length - 1]?.pathname ?? "/app"
  // L'admin (008) a son propre layout dense (header admin, PAS la bottombar
  // liquid-glass marchand). On laisse donc /app/admin/* rendre son layout sans
  // l'AppShell mobile.
  if (path.startsWith("/app/admin")) return <Outlet />
  return (
    <AppShell activeTab={activeTab}>
      <Outlet />
    </AppShell>
  )
}
