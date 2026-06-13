import { Link } from "@tanstack/react-router"
import { Check, ExternalLink, Globe } from "lucide-react"
import { useRef } from "react"
import { useReveal } from "./useReveal"

/**
 * Section "Votre boutique" : argumentaire vitrine publique + apercu navigateur.
 * Le CTA mene vers une boutique de demo (storefront public par slug).
 * Scroll-reveal GSAP via useReveal (gsap brut, SSR-safe, reduced-motion ok).
 */
const POINTS = [
  "Mise a jour automatique depuis votre stock",
  "Bouton commander directement sur WhatsApp",
  "Lien partageable sur vos statuts et stories",
]

export function StorefrontShowcase() {
  const scope = useRef<HTMLElement>(null)
  useReveal(scope)

  return (
    <section id="boutique" ref={scope} className="border-b border-line">
      <div className="mx-auto max-w-6xl px-4 py-16 md:px-8 md:py-24">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <div>
            <p data-reveal className="text-sm font-medium text-primary">
              Votre boutique
            </p>
            <h2
              data-reveal
              className="mt-2 font-display text-3xl font-semibold tracking-tight text-ink md:text-4xl"
            >
              Une vitrine prete, a votre nom.
            </h2>
            <p data-reveal className="mt-3 text-ink-muted">
              Chaque marchand obtient une boutique publique en ligne. Vos clients
              parcourent le catalogue, voient les prix, et commandent en un tap
              sur WhatsApp.
            </p>

            <div
              data-reveal
              className="mt-6 inline-flex items-center gap-2 rounded-lg border border-line bg-surface px-4 py-3"
            >
              <Globe className="size-4 text-ink-faint" />
              <span className="font-mono text-sm">
                <span className="text-ink-faint">https://</span>
                <span className="font-medium text-primary-deep">chez-fatou</span>
                <span className="text-ink-faint">.kalga.app</span>
              </span>
            </div>

            <ul data-reveal className="mt-6 space-y-3 text-sm text-ink-muted">
              {POINTS.map((p) => (
                <li key={p} className="flex items-center gap-2">
                  <Check className="size-4 text-primary" /> {p}
                </li>
              ))}
            </ul>

            <Link
              data-reveal
              to="/boutique/$slug"
              params={{ slug: "chez-fatou" }}
              className="mt-7 inline-flex h-11 items-center gap-2 rounded-lg border border-line bg-surface px-5 text-sm font-medium text-ink-muted transition-colors hover:bg-secondary"
            >
              Voir une boutique de demo <ExternalLink className="size-4" />
            </Link>
          </div>

          <div data-reveal>
            <BrowserPreview />
          </div>
        </div>
      </div>
    </section>
  )
}

/** Apercu navigateur d'une boutique de demo. */
function BrowserPreview() {
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-surface shadow-[var(--shadow-soft)]">
      <div className="flex items-center gap-2 border-b border-line bg-secondary px-3 py-2.5">
        <span className="size-2.5 rounded-full bg-stone-300" />
        <span className="size-2.5 rounded-full bg-stone-300" />
        <span className="size-2.5 rounded-full bg-stone-300" />
        <span className="ml-3 flex-1 rounded-md bg-surface px-3 py-1 font-mono text-[11px] text-ink-faint">
          chez-fatou.kalga.app
        </span>
      </div>
      <div className="p-4">
        <div className="flex items-center gap-3 border-b border-line pb-4">
          <div className="grid size-11 place-items-center rounded-full bg-primary-tint font-display font-semibold text-primary-deep">
            CF
          </div>
          <div>
            <p className="font-medium text-ink">Chez Fatou</p>
            <p className="text-xs text-ink-faint">
              Pret-a-porter femme. Cocody, Abidjan
            </p>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <ProductTile name="Robe wax longue" price="22 000 FCFA" />
          <ProductTile name="Sac a main cuir" price="18 000 FCFA" />
        </div>
      </div>
    </div>
  )
}

function ProductTile({ name, price }: { name: string; price: string }) {
  return (
    <div className="overflow-hidden rounded-lg border border-line">
      <div className="aspect-square bg-gradient-to-br from-stone-200 to-stone-100" />
      <div className="p-2.5">
        <p className="truncate text-xs font-medium text-ink">{name}</p>
        <p className="text-sm font-semibold tabular text-primary-deep">{price}</p>
      </div>
    </div>
  )
}
