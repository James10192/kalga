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
 * Câblé aux données Convex LIVE scopées au marchand courant via withOrg
 * (api.dashboard.feed — aucun `merchantId` venant du client = anti-fuite
 * cross-tenant). Skeletons au chargement, état vide soigné.
 *
 * Responsive : mobile = liste plein écran ; >= lg = liste à gauche (rail) +
 * panneau d'invite à droite (« sélectionnez une conversation »), le détail
 * s'ouvrant sur /app/conversations/$id qui reprend le même rail.
 */
export const Route = createFileRoute("/app/conversations/")({
  component: ConversationsListPage,
})

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
  // Limite haute : on veut le fil complet (pas un aperçu comme l'accueil).
  const feed = useQuery(api.dashboard.feed, { limit: 200 })

  return (
    <div className="mx-auto w-full max-w-6xl lg:grid lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)] lg:gap-0">
      {/* Rail liste (gauche en desktop, plein écran en mobile). */}
      <div className="lg:border-r lg:border-line">
        <Header count={feed?.length} />
        <ConversationList feed={feed} />
      </div>

      {/* Panneau d'invite (desktop seulement). */}
      <aside className="hidden lg:flex lg:items-center lg:justify-center lg:px-8 lg:py-16">
        <div className="text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-primary-tint">
            <MessagesSquare className="h-7 w-7 text-primary-deep" />
          </div>
          <p className="mt-4 font-display text-[17px] font-bold">
            Sélectionnez une conversation
          </p>
          <p className="mt-1 text-[14px] text-ink-muted">
            Choisissez un client à gauche pour voir le fil et négocier.
          </p>
        </div>
      </aside>
    </div>
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
      <h1 className="font-display text-[22px] font-bold leading-tight tracking-tight lg:text-[26px]">
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
