import { useEffect, type RefObject } from "react"

/**
 * Hook de scroll-reveal GSAP, partage par les sections marketing.
 *
 * GOTCHA documente (tanstack-start-vite-gotchas, 0bis) : `gsap` brut via
 * `useEffect`, JAMAIS `@gsap/react` / `useGSAP` (double React -> page blanche).
 *
 * SSR-safe : sans JS le CSS ne cache rien, tout reste lisible. GSAP pose un etat
 * decale puis anime vers visible. Respecte `prefers-reduced-motion`.
 *
 * ANTI-STRANDING (bug landing blanche / figee apres nav SPA) : un reveal couple a
 * ScrollTrigger peut laisser les elements deja en vue invisibles ou figes a mi-
 * opacite lors d'une navigation client (pas d'event `load`, et les `refresh()` en
 * cascade des sections s'interrompent). PARADE = un FAILSAFE viewport : ~1s apres
 * le montage, tout element DANS le viewport encore non visible est force a
 * opacity:1 (les elements hors viewport gardent leur reveal au scroll). Ainsi le
 * contenu visible ne peut JAMAIS rester bloque, quelle que soit la nav.
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
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return

    let killed = false
    let cleanup = () => {}

    void (async () => {
      const [{ default: gsap }, { ScrollTrigger }] = await Promise.all([
        import("gsap"),
        import("gsap/ScrollTrigger"),
      ])
      gsap.registerPlugin(ScrollTrigger)
      if (killed || !scope.current) return

      const items = Array.from(
        root.querySelectorAll<HTMLElement>(selector),
      )
      if (items.length === 0) return

      gsap.set(items, { opacity: 0, y: 22 })

      const tweens = items.map((el) => {
        const delay = Number(el.dataset.revealDelay ?? 0)
        return gsap.to(el, {
          opacity: 1,
          y: 0,
          duration: 0.55,
          ease: "power2.out",
          delay,
          clearProps: "opacity,transform",
          scrollTrigger: { trigger: el, start: "top 90%", once: true },
        })
      })

      ScrollTrigger.refresh()

      // FAILSAFE : ce qui est dans le viewport mais encore (presque) invisible
      // est force a visible. On ecrit le style DIRECTEMENT (pas via gsap) : ainsi,
      // meme si le ticker rAF est gele (onglet en arriere-plan, throttling
      // headless), le contenu vu ne reste JAMAIS bloque. Le reveal au scroll du
      // contenu plus bas est preserve (on ne touche que ce qui est en vue).
      const failsafe = window.setTimeout(() => {
        items.forEach((el, i) => {
          const r = el.getBoundingClientRect()
          const inView = r.top < window.innerHeight && r.bottom > 0
          if (inView && Number(getComputedStyle(el).opacity) < 0.95) {
            tweens[i]?.kill()
            el.style.opacity = "1"
            el.style.transform = "none"
          }
        })
      }, 800)

      cleanup = () => {
        window.clearTimeout(failsafe)
        tweens.forEach((t) => {
          t.scrollTrigger?.kill()
          t.kill()
        })
      }
    })()

    return () => {
      killed = true
      cleanup()
    }
  }, [scope, selector])
}
