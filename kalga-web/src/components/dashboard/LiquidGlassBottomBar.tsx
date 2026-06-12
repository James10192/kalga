import { useEffect, useRef, useState } from "react"
import { Link } from "@tanstack/react-router"
import {
  MessagesSquare,
  ShoppingBag,
  Wallet,
  Settings,
  Home,
  type LucideIcon,
} from "lucide-react"
import gsap from "gsap"
import { cn } from "@/lib/utils"

type TabKey = "accueil" | "conversations" | "produits" | "argent" | "reglages"

type SideTab = {
  key: TabKey
  label: string
  icon: LucideIcon
  to: string
}

// Les 4 onglets latéraux (le FAB Accueil central est rendu à part).
const LEFT_TABS: SideTab[] = [
  { key: "conversations", label: "Conversations", icon: MessagesSquare, to: "/app/conversations" },
  { key: "produits", label: "Produits", icon: ShoppingBag, to: "/app/products" },
]
const RIGHT_TABS: SideTab[] = [
  { key: "argent", label: "Argent", icon: Wallet, to: "/app/money" },
  { key: "reglages", label: "Réglages", icon: Settings, to: "/app/settings" },
]

// Géométrie SVG de la barre (viewBox responsive en largeur).
const W = 440 // largeur de référence (s'étire via preserveAspectRatio none)
const H = 84 // hauteur de la barre
const TOP = 18 // ligne haute « plate » de la barre
const CX = W / 2 // centre horizontal (sous le FAB)
const NOTCH_HALF = 54 // demi-largeur de la cuvette
const BASE_DEPTH = 26 // profondeur de repos de l'encoche

/** Construit le `d` du path : plat -> cuvette concave (cubic bezier) -> plat. */
function buildPath(depth: number): string {
  const left = CX - NOTCH_HALF
  const right = CX + NOTCH_HALF
  const bottom = depth // profondeur du creux sous la ligne TOP
  // Les poignées de bézier contrôlent la douceur de la cuvette.
  const ctrl = NOTCH_HALF * 0.62
  return [
    `M0 ${TOP}`,
    `H${left}`,
    // descente vers le fond du creux
    `C${left + ctrl} ${TOP} ${CX - ctrl} ${TOP + bottom} ${CX} ${TOP + bottom}`,
    // remontée symétrique
    `C${CX + ctrl} ${TOP + bottom} ${right - ctrl} ${TOP} ${right} ${TOP}`,
    `H${W}`,
    `V${H}`,
    `H0`,
    `Z`,
  ].join(" ")
}

const prefersReduced = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches

/**
 * Barre de navigation « liquid glass » (pièce maîtresse du dashboard 006).
 * 5 zones : Conversations | Produits | (FAB Accueil) | Argent | Réglages.
 * Le bord haut a une encoche concave sous le FAB central, rendue en SVG et
 * animée au GSAP (settle au mount, enfoncement élastique au press du FAB).
 * SSR-safe : rendu statique en SVG/CSS, GSAP n'anime qu'au mount client.
 */
