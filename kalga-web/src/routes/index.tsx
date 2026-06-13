import { createFileRoute } from "@tanstack/react-router"
import {
  Features,
  FinalCta,
  Footer,
  Hero,
  HowItWorks,
  Nav,
  Pricing,
  StorefrontShowcase,
} from "@/components/marketing"

/**
 * Landing publique KALGA (kalga.app) — page marketing.
 *
 * Page PUBLIQUE : aucun provider auth/dashboard requis, SSR-safe (aucun acces
 * window/document au render). Tous les CTAs menent vers /signup, "Se connecter"
 * vers /login. Fidele a design-prototypes/landing.html, tokens DIRECTION.md.
 */
export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "KALGA — Votre vendeur WhatsApp qui ne dort jamais" },
      {
        name: "description",
        content:
          "KALGA automatise vos ventes WhatsApp : le bot repond, negocie et conclut pendant que vous gerez votre business.",
      },
    ],
  }),
  component: LandingPage,
})

function LandingPage() {
  return (
    <div className="min-h-dvh bg-page text-ink antialiased">
      <Nav />
      <main>
        <Hero />
        <HowItWorks />
        <Features />
        <StorefrontShowcase />
        <Pricing />
        <FinalCta />
      </main>
      <Footer />
    </div>
  )
}
