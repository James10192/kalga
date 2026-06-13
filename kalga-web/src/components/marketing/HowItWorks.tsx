import { Bot, PackagePlus, Smartphone, type LucideIcon } from "lucide-react"
import { useRef } from "react"
import { useReveal } from "./useReveal"

/**
 * Section "Comment ca marche" : trois etapes pour vendre.
 * Scroll-reveal GSAP via useReveal (gsap brut, SSR-safe, reduced-motion ok).
 */
const STEPS: { icon: LucideIcon; num: string; title: string; body: string }[] = [
  {
    icon: Smartphone,
    num: "01",
    title: "Connectez WhatsApp",
    body: "Liez votre numero une seule fois, par code ou QR. KALGA se branche a votre numero existant, rien a changer pour vos clients.",
  },
  {
    icon: PackagePlus,
    num: "02",
    title: "Ajoutez vos produits",
    body: "Photo, prix, stock, prix plancher pour la negociation. Vos articles ont un code que le bot reconnait dans les messages.",
  },
  {
    icon: Bot,
    num: "03",
    title: "Le bot vend et negocie",
    body: "Il repond, propose des prix dans vos limites, gere le stock et vous previent quand une commande est prete a conclure.",
  },
]

export function HowItWorks() {
  const scope = useRef<HTMLElement>(null)
  useReveal(scope)

  return (
    <section id="how" ref={scope} className="border-b border-line">
      <div className="mx-auto max-w-6xl px-4 py-16 md:px-8 md:py-24">
        <div className="max-w-2xl">
          <p data-reveal className="text-sm font-medium text-primary">
            Comment ca marche
          </p>
          <h2
            data-reveal
            className="mt-2 font-display text-3xl font-semibold tracking-tight text-ink md:text-4xl"
          >
            Pret a vendre en trois etapes.
          </h2>
          <p data-reveal className="mt-3 text-ink-muted">
            Pas d'installation compliquee. Vous gardez votre numero WhatsApp et
            votre facon de travailler.
          </p>
        </div>

        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {STEPS.map(({ icon: Icon, num, title, body }) => (
            <div
              key={num}
              data-reveal
              className="group rounded-xl border border-line bg-surface p-6 transition-shadow hover:shadow-[var(--shadow-card)]"
            >
              <div className="flex items-center justify-between">
                <span className="grid size-11 place-items-center rounded-lg bg-primary-tint text-primary-deep transition-transform group-hover:scale-105">
                  <Icon className="size-5" />
                </span>
                <span className="font-display text-4xl font-semibold tabular text-ink-faint/60">
                  {num}
                </span>
              </div>
              <h3 className="mt-5 text-lg font-medium text-ink">{title}</h3>
              <p className="mt-2 text-sm text-ink-muted">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
