import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "convex/react"
import {
  ArrowLeft,
  Bot,
  Check,
  HandCoins,
  MessageSquareOff,
  PackageCheck,
  Truck,
  User,
  type LucideIcon,
} from "lucide-react"
import { api } from "../../../convex/_generated/api"
import type { Id } from "../../../convex/_generated/dataModel"
import { Skeleton } from "@/components/ui/skeleton"
import {
  StatusChip,
  formatAmount,
  initials,
  isPhoneIdentity,
  statusKind,
  timeAgo,
  type ConversationStatus,
  type StatusKind,
} from "@/components/dashboard"

/**
 * Détail conversation (DIRECTION.md, plan 006).
 *
 * Fil de bulles façon WhatsApp (messages client/bot via
 * api.conversations.messagesByConversation) + panneau "affaire" slim (prix
 * demandé, offre actuelle, marge, prix plancher) + actions négociation.
 *
 * Câblé aux données Convex LIVE du marchand démo. Réutilise AppShell +
 * BottomTabBar via le layout /app (onglet Conversations actif). Mêmes tokens
 * que l'écran phare. Skeletons au chargement, état vide soigné.
 *
 * Les actions sont présentes mais non fonctionnelles (les mutations négociation
 * arrivent en 004). Pas d'auth gating pour l'instant (withOrg en 003/004).
 */
export const Route = createFileRoute("/app/conversations/$id")({
  component: ConversationDetailPage,
})

const AVATAR_STYLES: Record<StatusKind, string> = {
  nego: "bg-[#F3E9DF] text-[#8A5A2B]",
  livrer: "bg-[#E6EBF6] text-[#3457A6]",
  paye: "bg-primary-tint text-primary-deep",
  rupture: "bg-danger-tint text-danger",
  nouveau: "bg-[#EFEDE6] text-ink-faint",
}

function ConversationDetailPage() {
  const { id } = Route.useParams()
  const conversationId = id as Id<"conversations">

  const deal = useQuery(api.conversations.dealForConversation, {
    conversationId,
  })
  const messages = useQuery(api.conversations.messagesByConversation, {
    conversationId,
  })

  if (deal === undefined) return <DetailSkeleton />
  if (deal === null) return <DetailNotFound />

  const displayName = prettyPhone(deal.clientPhone)
  const kind = statusKind(deal.status)

  return (
    <div className="flex min-h-full flex-col">
      <DetailHeader
        displayName={displayName}
        status={deal.status}
        updatedAt={deal.updatedAt}
      />

      <DealPanel
        productName={deal.product?.name ?? null}
        productCode={deal.product?.code ?? null}
        askingPrice={deal.product?.price ?? null}
        floorPrice={deal.product?.minPrice ?? null}
        currentOffer={deal.currentOffer}
        kind={kind}
      />

      <MessageThread messages={messages} displayName={displayName} kind={kind} />

      <ActionBar kind={kind} />
    </div>
  )
}

// ── En-tête ──────────────────────────────────────────────────────────────────

function DetailHeader({
  displayName,
  status,
  updatedAt,
}: {
  displayName: string
  status: ConversationStatus
  updatedAt: number
}) {
  const kind = statusKind(status)
  const phone = isPhoneIdentity(displayName)
  const monogram = initials(displayName)

  return (
    <header className="sticky top-0 z-10 flex items-center gap-3 border-b border-line bg-page/95 px-3 py-2.5 backdrop-blur">
      <Link
        to="/app"
        aria-label="Retour"
        className="grid h-10 w-10 shrink-0 place-items-center rounded-full text-ink-muted transition active:bg-surface"
      >
        <ArrowLeft className="h-5 w-5" />
      </Link>

      <span
        className={`grid h-11 w-11 shrink-0 place-items-center rounded-full font-display text-[14px] font-bold ${AVATAR_STYLES[kind]}`}
      >
        {phone || !monogram ? <User className="h-5 w-5" /> : monogram}
      </span>

      <div className="min-w-0 flex-1">
        <p className="truncate font-display text-[16px] font-bold leading-tight">
          {displayName}
        </p>
        <p className="text-[12px] text-ink-faint">
          Dernière activité {timeAgo(updatedAt)}
        </p>
      </div>

      <StatusChip kind={kind} />
    </header>
  )
}

// ── Panneau affaire (négociation) ────────────────────────────────────────────

