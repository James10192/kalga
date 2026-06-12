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
  type ConversationRowData,
} from "@/components/dashboard"

/**
 * Accueil dashboard marchand — portage de design/flagship-home.html en React,
 * câblé aux données Convex LIVE du marchand démo (slug `demo`).
 *
 * Résolution : merchants.getBySlug({ slug: "demo" }) -> id -> feed + résumé jour.
 * Skeletons pendant le chargement, états vides soignés. Pas d'auth gating
 * pour l'instant (OTP live + withOrg en 003/004).
 */
export const Route = createFileRoute("/app/")({
  component: HomePage,
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

function HomePage() {
  const merchant = useQuery(api.merchants.getBySlug, { slug: DEMO_SLUG })

  // Chargement initial : on n'a pas encore le merchant.
  if (merchant === undefined) return <HomeLoading />
  if (merchant === null) return <HomeMerchantMissing />

  return <HomeContent merchantId={merchant._id} merchantName={merchant.name} />
}

function HomeContent({
  merchantId,
  merchantName,
}: {
  merchantId: string
  merchantName: string
}) {
  const summary = useQuery(api.dashboard.todaySummaryForMerchant, {
    merchantId: merchantId as never,
  })
  // Accueil = aperçu seulement. La liste complète est sur /app/conversations.
  const feed = useQuery(api.dashboard.feedForMerchant, {
    merchantId: merchantId as never,
    limit: 4,
  })

  const monogram = initials(merchantName) || "BA"

  return (
    <>
      <Header merchantName={merchantName} monogram={monogram} />

      {/* Héros argent du jour */}
      <section className="px-5 pt-2">
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

      {/* Pills statistiques */}
      <section className="px-5 pt-3">
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

      {/* Conversations */}
      <section className="px-5 pb-2 pt-5">
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
    </>
  )
}

function ConversationList({
  feed,
}: {
  feed: FeedItem[] | undefined
}) {
  if (feed === undefined) {
    return (
      <ul className="space-y-1 px-3 pb-4">
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
        <h1 className="font-display text-[22px] font-bold leading-tight tracking-tight">
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

/** Skeleton plein écran (merchant pas encore résolu). */
function HomeLoading() {
  return (
    <>
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
    </>
  )
}

/** Le marchand démo est introuvable (seed pas lancé). */
function HomeMerchantMissing() {
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
