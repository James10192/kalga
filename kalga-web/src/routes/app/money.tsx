import { createFileRoute } from "@tanstack/react-router"
import { useQuery } from "convex/react"
import { Wallet, Check } from "lucide-react"
import { api } from "../../../convex/_generated/api"
import { Skeleton } from "@/components/ui/skeleton"
import {
  formatAmount,
  initials,
  isPhoneIdentity,
  prettyPhone,
  dayGroupLabel,
  timeOfDay,
} from "@/components/dashboard"

/**
 * Écran "Argent" du dashboard marchand — vue REGISTRE (pas analytics).
 *
 * Portage du contrat visuel (design/flagship-home.html + DIRECTION.md) :
 * gros "Aujourd'hui" + "Cette semaine" en Bricolage, puis la liste des ventes
 * récentes (conversations statut `completed` avec montant), groupées par jour.
 * Câblé aux données Convex LIVE du marchand démo (slug `demo`).
 *
 * Skeletons pendant le chargement, état vide soigné. Pas d'auth gating pour
 * l'instant (l'OTP live + withOrg viennent en 003/004).
 */
export const Route = createFileRoute("/app/money")({
  component: MoneyPage,
})

const DEMO_SLUG = "demo"

type Sale = {
  conversationId: string
  clientPhone: string
  amount: number
  productName: string | null
  soldAt: number
}

function MoneyPage() {
  const merchant = useQuery(api.merchants.getBySlug, { slug: DEMO_SLUG })

  if (merchant === undefined) return <MoneyLoading />
  if (merchant === null) return <MoneyMerchantMissing />

  return <MoneyContent merchantId={merchant._id} />
}

function MoneyContent({ merchantId }: { merchantId: string }) {
  const registry = useQuery(api.dashboard.salesRegistryForMerchant, {
    merchantId: merchantId as never,
    limit: 40,
  })

  return (
    <>
      <Header />

      {/* Totaux héros : Aujourd'hui + Cette semaine */}
      <section className="px-5 pt-2">
        {registry === undefined ? (
          <TotalsSkeleton />
        ) : (
          <div className="grid grid-cols-2 gap-2.5">
            <TotalCard
              label="Aujourd'hui"
              amount={registry.todayTotal}
              count={registry.todayCount}
              accent
            />
            <TotalCard
              label="Cette semaine"
              amount={registry.weekTotal}
              count={registry.weekCount}
            />
          </div>
        )}
      </section>

      {/* Liste des ventes récentes */}
      <section className="px-5 pb-2 pt-5">
        <h2 className="font-display text-[17px] font-bold">Ventes récentes</h2>
      </section>

      <SalesList sales={registry?.sales} />
    </>
  )
}

/** Carte de total (montant FCFA grand, Bricolage, tabular-nums). */
function TotalCard({
  label,
  amount,
  count,
  accent = false,
}: {
  label: string
  amount: number
  count: number
  accent?: boolean
}) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-card">
      <p className="text-[13px] font-medium text-ink-muted">{label}</p>
      <div className="mt-1.5 flex items-end gap-1.5">
        <span
          className={`font-display text-[30px] font-extrabold leading-none tracking-tight tabular ${
            accent ? "text-primary-deep" : "text-ink"
          }`}
        >
          {formatAmount(amount)}
        </span>
        <span className="mb-0.5 font-display text-[14px] font-semibold text-ink-muted">
          FCFA
        </span>
      </div>
      <p className="mt-2 text-[12px] text-ink-muted">
        {count} {count > 1 ? "ventes" : "vente"}
      </p>
    </div>
  )
}

function TotalsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-2.5">
      {[0, 1].map((i) => (
        <div
          key={i}
          className="rounded-2xl border border-line bg-surface p-4 shadow-card"
        >
          <Skeleton className="h-4 w-24" />
          <Skeleton className="mt-2.5 h-8 w-28" />
          <Skeleton className="mt-2.5 h-3 w-16" />
        </div>
      ))}
    </div>
  )
}

