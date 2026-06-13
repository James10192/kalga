import { createFileRoute, Link } from "@tanstack/react-router"
import { useQuery } from "convex/react"
import { Search, ChevronRight, MessagesSquare } from "lucide-react"
import { api } from "../../../convex/_generated/api"
import {
  MoneyHero,
  MoneyHeroSkeleton,
  StatPill,
  StatPillsSkeleton,
  ConversationRow,
  ConversationRowSkeleton,
  buildMoneyLine,
  initials,
  prettyPhone,
  type ConversationRowData,
} from "@/components/dashboard"

/**
 * Accueil dashboard marchand — portage de design/flagship-home.html en React,
 * câblé aux données Convex LIVE scopées au marchand courant via withOrg
 * (aucun `merchantId` venant du client = anti-fuite cross-tenant).
 *
 * Résolution : merchants.currentMerchant (organisation active) -> feed + résumé
 * jour. Skeletons pendant le chargement, états vides soignés.
 *
 * Responsive : mobile = colonne unique inchangée ; >= lg = deux colonnes (fil de
 * conversations à gauche + panneau argent du jour à droite, collant).
 */
export const Route = createFileRoute("/app/")({
  component: HomePage,
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

type Summary = {
  todayRevenue: number
  todaySales: number
  deltaPct: number | null
  pills: { negotiating: number; toDeliver: number; outOfStock: number }
}

function HomePage() {
  const merchant = useQuery(api.merchants.currentMerchant, {})
  const summary = useQuery(api.dashboard.todaySummary, {})
  // Accueil = aperçu seulement. La liste complète est sur /app/conversations.
  const feed = useQuery(api.dashboard.feed, { limit: 6 })

  // Chargement initial : on n'a pas encore le marchand courant.
  if (merchant === undefined) return <HomeLoading />
  if (merchant === null) return <HomeMerchantMissing />

  const monogram = initials(merchant.name) || "BA"

  return (
    <div className="mx-auto w-full max-w-6xl">
      <Header merchantName={merchant.name} monogram={monogram} />

      {/* Desktop : deux colonnes (fil + argent). Mobile : empilé. */}
      <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_320px] lg:gap-6 lg:px-5">
        {/* Colonne principale : conversations */}
        <div className="lg:order-1 lg:min-w-0">
          {/* Argent + pills : visibles en flux mobile, masqués desktop (colonne dédiée) */}
          <div className="lg:hidden">
            <MoneyBlock summary={summary} />
            <PillsBlock summary={summary} />
          </div>

          <section className="px-5 pb-2 pt-5 lg:px-0">
            <div className="mb-1 flex items-center justify-between">
              <h2 className="font-display text-[17px] font-bold">Conversations</h2>
              <Link
                to="/app/conversations"
                className="inline-flex items-center gap-1 text-[13px] font-medium text-ink-muted"
              >
                Tout voir <ChevronRight className="h-4 w-4" />
              </Link>
            </div>
          </section>

          <ConversationList feed={feed} />
        </div>

        {/* Colonne argent (desktop seulement) */}
        <aside className="hidden lg:order-2 lg:block">
          <div className="sticky top-4 space-y-3 pt-5">
            <MoneyBlock summary={summary} bare />
            <PillsBlock summary={summary} bare />
          </div>
        </aside>
      </div>
    </div>
  )
}

/** Bloc héros argent du jour (réutilisé mobile + colonne desktop). */
function MoneyBlock({
  summary,
  bare = false,
}: {
  summary: Summary | undefined
  bare?: boolean
}) {
  return (
    <section className={bare ? "" : "px-5 pt-2"}>
      {summary === undefined ? (
        <MoneyHeroSkeleton />
      ) : (
        <MoneyHero
          amount={summary.todayRevenue}
          sales={summary.todaySales}
          deltaPct={summary.deltaPct}
        />
      )}
    </section>
  )
}

/** Bloc des pills statistiques (réutilisé mobile + colonne desktop). */
function PillsBlock({
  summary,
  bare = false,
}: {
  summary: Summary | undefined
  bare?: boolean
}) {
  return (
    <section className={bare ? "" : "px-5 pt-3"}>
      {summary === undefined ? (
        <StatPillsSkeleton />
      ) : (
        <div className="grid grid-cols-3 gap-2.5">
          <StatPill count={summary.pills.negotiating} label="en négo" dot="nego" />
          <StatPill count={summary.pills.toDeliver} label="à livrer" dot="livrer" />
          <StatPill count={summary.pills.outOfStock} label="en rupture" dot="danger" />
        </div>
      )}
    </section>
  )
}

function ConversationList({
  feed,
}: {
  feed: FeedItem[] | undefined
}) {
  if (feed === undefined) {
    return (
      <ul className="space-y-1 px-3 pb-4 lg:px-0">
        {[0, 1, 2, 3].map((i) => (
          <li key={i}>
            <ConversationRowSkeleton />
          </li>
        ))}
      </ul>
    )
  }

  if (feed.length === 0) return <ConversationsEmpty />

  return (
    <ul className="space-y-1 px-3 pb-4 lg:px-0">
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

function Header({
  merchantName,
  monogram,
}: {
  merchantName: string
  monogram: string
}) {
  return (
    <header className="flex items-center justify-between px-5 pb-2 pt-4">
      <div>
        <p className="text-[13px] text-ink-muted">Bonjour,</p>
        <h1 className="font-display text-[22px] font-bold leading-tight tracking-tight lg:text-[26px]">
          {merchantName}
        </h1>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          aria-label="Rechercher"
          className="grid h-11 w-11 place-items-center rounded-full border border-line bg-surface shadow-soft"
        >
          <Search className="h-5 w-5 text-ink-muted" />
        </button>
        <button
          type="button"
          aria-label="Profil boutique"
          className="grid h-11 w-11 place-items-center rounded-full border border-primary/20 bg-primary-tint"
        >
          <span className="font-display text-[15px] font-bold text-primary-deep">
            {monogram}
          </span>
        </button>
      </div>
    </header>
  )
}

/** État vide soigné pour la liste de conversations. */
function ConversationsEmpty() {
  return (
    <div className="px-5 pb-8 pt-4 lg:px-0">
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
function HomeLoading() {
  return (
    <div className="mx-auto w-full max-w-6xl">
      <header className="flex items-center justify-between px-5 pb-2 pt-4">
        <div className="space-y-2">
          <div className="h-3 w-16 animate-pulse rounded bg-line" />
          <div className="h-6 w-40 animate-pulse rounded bg-line" />
        </div>
        <div className="h-11 w-11 animate-pulse rounded-full bg-line" />
      </header>
      <section className="px-5 pt-2">
        <MoneyHeroSkeleton />
      </section>
      <section className="px-5 pt-3">
        <StatPillsSkeleton />
      </section>
      <ul className="space-y-1 px-3 pb-4 pt-6">
        {[0, 1, 2, 3].map((i) => (
          <li key={i}>
            <ConversationRowSkeleton />
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Le marchand courant est introuvable (pas encore d'organisation liée). */
function HomeMerchantMissing() {
  return (
    <div className="px-5 py-16 text-center">
      <p className="font-display text-[18px] font-bold">Boutique introuvable</p>
      <p className="mt-2 text-[14px] text-ink-muted">
        Votre compte n'est pas encore relié à une boutique. Terminez la création
        de votre compte pour accéder au tableau de bord.
      </p>
    </div>
  )
}
