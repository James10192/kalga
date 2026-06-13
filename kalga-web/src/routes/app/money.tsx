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
 * Câblé aux données Convex LIVE scopées au marchand courant via withOrg
 * (api.dashboard.salesRegistry — aucun `merchantId` venant du client).
 *
 * Responsive : mobile = totaux empilés puis registre ; >= lg = totaux en
 * colonne collante à droite + registre à gauche. Skeletons + état vide soignés.
 */
export const Route = createFileRoute("/app/money")({
  component: MoneyPage,
})

type Sale = {
  conversationId: string
  clientPhone: string
  amount: number
  productName: string | null
  soldAt: number
}

type Registry = {
  todayTotal: number
  weekTotal: number
  todayCount: number
  weekCount: number
  sales: Sale[]
}

function MoneyPage() {
  const registry = useQuery(api.dashboard.salesRegistry, { limit: 60 })

  return (
    <div className="mx-auto w-full max-w-6xl">
      <Header />

      {/* Desktop : registre (gauche) + totaux collants (droite). Mobile : empilé. */}
      <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_300px] lg:gap-6 lg:px-5">
        <div className="lg:order-1 lg:min-w-0">
          {/* Totaux : en flux mobile, masqués desktop (colonne dédiée). */}
          <div className="lg:hidden">
            <Totals registry={registry} />
          </div>

          <section className="px-5 pb-2 pt-5 lg:px-0">
            <h2 className="font-display text-[17px] font-bold">Ventes récentes</h2>
          </section>

          <SalesList sales={registry?.sales} />
        </div>

        <aside className="hidden lg:order-2 lg:block">
          <div className="sticky top-4 pt-5">
            <Totals registry={registry} stacked />
          </div>
        </aside>
      </div>
    </div>
  )
}

/** Totaux héros (Aujourd'hui + Cette semaine), grille en ligne ou empilée. */
function Totals({
  registry,
  stacked = false,
}: {
  registry: Registry | undefined
  stacked?: boolean
}) {
  const layout = stacked ? "" : "px-5 pt-2"
  if (registry === undefined) {
    return (
      <section className={layout}>
        <TotalsSkeleton stacked={stacked} />
      </section>
    )
  }
  return (
    <section className={layout}>
      <div className={stacked ? "space-y-2.5" : "grid grid-cols-2 gap-2.5"}>
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
    </section>
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

function TotalsSkeleton({ stacked = false }: { stacked?: boolean }) {
  return (
    <div className={stacked ? "space-y-2.5" : "grid grid-cols-2 gap-2.5"}>
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
      <ul className="space-y-1 px-3 pb-4 lg:px-0">
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
    <div className="px-3 pb-6 lg:px-0">
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
      <h1 className="font-display text-[22px] font-bold leading-tight tracking-tight lg:text-[26px]">
        Argent
      </h1>
    </header>
  )
}

/** État vide soigné : aucune vente encore enregistrée. */
function SalesEmpty() {
  return (
    <div className="px-5 pb-8 pt-4 lg:px-0">
      <div className="mx-auto max-w-md rounded-2xl border border-line bg-surface p-8 text-center shadow-soft">
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
