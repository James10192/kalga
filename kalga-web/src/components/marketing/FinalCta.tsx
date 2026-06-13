import { Link } from "@tanstack/react-router"
import { ArrowRight } from "lucide-react"
import { useRef } from "react"
import { useReveal } from "./useReveal"

/**
 * Bandeau d'appel a l'action final, sur fond sombre.
 * Scroll-reveal GSAP via useReveal (gsap brut, SSR-safe, reduced-motion ok).
 */
export function FinalCta() {
  const scope = useRef<HTMLElement>(null)
  useReveal(scope)

  return (
    <section ref={scope} className="border-b border-line">
      <div className="mx-auto max-w-6xl px-4 py-16 md:px-8 md:py-24">
        <div
          data-reveal
          className="relative overflow-hidden rounded-2xl border border-line bg-stone-900 px-6 py-12 text-center md:px-12 md:py-16"
          style={{
            backgroundImage:
              "radial-gradient(rgba(255,255,255,0.06) 1px, transparent 1px)",
            backgroundSize: "20px 20px",
          }}
        >
          <h2 className="mx-auto max-w-2xl font-display text-3xl font-semibold tracking-tight text-white md:text-5xl">
            Arretez de repondre aux memes questions toute la journee.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-stone-300">
            Laissez KALGA gerer le bavardage et la negociation. Vous vous
            concentrez sur les ventes et la livraison.
          </p>
          <Link
            to="/signup"
            className="mt-8 inline-flex h-12 items-center gap-2 rounded-lg bg-primary px-6 text-base font-medium text-white transition-colors hover:bg-primary-deep"
          >
            Connecter mon WhatsApp <ArrowRight className="size-4" />
          </Link>
        </div>
      </div>
    </section>
  )
}
