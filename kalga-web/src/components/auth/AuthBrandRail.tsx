import { Link } from "@tanstack/react-router"
import { Check, MessageCircle, ShieldCheck, Sparkles } from "lucide-react"
import { BrandMark } from "./AuthShell"

interface AuthBrandRailProps {
  variant: "login" | "signup"
}

/**
 * Panneau de marque (desktop, >= lg). Chaleureux, monochrome chaud + vert
 * chirurgical. Met en scene la promesse KALGA via un apercu de conversation
 * ou le bot negocie et conclut une vente. Pas de gradient/orbe/glassmorphism.
 */
export function AuthBrandRail({ variant }: AuthBrandRailProps) {
  const points =
    variant === "signup"
      ? [
          "Le bot repond et negocie a votre place, jour et nuit.",
          "Vos clients commandent directement depuis WhatsApp.",
          "Suivez vos ventes du jour en un coup d'oeil.",
        ]
      : [
          "Retrouvez vos conversations en cours.",
          "Vos ventes et offres actives, a jour.",
          "Le bot a continue de vendre pendant votre absence.",
        ]

  return (
    <aside className="relative hidden flex-col justify-between overflow-hidden border-r border-line bg-surface px-12 py-12 lg:flex">
      {/* Marque */}
      <Link to="/" className="flex items-center gap-2.5" aria-label="Accueil KALGA">
        <BrandMark />
        <span className="font-display text-xl font-semibold tracking-tight">
          KALGA
        </span>
      </Link>

      {/* Promesse + apercu conversation */}
      <div className="max-w-sm">
        <p className="inline-flex items-center gap-1.5 rounded-full bg-primary-tint px-3 py-1 text-xs font-medium text-primary-deep">
          <Sparkles className="size-3.5" />
          Votre vendeur sur WhatsApp
        </p>
        <h2 className="mt-5 font-display text-[2rem] font-semibold leading-[1.15] tracking-tight">
          Votre WhatsApp devient une boutique qui vend et negocie toute seule.
        </h2>

        <ConversationGlimpse />

        <ul className="mt-8 space-y-3">
          {points.map((point) => (
            <li key={point} className="flex items-start gap-2.5 text-sm text-ink-muted">
              <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-primary-tint text-primary-deep">
                <Check className="size-3" strokeWidth={2.5} />
              </span>
              {point}
            </li>
          ))}
        </ul>
      </div>

      {/* Reassurance bas */}
      <p className="flex items-center gap-2 text-xs text-ink-faint">
        <ShieldCheck className="size-3.5" />
        Connexion securisee. Votre numero reste prive.
      </p>
    </aside>
  )
}

/**
 * Apercu statique d'une conversation KALGA : le client negocie, le bot conclut.
 * Bulles facon WhatsApp (client a gauche, bot a droite en vert), ligne argent.
 */
function ConversationGlimpse() {
  return (
    <div className="mt-7 rounded-2xl border border-line bg-page p-4 shadow-soft">
      <div className="mb-3 flex items-center gap-2 text-xs text-ink-faint">
        <MessageCircle className="size-3.5 text-primary" />
        Negociation en direct
      </div>

      <div className="space-y-2.5">
        {/* Client */}
        <div className="max-w-[80%]">
          <div className="rounded-2xl rounded-tl-sm border border-line bg-surface px-3.5 py-2 text-[13px] text-ink">
            Bonjour, le sac a 15 000, vous faites 12 000 ?
          </div>
        </div>

        {/* Bot */}
        <div className="ml-auto max-w-[82%]">
          <div className="rounded-2xl rounded-tr-sm bg-primary px-3.5 py-2 text-[13px] text-white">
            Je peux vous le faire a 13 500. C'est ma meilleure offre.
          </div>
        </div>

        {/* Client */}
        <div className="max-w-[70%]">
          <div className="rounded-2xl rounded-tl-sm border border-line bg-surface px-3.5 py-2 text-[13px] text-ink">
            D'accord, je prends.
          </div>
        </div>
      </div>

      {/* Ligne argent — issue de la negociation */}
      <div className="mt-3 flex items-center justify-between rounded-xl border border-primary/20 bg-primary-tint px-3.5 py-2.5">
        <span className="text-xs font-medium text-primary-deep">Vente conclue</span>
        <span className="font-display text-base font-semibold tabular text-primary-deep">
          13 500 FCFA
        </span>
      </div>
    </div>
  )
}
