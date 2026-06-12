import { createFileRoute } from "@tanstack/react-router"
import { useQuery } from "convex/react"
import { Store, Users } from "lucide-react"
import { api } from "../../../../convex/_generated/api"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  SubscriptionBadge,
  WhatsAppBadge,
} from "@/components/admin/badges"
import { prettyPhone } from "@/components/dashboard"

/**
 * Admin — liste des marchands (tous). Tableau dense : nom, slug, téléphone,
 * statut abonnement, statut WhatsApp. Données via api.admin.listMerchants
 * (read-only, gardée admin). Skeletons + état vide soigné.
 */
export const Route = createFileRoute("/app/admin/")({
  component: AdminMerchantsPage,
})

type MerchantRow = {
  id: string
  name: string
  slug: string
  phone: string
  businessName: string | null
  subscription: {
    plan: string
    status: string
    trialEndsAt: number | null
    endDate: number | null
    updatedAt: number
  } | null
  whatsapp: "connected" | "disconnected" | "unknown"
  createdAt: number
}

function AdminMerchantsPage() {
  const merchants = useQuery(api.admin.listMerchants, {}) as
    | MerchantRow[]
    | undefined

  const activeSubs =
    merchants?.filter((m) => m.subscription?.status === "active").length ?? 0

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-[22px] font-bold tracking-tight">
            Marchands
          </h1>
          <p className="mt-0.5 text-[13.5px] text-ink-muted">
            Tous les comptes marchands de la plateforme KALGA.
          </p>
        </div>
        {merchants !== undefined && (
          <div className="flex items-center gap-2">
            <Metric
              icon={<Users className="h-4 w-4" />}
              value={String(merchants.length)}
              label="marchands"
            />
            <Metric
              icon={<Store className="h-4 w-4" />}
              value={String(activeSubs)}
              label="abonnements actifs"
            />
          </div>
        )}
      </div>

      <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-soft">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Marchand</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead>WhatsApp (bot)</TableHead>
              <TableHead>Abonnement</TableHead>
              <TableHead>Statut WhatsApp</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {merchants === undefined ? (
              <SkeletonRows />
            ) : merchants.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="py-0">
                  <EmptyState />
                </TableCell>
              </TableRow>
            ) : (
              merchants.map((m) => (
                <TableRow key={m.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-primary/20 bg-primary-tint font-display text-[13px] font-bold text-primary-deep">
                        {monogram(m.name)}
                      </span>
                      <div className="min-w-0">
                        <p className="truncate font-medium text-ink">
                          {m.name}
                        </p>
                        {m.businessName && (
                          <p className="truncate text-[12px] text-ink-muted">
                            {m.businessName}
                          </p>
                        )}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <code className="rounded-md bg-secondary px-1.5 py-0.5 font-mono text-[12px] text-ink-muted">
                      {m.slug}
                    </code>
                  </TableCell>
                  <TableCell className="tabular text-ink-muted">
                    {prettyPhone(m.phone)}
                  </TableCell>
                  <TableCell>
                    <SubscriptionBadge subscription={m.subscription} />
                  </TableCell>
                  <TableCell>
                    <WhatsAppBadge status={m.whatsapp} />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Note placeholder statut WhatsApp (non suivi côté Convex). */}
      <p className="text-[12.5px] text-ink-faint">
        Le statut WhatsApp temps réel provient de la passerelle Baileys. Il
        n'est pas encore relayé vers Convex : affichage placeholder.
      </p>
    </div>
  )
}

function Metric({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode
  value: string
  label: string
}) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2 shadow-soft">
      <span className="grid h-7 w-7 place-items-center rounded-lg bg-secondary text-ink-muted">
        {icon}
      </span>
      <div className="leading-tight">
        <p className="font-display text-[16px] font-bold tabular">{value}</p>
        <p className="text-[11.5px] text-ink-muted">{label}</p>
      </div>
    </div>
  )
}

function SkeletonRows() {
  return (
    <>
      {[0, 1, 2, 3, 4].map((i) => (
        <TableRow key={i}>
          {[0, 1, 2, 3, 4].map((j) => (
            <TableCell key={j}>
              <div className="h-4 w-full max-w-[160px] animate-pulse rounded bg-line" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  )
}

function EmptyState() {
  return (
    <div className="px-5 py-12 text-center">
      <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-secondary">
        <Store className="h-6 w-6 text-ink-muted" />
      </div>
      <p className="mt-3 font-display text-[16px] font-bold">Aucun marchand</p>
      <p className="mt-1 text-[13.5px] text-ink-muted">
        Aucun compte marchand n'existe encore. Lancez le seed Convex avec{" "}
        <code className="rounded bg-secondary px-1 py-0.5 font-mono text-[12px]">
          npx convex run seed:run
        </code>
        .
      </p>
    </div>
  )
}

function monogram(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return "?"
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}