export function LiquidGlassBottomBar({ active }: { active: TabKey }) {
  const scope = useRef<HTMLElement>(null)
  const pathRef = useRef<SVGPathElement>(null)
  const fabRef = useRef<HTMLDivElement>(null)
  const depthProxy = useRef({ depth: BASE_DEPTH })
  const [pressing, setPressing] = useState(false)

  // GSAP via useEffect + gsap.context (PAS @gsap/react, qui injecte une 2e copie
  // de React -> "Invalid hook call" -> page blanche). Client-only par nature.
  useEffect(() => {
    if (prefersReduced()) return
    const ctx = gsap.context(() => {
      const proxy = depthProxy.current
      const sync = () => {
        if (pathRef.current) pathRef.current.setAttribute("d", buildPath(proxy.depth))
      }
      // Settle au mount : la bille « rentre » doucement dans la surface.
      gsap.fromTo(
        proxy,
        { depth: BASE_DEPTH + 16 },
        { depth: BASE_DEPTH, duration: 0.9, ease: "elastic.out(1, 0.55)", onUpdate: sync },
      )
      gsap.fromTo(
        fabRef.current,
        { y: -6, scale: 0.92 },
        { y: 0, scale: 1, duration: 0.9, ease: "elastic.out(1, 0.5)" },
      )
    }, scope)
    return () => ctx.revert()
  }, [])

  // Press du FAB : la cuvette s'approfondit puis revient en élastique.
  const onFabPress = () => {
    setPressing(true)
    if (prefersReduced()) return
    const proxy = depthProxy.current
    const sync = () => {
      if (pathRef.current) pathRef.current.setAttribute("d", buildPath(proxy.depth))
    }
    gsap.killTweensOf(proxy)
    gsap
      .timeline()
      .to(proxy, { depth: BASE_DEPTH + 12, duration: 0.16, ease: "power2.in", onUpdate: sync })
      .to(proxy, { depth: BASE_DEPTH, duration: 0.85, ease: "elastic.out(1, 0.45)", onUpdate: sync })
    gsap
      .timeline()
      .to(fabRef.current, { scale: 0.9, y: 3, duration: 0.16, ease: "power2.in" })
      .to(fabRef.current, { scale: 1, y: 0, duration: 0.7, ease: "elastic.out(1, 0.4)" })
  }
  const onFabRelease = () => setPressing(false)

  const accueilActive = active === "accueil"

  return (
    <nav
      ref={scope}
      aria-label="Navigation principale"
      className="pointer-events-none fixed inset-x-0 bottom-0 z-40 flex justify-center"
    >
      {/* Colonne cadrée mobile, alignée sur l'AppShell. */}
      <div className="pointer-events-auto relative w-full max-w-[440px]">
        {/* Couche verre dépoli, masquée à la forme du path SVG. */}
        <div
          className="absolute inset-x-0 bottom-0 backdrop-blur-xl"
          style={{
            height: H,
            paddingBottom: "env(safe-area-inset-bottom)",
            WebkitMaskImage: "var(--lg-mask)",
            maskImage: "var(--lg-mask)",
            WebkitMaskSize: "100% 100%",
            maskSize: "100% 100%",
            background:
              "linear-gradient(180deg, rgba(255,255,255,.78) 0%, rgba(255,251,244,.72) 100%)",
            // @ts-expect-error custom prop pour le mask SVG
            "--lg-mask": `url("data:image/svg+xml;utf8,${encodeURIComponent(
              `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 ${W} ${H}' preserveAspectRatio='none'><path d='${buildPath(BASE_DEPTH)}' fill='black'/></svg>`,
            )}")`,
          }}
        />

        {/* Le SVG porte le contour (bord haut clair + ombre douce vers le haut). */}
        <svg
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="none"
          className="absolute inset-x-0 bottom-0 h-[84px] w-full"
          style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
          aria-hidden
        >
          <defs>
            <filter id="lg-soft-shadow" x="-20%" y="-60%" width="140%" height="180%">
              <feDropShadow dx="0" dy="-6" stdDeviation="10" floodColor="#1C1A17" floodOpacity="0.10" />
            </filter>
            <linearGradient id="lg-edge" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="rgba(255,255,255,.95)" />
              <stop offset="1" stopColor="rgba(255,255,255,0)" />
            </linearGradient>
          </defs>
          {/* Ombre douce portée vers le haut (forme = path). */}
          <path d={buildPath(BASE_DEPTH)} fill="rgba(255,255,255,0.001)" filter="url(#lg-soft-shadow)" />
          {/* Highlight 1px clair sur le bord haut. */}
          <path
            ref={pathRef}
            d={buildPath(BASE_DEPTH)}
            fill="none"
            stroke="url(#lg-edge)"
            strokeWidth={1.5}
            vectorEffect="non-scaling-stroke"
          />
        </svg>

        {/* Rangée des 4 onglets latéraux (le FAB occupe le centre). */}
        <div
          className="relative grid grid-cols-5 items-end"
          style={{ height: H, paddingBottom: "calc(env(safe-area-inset-bottom) + 6px)" }}
        >
          {LEFT_TABS.map((tab) => (
            <SideTabItem key={tab.key} tab={tab} active={tab.key === active} />
          ))}

          {/* Cellule centrale vide : le FAB est positionné en absolute par-dessus. */}
          <div aria-hidden />

          {RIGHT_TABS.map((tab) => (
            <SideTabItem key={tab.key} tab={tab} active={tab.key === active} />
          ))}
        </div>

        {/* FAB ACCUEIL central, surélevé (mi-hauteur au-dessus de la barre). */}
        <Link
          to="/app"
          aria-label="Accueil"
          aria-current={accueilActive ? "page" : undefined}
          className="pointer-events-auto absolute left-1/2 z-10 -translate-x-1/2"
          style={{ bottom: "calc(env(safe-area-inset-bottom) + 38px)" }}
          onPointerDown={onFabPress}
          onPointerUp={onFabRelease}
          onPointerLeave={onFabRelease}
        >
          <div
            ref={fabRef}
            className={cn(
              "relative grid h-16 w-16 place-items-center rounded-full",
              "shadow-[0_10px_28px_-6px_rgba(22,163,74,.45),0_2px_8px_rgba(28,26,23,.18)]",
              "transition-colors",
            )}
            style={{
              // Bille « liquid glass » : verre dépoli teinté chaud + ring.
              background:
                "radial-gradient(120% 120% at 32% 24%, rgba(255,255,255,.55), rgba(255,255,255,.06) 42%), linear-gradient(160deg, rgba(22,163,74,.92), rgba(21,128,61,.96))",
              boxShadow: pressing
                ? "inset 0 2px 6px rgba(0,0,0,.25), 0 6px 16px -4px rgba(22,163,74,.4)"
                : undefined,
              backdropFilter: "blur(8px)",
            }}
          >
            {/* Highlight spéculaire radial. */}
            <span
              aria-hidden
              className="pointer-events-none absolute inset-0 rounded-full"
              style={{
                background:
                  "radial-gradient(60% 45% at 38% 26%, rgba(255,255,255,.7), rgba(255,255,255,0) 70%)",
              }}
            />
            {/* Ring subtil. */}
            <span
              aria-hidden
              className="pointer-events-none absolute inset-0 rounded-full ring-1 ring-inset ring-white/40"
            />
            <Home
              className={cn(
                "relative h-7 w-7",
                accueilActive ? "text-white" : "text-white/95",
              )}
              strokeWidth={2.2}
            />
          </div>
        </Link>
      </div>
    </nav>
  )
}

function SideTabItem({ tab, active }: { tab: SideTab; active: boolean }) {
  const Icon = tab.icon
  return (
    <Link
      to={tab.to}
      aria-label={tab.label}
      aria-current={active ? "page" : undefined}
      className="relative flex min-h-[48px] flex-col items-center justify-end gap-1 pb-1"
    >
      <span
        className={cn(
          "grid h-9 w-12 place-items-center rounded-full transition-colors",
          active ? "bg-primary-tint text-primary-deep" : "text-ink-muted",
        )}
      >
        <Icon className="h-[22px] w-[22px]" strokeWidth={active ? 2.3 : 2} />
      </span>
      <span
        className={cn(
          "text-[10.5px] leading-none",
          active ? "font-semibold text-primary-deep" : "font-medium text-ink-muted",
        )}
      >
        {tab.label}
      </span>
    </Link>
  )
}

export type { TabKey }