/** Liste des ventes groupée par jour (Aujourd'hui / Hier / date). */
function SalesList({ sales }: { sales: Sale[] | undefined }) {
  if (sales === undefined) {
    return (
      <ul className="space-y-1 px-3 pb-4">
        {[0, 1, 2, 3, 4].map((i) => (
          <li key={i}>
            <SaleRowSkeleton />
          </li>
        ))}
      </ul>
    )
  }

  if (sales.length === 0) return <SalesEmpty />

  // Groupage par libellé de jour, en conservant l'ordre (déjà trié récence).
  const groups: { label: string; items: Sale[] }[] = []
  for (const sale of sales) {
    const label = dayGroupLabel(sale.soldAt)
    const last = groups[groups.length - 1]
    if (last && last.label === label) last.items.push(sale)
    else groups.push({ label, items: [sale] })
  }

  return (
    <div className="px-3 pb-6">
      {groups.map((group) => (
        <div key={group.label} className="mb-2">
          <p className="px-2.5 pb-1 pt-3 text-[12px] font-medium text-ink-faint">
            {group.label}
          </p>
          <ul className="space-y-0.5">
            {group.items.map((sale) => (
              <li key={sale.conversationId}>
                <SaleRow sale={sale} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

/** Rangée d'une vente : avatar payé + client + produit + montant + heure. */
function SaleRow({ sale }: { sale: Sale }) {
  const display = prettyPhone(sale.clientPhone)
  const phone = isPhoneIdentity(display)
  const monogram = initials(display)

  return (
    <div className="flex items-center gap-3 rounded-2xl p-2.5">
      <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-primary-tint text-primary-deep">
        {phone || !monogram ? (
          <Check className="h-5 w-5" />
        ) : (
          <span className="font-display text-[14px] font-bold">{monogram}</span>
        )}
      </span>

      <span className="min-w-0 flex-1">
        <span className="flex items-center justify-between gap-2">
          <span className="truncate text-[15px] font-semibold">{display}</span>
          <span className="shrink-0 font-display text-[15px] font-bold text-primary-deep tabular">
            {formatAmount(sale.amount)}
          </span>
        </span>
        <span className="mt-0.5 flex items-center justify-between gap-2">
          <span className="truncate text-[13px] text-ink-muted">
            {sale.productName ?? "Vente"}
          </span>
          <span className="shrink-0 text-[12px] text-ink-faint tabular">
            {timeOfDay(sale.soldAt)}
          </span>
        </span>
      </span>
    </div>
  )
}

function SaleRowSkeleton() {
  return (
    <div className="flex items-center gap-3 p-2.5">
      <Skeleton className="h-11 w-11 shrink-0 rounded-full" />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-16" />
        </div>
        <div className="flex items-center justify-between">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-3 w-10" />
        </div>
      </div>
    </div>
  )
}

function Header() {
  return (
    <header className="px-5 pb-2 pt-4">
      <p className="text-[13px] text-ink-muted">Registre des ventes</p>
      <h1 className="font-display text-[22px] font-bold leading-tight tracking-tight">
        Argent
      </h1>
    </header>
  )
}

/** État vide soigné : aucune vente encore enregistrée. */
function SalesEmpty() {
  return (
    <div className="px-5 pb-8 pt-4">
      <div className="rounded-2xl border border-line bg-surface p-8 text-center shadow-soft">
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-primary-tint">
          <Wallet className="h-6 w-6 text-primary-deep" />
        </div>
        <p className="mt-3 font-display text-[16px] font-bold">
          Aucune vente pour l'instant
        </p>
        <p className="mt-1 text-[13.5px] text-ink-muted">
          Dès qu'une vente est finalisée, elle apparaît ici avec son montant.
        </p>
      </div>
    </div>
  )
}

/** Skeleton plein écran (marchand pas encore résolu). */
function MoneyLoading() {
  return (
    <>
      <header className="px-5 pb-2 pt-4">
        <Skeleton className="h-3.5 w-32" />
        <Skeleton className="mt-1.5 h-6 w-24" />
      </header>
      <section className="px-5 pt-2">
        <TotalsSkeleton />
      </section>
      <ul className="space-y-1 px-3 pb-4 pt-6">
        {[0, 1, 2, 3, 4].map((i) => (
          <li key={i}>
            <SaleRowSkeleton />
          </li>
        ))}
      </ul>
    </>
  )
}

/** Le marchand démo est introuvable (seed pas lancé). */
function MoneyMerchantMissing() {
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
