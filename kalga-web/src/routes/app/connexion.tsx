import { createFileRoute } from "@tanstack/react-router"
import { WhatsAppConnect } from "@/components/onboarding/WhatsAppConnect"

/**
 * Route onboarding « Connecter WhatsApp » (plan 010 §E).
 *
 * Rendue sous /app : la gate d'auth de `app/route.tsx` garantit une session.
 * C'est l'etape ou le marchand lie sa session WhatsApp (code d'appairage ou QR)
 * avant d'acceder au tableau de bord. L'AppShell parent fournit la coquille
 * mobile ; cette page n'affiche pas la pression du dashboard, juste le flux de
 * connexion (toggle Code/QR, code, etapes, statut vivant, succes).
 */
export const Route = createFileRoute("/app/connexion")({
  component: ConnexionPage,
})

function ConnexionPage() {
  return <WhatsAppConnect />
}
