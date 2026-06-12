import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "convex/react"
import { MessagesSquare } from "lucide-react"
import { api } from "../../../convex/_generated/api"
import {
  ConversationRow,
  ConversationRowSkeleton,
  buildMoneyLine,
  prettyPhone,
  type ConversationRowData,
} from "@/components/dashboard"

/**
 * Liste COMPLÈTE des conversations du marchand (DIRECTION.md, phase Nav).
 *
 * Route /app/conversations. L'accueil ne montre qu'un aperçu (~3-4 récentes) ;
 * cette page liste tout le fil, scrollable, chaque rangée câblée en Link vers
 * le détail /app/conversations/$id.
 *
 * Réutilise la query existante api.dashboard.feedForMerchant (grain grossier,
 * pas de N+1). Câblé au marchand démo (slug `demo`) — se branchera derrière
 * withOrg avec l'OTP live, sans casser ce contrat de lecture. Skeletons au
 * chargement, état vide soigné. Onglet Conversations actif (via le layout /app).
 */
export const Route = createFileRoute("/app/conversations/")({
  component: ConversationsListPage,
})

const DEMO_SLUG = "demo"

type FeedItem = {
  conversationId: string
  clientPhone: string
  status: ConversationRowData["status"]
  currentOffer: number | null
  updatedAt: number
  productName: string | null
  productPrice: number | null
  amount: number | null
  lastMessage: { content: string; isFromClient: boolean } | null
}

function ConversationsListPage() {
  const merchant = useQuery(api.merchants.getBySlug, { slug: DEMO_SLUG })

  if (merchant === undefined) return <ListLoading />
  if (merchant === null) return <ListMerchantMissing />

  return <ListContent merchantId={merchant._id} />
}

function ListContent({ merchantId }: { merchantId: string }) {
  // Limite haute : on veut le fil complet (pas un aperçu comme l'accueil).
  const feed = useQuery(api.dashboard.feedForMerchant, {
    merchantId: merchantId as never,
    limit: 200,
  })

  return (
    <>
      <Header count={feed?.length} />
      <ConversationList feed={feed} />
    </>
  )
}

function ConversationList({ feed }: { feed: FeedItem[] | undefined }) {
  if (feed === undefined) {
    return (
      <ul className="space-y-1 px-3 pb-4">
        {[0, 1, 2, 3, 4, 5, 6].map((i) => (
          <li key={i}>
            <ConversationRowSkeleton />
          </li>
        ))}
      </ul>
    )
  }

  if (feed.length === 0) return <ConversationsEmpty />

  return (
    <ul className="space-y-1 px-3 pb-4">
      {feed.map((c) => {
        const data: ConversationRowData = {
          conversationId: c.conversationId,
          displayName: prettyPhone(c.clientPhone),
          status: c.status,
          updatedAt: c.updatedAt,
          preview: c.lastMessage?.content ?? null,
          fromBot: c.lastMessage ? !c.lastMessage.isFromClient : false,
          // Non-lu : dernier message du client (en attente de traitement).
          unread: c.lastMessage ? c.lastMessage.isFromClient : false,
          moneyLine: buildMoneyLine({
            status: c.status,
            currentOffer: c.currentOffer,
            productName: c.productName,
            productPrice: c.productPrice,
            amount: c.amount,
          }),
        }
        return (
          <li key={c.conversationId}>
            <Link
              to="/app/conversations/$id"
              params={{ id: c.conversationId }}
              className="block"
            >
              <ConversationRow data={data} />
            </Link>
          </li>
        )
      })}
    </ul>
  )
}

function Header({ count }: { count: number | undefined }) {
  return (
    <header className="px-5 pb-2 pt-4">
      <p className="text-[13px] text-ink-muted">
        {count === undefined
          ? "Tout votre fil WhatsApp"
          : count === 0
            ? "Tout votre fil WhatsApp"
            : count === 1
              ? "1 conversation"
              : `${count} conversations`}
      </p>
      <h1 className="font-display text-[22px] font-bold leading-tight tracking-tight">
        Conversations
      </h1>
    </header>
  )
}

/** État vide soigné pour la liste de conversations. */
function ConversationsEmpty() {
  return (
    <div className="px-5 pb-8 pt-4">
      <div className="rounded-2xl border border-line bg-surface p-8 text-center shadow-soft">
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-primary-tint">
          <MessagesSquare className="h-6 w-6 text-primary-deep" />
        </div>
        <p className="mt-3 font-display text-[16px] font-bold">
          Aucune conversation
        </p>
        <p className="mt-1 text-[13.5px] text-ink-muted">
          Dès qu'un client écrit sur votre WhatsApp, la conversation apparaît ici.
        </p>
      </div>
    </div>
  )
}

/** Skeleton plein écran (marchand pas encore résolu). */
function ListLoading() {
  return (
    <>
      <header className="px-5 pb-2 pt-4">
        <div className="h-3.5 w-32 animate-pulse rounded bg-line" />
        <div className="mt-1.5 h-6 w-44 animate-pulse rounded bg-line" />
      </header>
      <ul className="space-y-1 px-3 pb-4 pt-2">
        {[0, 1, 2, 3, 4, 5, 6].map((i) => (
          <li key={i}>
            <ConversationRowSkeleton />
          </li>
        ))}
      </ul>
    </>
  )
}

/** Le marchand démo est introuvable (seed pas lancé). */
function ListMerchantMissing() {
  return (
    <div className="px-5 py-16 text-center">
      <p className="font-display text-[18px] font-bold">Marchand introuvable</p>
      <p className="mt-2 text-[14px] text-ink-muted">
        Le marchand de démonstration n'existe pas encore. Lancez le seed Convex :
      </p>
      <code className="mt-3 inline-block rounded-md bg-line px-2 py-1 font-mono text-[13px] text-ink">
        npx convex run seed:run
      </code>
    </div>
  )
}