function DealPanel({
  productName,
  productCode,
  askingPrice,
  floorPrice,
  currentOffer,
  kind,
}: {
  productName: string | null
  productCode: string | null
  askingPrice: number | null
  floorPrice: number | null
  currentOffer: number | null
  kind: StatusKind
}) {
  // Marge si on accepte l'offre courante : offre - prix plancher.
  const margin =
    currentOffer !== null && floorPrice !== null
      ? currentOffer - floorPrice
      : null

  return (
    <section className="px-3 pt-3">
      <div className="rounded-2xl border border-line bg-surface p-4 shadow-card">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate font-display text-[15px] font-bold">
              {productName ?? "Produit retiré"}
            </p>
            {productCode && (
              <p className="mt-0.5 font-mono text-[12px] text-ink-faint">
                {productCode}
              </p>
            )}
          </div>
          <StatusChip kind={kind} />
        </div>

        {/* Offre actuelle, mise en avant (argent first-class). */}
        <div className="mt-3 flex items-end gap-2">
          <span className="font-display text-[30px] font-extrabold leading-none tracking-tight tabular">
            {currentOffer !== null ? formatAmount(currentOffer) : "—"}
          </span>
          <span className="mb-0.5 font-display text-[15px] font-semibold text-ink-muted">
            FCFA
          </span>
          <span className="mb-1 ml-1 text-[12px] text-ink-faint">
            offre actuelle
          </span>
        </div>

        {/* Détail négociation : demandé · plancher · marge. */}
        <div className="mt-3 grid grid-cols-3 gap-2 border-t border-line pt-3">
          <DealStat label="Prix demandé" value={askingPrice} />
          <DealStat label="Prix plancher" value={floorPrice} />
          <DealStat label="Marge" value={margin} highlight />
        </div>
      </div>
    </section>
  )
}

function DealStat({
  label,
  value,
  highlight = false,
}: {
  label: string
  value: number | null
  highlight?: boolean
}) {
  const negative = highlight && value !== null && value < 0
  return (
    <div>
      <p className="text-[11.5px] text-ink-faint">{label}</p>
      <p
        className={`mt-0.5 font-display text-[15px] font-bold tabular ${
          negative ? "text-danger" : highlight ? "text-primary-deep" : "text-ink"
        }`}
      >
        {value !== null ? formatAmount(value) : "—"}
      </p>
    </div>
  )
}

// ── Fil de messages ──────────────────────────────────────────────────────────

type MessageDoc = {
  _id: string
  _creationTime: number
  content: string
  isFromClient: boolean
}

function MessageThread({
  messages,
  displayName,
  kind,
}: {
  messages: MessageDoc[] | undefined
  displayName: string
  kind: StatusKind
}) {
  if (messages === undefined) return <ThreadSkeleton />
  if (messages.length === 0) return <ThreadEmpty displayName={displayName} />

  return (
    <section className="flex-1 space-y-2 px-4 pb-4 pt-4">
      {messages.map((m) => (
        <MessageBubble key={m._id} message={m} kind={kind} />
      ))}
    </section>
  )
}

function MessageBubble({
  message,
  kind,
}: {
  message: MessageDoc
  kind: StatusKind
}) {
  const fromClient = message.isFromClient

  return (
    <div className={fromClient ? "flex justify-start" : "flex justify-end"}>
      <div className="flex max-w-[82%] flex-col">
        <div
          className={
            fromClient
              ? "rounded-2xl rounded-tl-md border border-line bg-surface px-3.5 py-2.5 text-[14.5px] leading-snug text-ink shadow-soft"
              : "rounded-2xl rounded-tr-md bg-primary-tint px-3.5 py-2.5 text-[14.5px] leading-snug text-ink"
          }
        >
          {message.content}
        </div>
        <div
          className={`mt-1 flex items-center gap-1 px-1 text-[11px] text-ink-faint ${
            fromClient ? "justify-start" : "justify-end"
          }`}
        >
          {!fromClient && (
            <Bot className="h-3 w-3 text-primary-deep" aria-label="Bot" />
          )}
          <span className="tabular">{timeAgo(message._creationTime)}</span>
        </div>
      </div>
    </div>
  )
}

function ThreadEmpty({ displayName }: { displayName: string }) {
  return (
    <section className="flex-1 px-5 pb-6 pt-8">
      <div className="rounded-2xl border border-line bg-surface p-8 text-center shadow-soft">
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-line">
          <MessageSquareOff className="h-6 w-6 text-ink-faint" />
        </div>
        <p className="mt-3 font-display text-[16px] font-bold">
          Aucun message
        </p>
        <p className="mt-1 text-[13.5px] text-ink-muted">
          La conversation avec {displayName} ne contient encore aucun message.
        </p>
      </div>
    </section>
  )
}

// ── Barre d'actions ──────────────────────────────────────────────────────────

type ActionDef = {
  key: string
  label: string
  icon: LucideIcon
  className: string
}

/**
 * Actions négociation, contextuelles au statut. Présentes mais non
 * fonctionnelles pour l'instant (les mutations arrivent en 004). On garde une
 * action primaire claire (vert) + des secondaires neutres, cibles >= 48px.
 */
