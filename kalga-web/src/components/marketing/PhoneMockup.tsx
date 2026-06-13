import { BatteryFull, Check, CheckCheck, Signal, Wifi } from "lucide-react"

/**
 * Mockup telephone montrant une vraie negociation menee par le bot KALGA.
 * Pose hors du flux de texte du hero ; flottement GSAP applique par le parent
 * via le ref transmis. Le `data-phone` sert de cible a l'animation flottante.
 */
export function PhoneMockup() {
  return (
    <div className="relative" data-phone>
      {/* Halo doux derriere le telephone, monochrome (pas d'orbe colore). */}
      <div
        aria-hidden
        className="absolute -inset-6 -z-10 rounded-[3rem] bg-surface/60 blur-2xl"
      />

      <div className="overflow-hidden rounded-[2.25rem] border border-line bg-surface shadow-[var(--shadow-card)] ring-1 ring-black/[0.02]">
        <div className="flex items-center justify-between bg-stone-900 px-5 py-2 text-[11px] text-white">
          <span className="font-medium tabular">9:41</span>
          <span className="flex items-center gap-1">
            <Signal className="size-3" />
            <Wifi className="size-3" />
            <BatteryFull className="size-3.5" />
          </span>
        </div>

        <div className="flex items-center gap-3 border-b border-line px-4 py-3">
          <div className="grid size-9 place-items-center rounded-full bg-primary-tint font-display text-sm font-semibold text-primary-deep">
            AT
          </div>
          <div className="leading-tight">
            <p className="text-sm font-medium text-ink">Aminata (cliente)</p>
            <p className="flex items-center gap-1 text-[11px] text-primary">
              <span className="size-1.5 animate-pulse rounded-full bg-primary" />
              le bot repond...
            </p>
          </div>
        </div>

        <div className="space-y-2.5 bg-stone-100 px-3 py-4">
          <Bubble from="client" time="20:14">
            Bonsoir, le sac ref{" "}
            <span className="font-mono text-xs">SAC-204</span> il coute combien ?
          </Bubble>
          <Bubble from="bot" time="20:14">
            Bonsoir Aminata. Le sac SAC-204 est a{" "}
            <span className="font-semibold tabular">18 000 FCFA</span>,
            disponible en noir et marron.
          </Bubble>
          <Bubble from="client" time="20:15">
            15 000 c'est possible ?
          </Bubble>
          <Bubble from="bot" time="20:15">
            Je peux faire{" "}
            <span className="font-semibold tabular">16 500 FCFA</span>, c'est mon
            meilleur prix. Je vous le reserve ?
          </Bubble>
        </div>
      </div>

      {/* Pastille "vente conclue" flottante, ancre le resultat en argent. */}
      <div className="absolute -bottom-4 -left-4 flex items-center gap-2 rounded-full border border-line bg-surface px-3.5 py-2 shadow-[var(--shadow-card)]">
        <span className="grid size-5 place-items-center rounded-full bg-primary text-white">
          <Check className="size-3" />
        </span>
        <span className="text-xs font-medium text-ink">
          Vente conclue
          <span className="ml-1.5 tabular text-primary-deep">16 500 FCFA</span>
        </span>
      </div>
    </div>
  )
}

function Bubble({
  from,
  time,
  children,
}: {
  from: "client" | "bot"
  time: string
  children: React.ReactNode
}) {
  if (from === "bot") {
    return (
      <div className="ml-auto max-w-[82%]">
        <div className="rounded-2xl rounded-tr-sm bg-primary px-3 py-2 text-sm text-white">
          {children}
        </div>
        <p className="mt-0.5 flex items-center justify-end gap-1 pr-1 text-[10px] text-ink-faint">
          {time} <CheckCheck className="size-3 text-primary" />
        </p>
      </div>
    )
  }
  return (
    <div className="max-w-[82%]">
      <div className="rounded-2xl rounded-tl-sm border border-line bg-white px-3 py-2 text-sm text-ink-muted">
        {children}
      </div>
      <p className="mt-0.5 pl-1 text-[10px] text-ink-faint">{time}</p>
    </div>
  )
}
