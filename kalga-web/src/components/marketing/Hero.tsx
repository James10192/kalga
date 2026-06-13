import { Link } from "@tanstack/react-router"
import { ArrowRight, ShieldCheck } from "lucide-react"
import { useEffect, useRef } from "react"
import { PhoneMockup } from "./PhoneMockup"

/**
 * Hero de la landing : composition deux colonnes sur >=lg (texte + badge + h1 +
 * paragraphe + CTAs a gauche, mockup telephone a droite, centres verticalement
 * ensemble), empile sur mobile. Le hero a son propre padding-bas pour que la
 * bande de stats soit nettement separee.
 *
 * Animations GSAP (gotcha 0bis : gsap brut + gsap.context + ctx.revert, jamais
 * @gsap/react). Entree echelonnee du contenu + flottement continu du telephone.
 * SSR-safe : rendu initial visible, GSAP anime FROM ; reduced-motion respecte.
 */
export function Hero() {
  const scope = useRef<HTMLElement>(null)

  useEffect(() => {
    if (typeof window === "undefined") return
    const root = scope.current
    if (!root) return
    const reduce = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches
    if (reduce) return

    let ctx: { revert: () => void } | undefined
    let failsafe = 0
    let cancelled = false

    void import("gsap").then(({ default: gsap }) => {
      if (cancelled || !scope.current) return
      ctx = gsap.context(() => {
        gsap.from("[data-hero-item]", {
          opacity: 0,
          y: 18,
          duration: 0.6,
          ease: "power3.out",
          stagger: 0.09,
        })
        gsap.from("[data-phone]", {
          opacity: 0,
          y: 28,
          scale: 0.97,
          duration: 0.7,
          ease: "power3.out",
          delay: 0.2,
        })
        gsap.to("[data-phone]", {
          y: -10,
          duration: 3.2,
          ease: "sine.inOut",
          yoyo: true,
          repeat: -1,
          delay: 0.9,
        })
      }, root)

      // FAILSAFE anti-strand : si l'entree n'a pas abouti (ticker rAF gele : nav
      // SPA, onglet en arriere-plan), on TUE le tween de l'element puis on force
      // la visibilite via le style DIRECT (sinon le tween fige reasserte son
      // opacity au tick suivant). Condition sur l'opacity => en navigation
      // normale (entree finie), on ne touche a rien (le flottement est preserve).
      failsafe = window.setTimeout(() => {
        root
          .querySelectorAll<HTMLElement>("[data-hero-item],[data-phone]")
          .forEach((el) => {
            if (Number(getComputedStyle(el).opacity) < 0.95) {
              gsap.killTweensOf(el)
              el.style.opacity = "1"
              el.style.transform = "none"
            }
          })
      }, 1000)
    })

    return () => {
      cancelled = true
      if (failsafe) window.clearTimeout(failsafe)
      ctx?.revert()
    }
  }, [])

  return (
    <section
      ref={scope}
      className="relative overflow-hidden border-b border-line"
      style={{
        backgroundImage: "radial-gradient(#eceae3 1px, transparent 1px)",
        backgroundSize: "22px 22px",
      }}
    >
      <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 pb-20 pt-16 md:px-8 md:pt-24 lg:grid-cols-[1.05fr_0.95fr] lg:gap-10 lg:pb-28">
        {/* Colonne texte */}
        <div className="max-w-xl text-center lg:text-left">
          <span
            data-hero-item
            className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-xs font-medium text-ink-muted"
          >
            <span className="size-1.5 rounded-full bg-primary" />
            Commerce WhatsApp automatise, sans coder
          </span>

          <h1
            data-hero-item
            className="mt-6 font-display text-[2.65rem] font-semibold leading-[1.04] tracking-tight text-ink md:text-6xl lg:text-[4.25rem]"
          >
            Votre vendeur WhatsApp qui ne dort{" "}
            <span className="text-primary">jamais</span>.
          </h1>

          <p
            data-hero-item
            className="mx-auto mt-5 max-w-lg text-base text-ink-muted md:text-lg lg:mx-0"
          >
            KALGA repond a vos clients, negocie les prix et conclut les ventes,
            24h/24, pendant que vous publiez vos statuts. Vous gardez le
            controle, le bot fait le travail repetitif.
          </p>

          <div
            data-hero-item
            className="mt-8 flex flex-col items-center gap-3 sm:flex-row lg:justify-start"
          >
            <Link
              to="/signup"
              className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-primary px-6 text-base font-medium text-white transition-colors hover:bg-primary-deep sm:w-auto"
            >
              Connecter mon WhatsApp
              <ArrowRight className="size-4" />
            </Link>
            <a
              href="#how"
              className="inline-flex h-12 w-full items-center justify-center rounded-lg border border-line bg-surface px-6 text-base font-medium text-ink-muted transition-colors hover:bg-secondary sm:w-auto"
            >
              Voir comment
            </a>
          </div>

          <p
            data-hero-item
            className="mt-4 flex items-center justify-center gap-1.5 text-xs text-ink-faint lg:justify-start"
          >
            <ShieldCheck className="size-3.5" />
            Activation par code apres paiement Wave ou Orange Money. Pas de carte
            bancaire.
          </p>
        </div>

        {/* Colonne mockup, centree verticalement avec le texte */}
        <div className="mx-auto w-full max-w-sm lg:mx-0 lg:justify-self-end">
          <PhoneMockup />
        </div>
      </div>

      <StatStrip />
    </section>
  )
}

/** Bande de statistiques, nettement separee du hero (padding-bas du hero). */
function StatStrip() {
  const stats = [
    { value: "24/7", label: "reponses automatiques" },
    { value: "< 5s", label: "temps de reponse moyen" },
    { value: "0", label: "client laisse sans reponse" },
  ]
  return (
    <div className="border-t border-line bg-surface">
      <div className="mx-auto grid max-w-6xl grid-cols-3 divide-x divide-line px-4 md:px-8">
        {stats.map((s) => (
          <div key={s.label} className="py-6 text-center md:py-8">
            <p className="font-display text-2xl font-semibold tabular text-ink md:text-4xl">
              {s.value}
            </p>
            <p className="mt-1 text-xs text-ink-faint">{s.label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
