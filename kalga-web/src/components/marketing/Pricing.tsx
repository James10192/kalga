import { Link } from "@tanstack/react-router"
import { Check, Wallet } from "lucide-react"
import { useRef } from "react"
import { useReveal } from "./useReveal"

/**
 * Section "Tarifs" : plan essai gratuit + plan Pro active par code.
 * Activation par code apres paiement Wave / Orange Money / MTN MoMo.
 * Scroll-reveal GSAP via useReveal (gsap brut, SSR-safe, reduced-motion ok).
 */
const ESSAI = [
  "Bot de vente et negociation",
  "Jusqu'a 30 produits",
  "Boutique en ligne",
]
const PRO = [
  "Produits illimites",
  "Memoire client et suivi des relances",
  "Statistiques de ventes",
  "Support prioritaire WhatsApp",
]
const RAILS = ["Wave", "Orange Money", "MTN MoMo"]

export function Pricing() {
  const scope = useRef<HTMLElement>(null)
  useReveal(scope)

  return (
    <section
      id="tarifs"
      ref={scope}
      className="border-b border-line bg-secondary"
    >
      <div className="mx-auto max-w-6xl px-4 py-16 md:px-8 md:py-24">
        <div className="mx-auto max-w-2xl text-center">
          <p data-reveal className="text-sm font-medium text-primary">
            Tarifs
          </p>
          <h2
            data-reveal
            className="mt-2 font-display text-3xl font-semibold tracking-tight text-ink md:text-4xl"
          >
            Simple, sans engagement.
          </h2>
          <p data-reveal className="mt-3 text-ink-muted">
            Vous payez par Wave ou Orange Money, on vous envoie un code
            d'activation. Vous l'entrez, votre bot s'active. Pas de carte
            bancaire.
          </p>
        </div>

        <div className="mx-auto mt-12 grid max-w-3xl gap-4 md:grid-cols-2">
          <div
            data-reveal
            className="rounded-xl border border-line bg-surface p-6"
          >
            <p className="text-sm font-medium text-ink-faint">Essai</p>
            <p className="mt-2 font-display text-4xl font-semibold tabular text-ink">
              Gratuit
            </p>
            <p className="mt-1 text-sm text-ink-faint">7 jours, sans code</p>
            <PlanList items={ESSAI} />
            <Link
              to="/signup"
              className="mt-7 inline-flex h-11 w-full items-center justify-center rounded-lg border border-line bg-surface text-sm font-medium text-ink hover:bg-secondary"
            >
              Commencer l'essai
            </Link>
          </div>

          <div
            data-reveal
            data-reveal-delay="0.08"
            className="relative rounded-xl border-2 border-primary bg-surface p-6 shadow-[var(--shadow-card)]"
          >
            <span className="absolute -top-3 left-6 rounded-full bg-primary px-3 py-1 text-xs font-medium text-white">
              Recommande
            </span>
            <p className="text-sm font-medium text-ink-faint">Pro</p>
            <p className="mt-2 font-display text-4xl font-semibold tabular text-ink">
              5 000{" "}
              <span className="text-lg font-medium text-ink-faint">
                FCFA / mois
              </span>
            </p>
            <p className="mt-1 text-sm text-ink-faint">active par code</p>
            <PlanList items={PRO} />
            <Link
              to="/signup"
              className="mt-7 inline-flex h-11 w-full items-center justify-center rounded-lg bg-primary text-sm font-medium text-white hover:bg-primary-deep"
            >
              Obtenir un code
            </Link>
          </div>
        </div>

        <div className="mx-auto mt-8 flex max-w-3xl items-center justify-center gap-6 text-xs text-ink-faint">
          {RAILS.map((r) => (
            <span key={r} className="flex items-center gap-1.5">
              <Wallet className="size-4" /> {r}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}

function PlanList({ items }: { items: string[] }) {
  return (
    <ul className="mt-6 space-y-3 text-sm text-ink-muted">
      {items.map((i) => (
        <li key={i} className="flex gap-2">
          <Check className="size-4 shrink-0 text-primary" /> {i}
        </li>
      ))}
    </ul>
  )
}
