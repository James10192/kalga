import { createFileRoute } from "@tanstack/react-router"
import { useQuery } from "convex/react"
import { ScrollText } from "lucide-react"
import { api } from "../../../../convex/_generated/api"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

/**
 * Admin — journal d'audit (adminAuditLogs). Tableau dense, read-only via
 * api.admin.auditLogs. État vide soigné, parsing tolérant du JSON `details`.
 */
export const Route = createFileRoute("/app/admin/audit")({
  component: AdminAuditPage,
})

type Log = {
  id: string
  adminUserId: string
  action: string
  targetType: string | null
  targetId: string | null
  details: string | null
  ipAddress: string | null
  createdAt: number
}

const ACTION_LABEL: Record<string, string> = {
  issue_activation_code: "Émission code d'activation",
}

function AdminAuditPage() {
  const logs = useQuery(api.admin.auditLogs, { limit: 100 }) as
    | Log[]
    | undefined

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-[22px] font-bold tracking-tight">
          Journal d'audit
        </h1>
        <p className="mt-0.5 text-[13.5px] text-ink-muted">
          Actions sensibles de l'équipe KALGA, les plus récentes en tête.
        </p>
      </div>

      <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-soft">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Quand</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Cible</TableHead>
              <TableHead>Détail</TableHead>
              <TableHead>Acteur</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {logs === undefined ? (
              <SkeletonRows />
            ) : logs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="py-0">
                  <EmptyState />
                </TableCell>
              </TableRow>
            ) : (
              logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="text-ink-muted">
                    {formatDateTime(log.createdAt)}
                  </TableCell>
                  <TableCell>
                    <span className="font-medium text-ink">
                      {ACTION_LABEL[log.action] ?? log.action}
                    </span>
                  </TableCell>
                  <TableCell className="text-ink-muted">
                    {log.targetType ? (
                      <span>
                        {log.targetType}
                        {log.targetId ? (
                          <span className="text-ink-faint">
                            {" "}
                            #{log.targetId.slice(-6)}
                          </span>
                        ) : null}
                      </span>
                    ) : (
                      "·"
                    )}
                  </TableCell>
                  <TableCell className="max-w-[320px]">
                    <DetailCell details={log.details} />
                  </TableCell>
                  <TableCell>
                    <code className="rounded-md bg-secondary px-1.5 py-0.5 font-mono text-[12px] text-ink-muted">
                      {log.adminUserId}
                    </code>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

/** Affiche un résumé lisible du JSON `details` (tolérant aux formats). */
function DetailCell({ details }: { details: string | null }) {
  if (!details) return <span className="text-ink-faint">·</span>
  try {
    const obj = JSON.parse(details) as Record<string, unknown>
    const parts: string[] = []
    if (typeof obj.code === "string") parts.push(`code ${obj.code}`)
    if (typeof obj.merchantName === "string") parts.push(String(obj.merchantName))
    if (parts.length > 0) {
      return <span className="truncate text-ink-muted">{parts.join(" · ")}</span>
    }
  } catch {
    /* details non-JSON : on affiche brut tronqué */
  }
  return (
    <span className="block truncate font-mono text-[12px] text-ink-muted">
      {details}
    </span>
  )
}

function SkeletonRows() {
  return (
    <>
      {[0, 1, 2, 3].map((i) => (
        <TableRow key={i}>
          {[0, 1, 2, 3, 4].map((j) => (
            <TableCell key={j}>
              <div className="h-4 w-full max-w-[140px] animate-pulse rounded bg-line" />
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
        <ScrollText className="h-6 w-6 text-ink-muted" />
      </div>
      <p className="mt-3 font-display text-[16px] font-bold">
        Aucune action enregistrée
      </p>
      <p className="mt-1 text-[13.5px] text-ink-muted">
        Les actions sensibles (émission de code, etc.) apparaîtront ici.
      </p>
    </div>
  )
}

function formatDateTime(epochMs: number): string {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(epochMs))
}