function actionsForKind(kind: StatusKind): ActionDef[] {
  const accept: ActionDef = {
    key: "accept",
    label: "Accepter l'offre",
    icon: Check,
    className: "bg-primary text-primary-foreground active:bg-primary-deep",
  }
  const counter: ActionDef = {
    key: "counter",
    label: "Contre-offre",
    icon: HandCoins,
    className:
      "border border-line bg-surface text-ink active:bg-page shadow-soft",
  }
  const markPaid: ActionDef = {
    key: "paid",
    label: "Marquer payé",
    icon: PackageCheck,
    className: "bg-primary text-primary-foreground active:bg-primary-deep",
  }
  const toDeliver: ActionDef = {
    key: "deliver",
    label: "À livrer",
    icon: Truck,
    className:
      "border border-livrer/25 bg-livrer-tint text-livrer active:opacity-90",
  }

  switch (kind) {
    case "nego":
      return [accept, counter]
    case "livrer":
      return [markPaid, toDeliver]
    case "paye":
      return [toDeliver]
    default:
      return [counter, markPaid]
  }
}

function ActionBar({ kind }: { kind: StatusKind }) {
  const actions = actionsForKind(kind)
  return (
    <div className="sticky bottom-0 border-t border-line bg-surface px-3 py-3 shadow-tab">
      <div
        className={`grid gap-2 ${
          actions.length > 1 ? "grid-cols-2" : "grid-cols-1"
        }`}
      >
        {actions.map((a) => {
          const Icon = a.icon
          return (
            <button
              key={a.key}
              type="button"
              className={`inline-flex h-12 items-center justify-center gap-2 rounded-2xl text-[14.5px] font-semibold transition ${a.className}`}
            >
              <Icon className="h-[18px] w-[18px]" />
              {a.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── États de chargement / erreur ─────────────────────────────────────────────

function DetailSkeleton() {
  return (
    <div className="flex min-h-full flex-col">
      <header className="flex items-center gap-3 border-b border-line px-3 py-2.5">
        <Skeleton className="h-10 w-10 rounded-full" />
        <Skeleton className="h-11 w-11 rounded-full" />
        <div className="flex-1 space-y-1.5">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-20" />
        </div>
        <Skeleton className="h-6 w-20 rounded-full" />
      </header>

      <section className="px-3 pt-3">
        <div className="rounded-2xl border border-line bg-surface p-4 shadow-card">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="mt-3 h-8 w-44" />
          <div className="mt-3 grid grid-cols-3 gap-2 border-t border-line pt-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="space-y-1.5">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-12" />
              </div>
            ))}
          </div>
        </div>
      </section>

      <ThreadSkeleton />
    </div>
  )
}

function ThreadSkeleton() {
  return (
    <section className="flex-1 space-y-3 px-4 pb-4 pt-4">
      <div className="flex justify-start">
        <Skeleton className="h-12 w-3/5 rounded-2xl rounded-tl-md" />
      </div>
      <div className="flex justify-end">
        <Skeleton className="h-12 w-2/3 rounded-2xl rounded-tr-md" />
      </div>
      <div className="flex justify-start">
        <Skeleton className="h-10 w-1/2 rounded-2xl rounded-tl-md" />
      </div>
    </section>
  )
}

function DetailNotFound() {
  return (
    <div className="flex min-h-full flex-col">
      <header className="flex items-center gap-3 border-b border-line px-3 py-2.5">
        <Link
          to="/app"
          aria-label="Retour"
          className="grid h-10 w-10 place-items-center rounded-full text-ink-muted active:bg-surface"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <p className="font-display text-[16px] font-bold">Conversation</p>
      </header>

      <div className="flex flex-1 items-center justify-center px-5 py-16 text-center">
        <div>
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-line">
            <MessageSquareOff className="h-6 w-6 text-ink-faint" />
          </div>
          <p className="mt-3 font-display text-[17px] font-bold">
            Conversation introuvable
          </p>
          <p className="mt-1.5 text-[14px] text-ink-muted">
            Elle a peut-être été clôturée ou supprimée.
          </p>
          <Link
            to="/app"
            className="mt-4 inline-flex h-11 items-center justify-center gap-2 rounded-full border border-line bg-surface px-5 text-[14px] font-semibold text-ink shadow-soft active:bg-page"
          >
            <ArrowLeft className="h-4 w-4" />
            Retour aux conversations
          </Link>
        </div>
      </div>
    </div>
  )
}

/** Formate un numéro brut en identité lisible (+225 07 88 41 20). */
function prettyPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "")
  if (digits.startsWith("225") && digits.length >= 12) {
    const local = digits.slice(3)
    const groups = local.match(/.{1,2}/g) ?? [local]
    return `+225 ${groups.join(" ")}`
  }
  return `+${digits}`
}
