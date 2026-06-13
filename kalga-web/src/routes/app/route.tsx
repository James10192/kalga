import { useEffect } from "react"
import {
  createFileRoute,
  Outlet,
  redirect,
  useMatches,
  useNavigate,
} from "@tanstack/react-router"
import { Authenticated, AuthLoading, useQuery } from "convex/react"
import { Loader2 } from "lucide-react"
import { AppShell, type TabKey } from "@/components/dashboard"
import { api } from "../../../convex/_generated/api"

/**
 * Layout des routes /app/* (dashboard marchand).
 *
 * Gating (plan 010 C) :
 *  1. Auth requise : pas de session -> redirect /login (beforeLoad).
 *  2. Au 1er render, le token client Convex n'est pas encore pret : on monte
 *     d'abord un squelette via <AuthLoading>, puis le contenu reel via
 *     <Authenticated>. Les queries authentifiees (withOrg) ne se montent donc
 *     qu'une fois la session prete, ce qui evite le flash "Unauthenticated".
 *  3. Reprise onboarding : marchand sans `whatsappLinkedAt` -> /app/connexion,
 *     verifie cote client dans <OnboardingGate> (une fois authentifie), pour ne
 *     pas declencher une query withOrg avant que le token soit pret.
 *
 * Les providers Convex/Auth sont montes dans __root.tsx
 * (ConvexBetterAuthProvider) ; useQuery fonctionne dans les enfants.
 */
export const Route = createFileRoute("/app")({
  beforeLoad: async ({ context }) => {
    // Session obligatoire (cote serveur/loader). La gate WhatsApp est faite
    // cote client dans <OnboardingGate> pour eviter un withOrg premature.
    if (!context.isAuthenticated) {
      throw redirect({ to: "/login" })
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

/**
 * Reprise d'onboarding cote client : une fois authentifie, lit le marchand
 * courant (via withOrg). Tant que `whatsappLinkedAt` est absent, renvoie vers
 * /app/connexion. Neutralisee sur /app/connexion et /app/admin/*.
 */
function OnboardingGate({ path }: { path: string }) {
  const navigate = useNavigate()
  const skip = path === "/app/connexion" || path.startsWith("/app/admin")
  const merchant = useQuery(api.merchants.currentMerchant, {})

  useEffect(() => {
    if (skip) return
    // `undefined` = en cours de chargement ; `null` = pas de marchand.
    if (merchant && !merchant.whatsappLinkedAt) {
      void navigate({ to: "/app/connexion" })
    }
  }, [skip, merchant, navigate])

  return null
}

/** Squelette leger affiche pendant que le token Convex se charge. */
function DashboardSkeleton() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Loader2 className="size-6 animate-spin text-[#16A34A]" aria-hidden />
      <span className="sr-only">Chargement de votre espace</span>
    </div>
  )
}

function AppLayout() {
  const activeTab = useActiveTab()
  const matches = useMatches()
  const path = matches[matches.length - 1]?.pathname ?? "/app"
  const isAdmin = path.startsWith("/app/admin")

  // L'admin (008) a son propre layout dense (header admin, PAS la bottombar
  // liquid-glass marchand). On laisse donc /app/admin/* rendre son layout sans
  // l'AppShell mobile. On garde toutefois le gating auth (squelette puis Outlet).
  if (isAdmin) {
    return (
      <>
        <AuthLoading>
          <DashboardSkeleton />
        </AuthLoading>
        <Authenticated>
          <Outlet />
        </Authenticated>
      </>
    )
  }

  return (
    <AppShell activeTab={activeTab}>
      <AuthLoading>
        <DashboardSkeleton />
      </AuthLoading>
      <Authenticated>
        <OnboardingGate path={path} />
        <Outlet />
      </Authenticated>
    </AppShell>
  )
}
