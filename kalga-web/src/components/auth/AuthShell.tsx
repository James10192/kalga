import * as React from "react"
import { Link } from "@tanstack/react-router"
import { useEffect, useRef } from "react"
import { gsap } from "gsap"
import { AuthBrandRail } from "./AuthBrandRail"

interface AuthShellProps {
  /** Titre principal de la carte. */
  title: string
  /** Sous-titre court sous le titre. */
  subtitle?: string
  children: React.ReactNode
  /** Pied de carte (liens secondaires). */
  footer?: React.ReactNode
  /**
   * Accroche du panneau de marque (desktop). Variante par page :
   * "signup" met en avant la creation, "login" le retour.
   */
  rail?: "login" | "signup"
}

/**
 * Coquille des pages publiques d'authentification (signup / login).
 *
 * Mise en page :
 *  - Mobile : une seule colonne centree, marque en haut, carte formulaire.
 *  - Desktop (>= lg) : split deux colonnes. A gauche un panneau de marque
 *    chaleureux (la promesse KALGA + un apercu de conversation). A droite le
 *    formulaire, sans carte flottante (ancre au panneau).
 *
 * Aucune dependance auth/Convex : ces pages rendent sans organisation active.
 */
export function AuthShell({
  title,
  subtitle,
  children,
  footer,
  rail = "login",
}: AuthShellProps) {
  const formRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (typeof window === "undefined") return
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return
    const ctx = gsap.context(() => {
      gsap.from("[data-auth-reveal]", {
        y: 14,
        opacity: 0,
        duration: 0.5,
        ease: "power2.out",
        stagger: 0.06,
        clearProps: "transform,opacity",
      })
    }, formRef)
    return () => ctx.revert()
  }, [])

  return (
    <div className="min-h-screen bg-page text-ink antialiased">
      <div className="mx-auto grid min-h-screen w-full max-w-6xl lg:grid-cols-2">
        {/* Panneau de marque — desktop uniquement */}
        <AuthBrandRail variant={rail} />

        {/* Colonne formulaire */}
        <div className="flex flex-col px-5 py-8 sm:px-8 lg:px-12 lg:py-12">
          {/* Marque compacte (mobile) + lien retour discret (desktop) */}
          <div className="flex items-center justify-between">
            <Link
              to="/"
              className="flex items-center gap-2 lg:hidden"
              aria-label="Accueil KALGA"
            >
              <BrandMark />
              <span className="font-display text-xl font-semibold tracking-tight">
                KALGA
              </span>
            </Link>
            <span className="hidden lg:block" />
            <Link
              to="/"
              className="hidden text-sm font-medium text-ink-muted transition-colors hover:text-ink lg:inline"
            >
              Retour au site
            </Link>
          </div>

          <main className="flex flex-1 flex-col justify-center py-8 lg:py-0">
            <div ref={formRef} className="mx-auto w-full max-w-md">
              <header data-auth-reveal>
                <h1 className="font-display text-[1.75rem] font-semibold leading-tight tracking-tight md:text-3xl">
                  {title}
                </h1>
                {subtitle ? (
                  <p className="mt-2 text-[15px] leading-relaxed text-ink-muted">
                    {subtitle}
                  </p>
                ) : null}
              </header>

              <div data-auth-reveal className="mt-7">
                {children}
              </div>

              {footer ? (
                <div
                  data-auth-reveal
                  className="mt-8 border-t border-line pt-6 text-center text-sm text-ink-muted"
                >
                  {footer}
                </div>
              ) : null}
            </div>
          </main>

          {/* Reassurance bas de page (mobile + desktop) */}
          <p className="mt-6 text-center text-xs text-ink-faint lg:text-left">
            En continuant, vous acceptez nos conditions d'utilisation.
          </p>
        </div>
      </div>
    </div>
  )
}

/** Pastille de marque KALGA (carre vert, K Bricolage). */
export function BrandMark() {
  return (
    <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary font-display text-lg font-bold text-white shadow-soft">
      K
    </span>
  )
}

/** Label de champ aligne sur les tokens (text-sm font-medium). */
export function FieldLabel({
  htmlFor,
  children,
}: {
  htmlFor: string
  children: React.ReactNode
}) {
  return (
    <label
      htmlFor={htmlFor}
      className="mb-1.5 block text-sm font-medium text-ink"
    >
      {children}
    </label>
  )
}
