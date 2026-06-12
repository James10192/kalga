import { Bot, User } from "lucide-react"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { StatusChip } from "./StatusChip"
import {
  formatAmount,
  initials,
  isPhoneIdentity,
  statusKind,
  timeAgo,
  type ConversationStatus,
  type StatusKind,
} from "./format"

export type ConversationRowData = {
  conversationId: string
  /** Nom du client ou numéro brut. */
  displayName: string
  status: ConversationStatus
  updatedAt: number
  /** Aperçu du dernier message. */
  preview: string | null
  /** Vrai si le dernier message vient du bot/marchand (glyphe bot affiché). */
  fromBot: boolean
  /** Point vert non-lu (dernier message du client non traité). */
  unread: boolean
  /** Ligne argent contextuelle (offre/demande, montant payé, prix produit). */
  moneyLine: string | null
}

/** Couleur de l'avatar selon la variante de statut (tons mats chauds). */
const AVATAR_STYLES: Record<StatusKind, string> = {
  nego: "bg-[#F3E9DF] text-[#8A5A2B]",
  livrer: "bg-[#E6EBF6] text-[#3457A6]",
  paye: "bg-primary-tint text-primary-deep",
  rupture: "bg-danger-tint text-danger",
  nouveau: "bg-[#EFEDE6] text-ink-faint",
}

/**
 * Rangée de conversation (la colonne vertébrale, DIRECTION.md).
 * Avatar initiales + nom + aperçu + StatusChip + ligne argent + point non-lu +
 * glyphe bot. Cible tactile généreuse (>= 48px), tap = ouvre le détail.
 */
export function ConversationRow({
  data,
  onClick,
}: {
  data: ConversationRowData
  onClick?: () => void
}) {
  const kind = statusKind(data.status)
  const phone = isPhoneIdentity(data.displayName)
  const monogram = initials(data.displayName)

  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-start gap-3 rounded-2xl p-2.5 text-left transition hover:bg-surface active:bg-surface"
    >
      <span
        className={cn(
          "grid h-12 w-12 shrink-0 place-items-center rounded-full font-display text-[15px] font-bold",
          AVATAR_STYLES[kind],
        )}
      >
        {phone || !monogram ? <User className="h-5 w-5" /> : monogram}
      </span>

      <span className="min-w-0 flex-1">
        <span className="flex items-center justify-between gap-2">
          <span className="truncate text-[15px] font-semibold">
            {data.displayName}
          </span>
          <span className="shrink-0 text-[12px] text-ink-faint">
            {timeAgo(data.updatedAt)}
          </span>
        </span>

        <span className="mt-0.5 flex items-center justify-between gap-2">
          <span className="flex min-w-0 items-center gap-1.5">
            {data.fromBot && (
              <Bot className="h-3.5 w-3.5 shrink-0 text-ink-faint" />
            )}
            <span className="truncate text-[13.5px] text-ink-muted">
              {data.preview ?? "Nouvelle conversation"}
            </span>
          </span>
          {data.unread && (
            <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-primary" />
          )}
        </span>

        <span className="mt-1.5 flex items-center gap-2">
          <StatusChip kind={kind} />
          {data.moneyLine && (
            <span className="truncate text-[12px] text-ink-muted tabular">
              {data.moneyLine}
            </span>
          )}
        </span>
      </span>
    </button>
  )
}

/** Construit la ligne argent d'une conversation selon son statut. */
export function buildMoneyLine(params: {
  status: ConversationStatus
  currentOffer: number | null
  productName: string | null
  productPrice: number | null
  amount: number | null
}): string | null {
  const { status, currentOffer, productName, productPrice, amount } = params
  const kind = statusKind(status)

  if (kind === "nego" && currentOffer !== null && productPrice !== null) {
    return `Offre ${formatAmount(currentOffer)} · demande ${formatAmount(productPrice)}`
  }
  if (kind === "paye" && amount !== null) {
    return `${formatAmount(amount)} FCFA`
  }
  if (kind === "livrer" && productName && amount !== null) {
    return `${productName} · ${formatAmount(amount)} FCFA`
  }
  if (productName && (productPrice !== null || amount !== null)) {
    return `${productName} · ${formatAmount(productPrice ?? amount)}`
  }
  return null
}

/** Skeleton d'une rangée de conversation. */
export function ConversationRowSkeleton() {
  return (
    <div className="flex w-full items-start gap-3 p-2.5">
      <Skeleton className="h-12 w-12 shrink-0 rounded-full" />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-10" />
        </div>
        <Skeleton className="h-3.5 w-48" />
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-3 w-28" />
        </div>
      </div>
    </div>
  )
}
