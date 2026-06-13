import { useEffect, type RefObject } from "react"

/**
 * Hook de scroll-reveal GSAP, partage par les sections marketing.
 *
 * GOTCHA documente (tanstack-start-vite-gotchas, section 0bis) : on utilise
 * `gsap` brut via `useEffect` + `gsap.context(..., scopeRef)` + `ctx.revert()`.
 * JAMAIS `@gsap/react` / `useGSAP` (double copie de React -> page blanche).
 *
 * SSR-safe : le rendu initial est deja visible (le CSS ne cache rien). GSAP
 * anime FROM un etat decale, donc sans JS / sans motion, tout reste lisible.
 * Respecte `prefers-reduced-motion`.
 *
 * @param scope ref du conteneur de section
 * @param selector elements a reveler (defaut : [data-reveal])
 */
export function useReveal(
  scope: RefObject<HTMLElement | null>,
  selector = "[data-reveal]",
) {
  useEffect(() => {
    if (typeof window === "undefined") return
    const root = scope.current
    if (!root) return

    const reduce = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches
    if (reduce) return

    let ctx: { revert: () => void } | undefined

    void (async () => {
      const [{ default: gsap }, { ScrollTrigger }] = await Promise.all([
        import("gsap"),
        import("gsap/ScrollTrigger"),
      ])
      gsap.registerPlugin(ScrollTrigger)

      ctx = gsap.context(() => {
        const items = gsap.utils.toArray<HTMLElement>(selector)
        items.forEach((el) => {
          const delay = Number(el.dataset.revealDelay ?? 0)
          gsap.from(el, {
            opacity: 0,
            y: 22,
            duration: 0.55,
            ease: "power2.out",
            delay,
            scrollTrigger: {
              trigger: el,
              start: "top 88%",
              toggleActions: "play none none none",
            },
          })
        })
      }, root)
    })()

    return () => ctx?.revert()
  }, [scope, selector])
}
