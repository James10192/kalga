import {
  Boxes,
  Handshake,
  MessagesSquare,
  Store,
  type LucideIcon,
} from "lucide-react"
import { useRef } from "react"
import { useReveal } from "./useReveal"

/**
 * Section "Fonctionnalites" : grille 4 capacites du vendeur automatise.
 * Scroll-reveal GSAP via useReveal (gsap brut, SSR-safe, reduced-motion ok).
 */
const FEATURES: {
  icon: LucideIcon
  title: string
  body: React.ReactNode
}[] = [
  {
    icon: Handshake,
    title: "Negociation IA",
    body: "Le bot marchande poliment, jamais en dessous de votre prix plancher. Comme vous le feriez, en plus patient.",
  },
  {
    icon: Boxes,
    title: "Gestion du stock",
    body: "Stock a jour en temps reel. Alerte rupture et stock bas, le bot ne vend jamais ce que vous n'avez plus.",
  },
  {
    icon: Store,
    title: "Boutique en ligne",
    body: (
      <>
        Une vitrine publique automatique sur votre adresse{" "}
        <span className="font-mono text-xs">slug.kalga.app</span>, partageable en
        un lien.
      </>
    ),
  },
  {
    icon: MessagesSquare,
    title: "Conversations en direct",
    body: "Suivez chaque echange en temps reel depuis le tableau de bord. Reprenez la main quand vous voulez.",
  },
]

export function Features() {
  const scope = useRef<HTMLElement>(null)
  useReveal(scope)

  return (
    <section
      id="features"
      ref={scope}
      className="border-b border-line bg-secondary"
    >
      <div className="mx-auto max-w-6xl px-4 py-16 md:px-8 md:py-24">
        <div className="max-w-2xl">
          <p data-reveal className="text-sm font-medium text-primary">
            Fonctionnalites
          </p>
          <h2
            data-reveal
            className="mt-2 font-display text-3xl font-semibold tracking-tight text-ink md:text-4xl"
          >
            Tout ce qu'un bon vendeur sait faire.
          </h2>
        </div>

        <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <div
              key={title}
              data-reveal
              className="group rounded-xl border border-line bg-surface p-6 transition-shadow hover:shadow-[var(--shadow-card)]"
            >
              <span className="grid size-11 place-items-center rounded-lg bg-primary-tint text-primary-deep transition-transform group-hover:scale-105">
                <Icon className="size-5" />
              </span>
              <h3 className="mt-5 font-medium text-ink">{title}</h3>
              <p className="mt-2 text-sm text-ink-muted">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
