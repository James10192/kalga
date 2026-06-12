import { cn } from "@/lib/utils"

/**
 * Badges de statut pour la surface admin (tokens KALGA, tons mats).
 * Distincts du StatusChip dashboard (sémantique conversation) : ici on couvre
 * l'abonnement, le WhatsApp et les statuts de codes d'activation.
 */

type Dot = "ok" | "warn" | "info" | "danger" | "neutral"

const DOT_BG: Record<Dot, string> = {
  ok: "bg-primary",
  warn: "bg-nego",
  info: "bg-livrer",
  danger: "bg-danger",
  neutral: "bg-ink-faint",
}

const PILL: Record<Dot, string> = {
  ok: "text-primary-deep bg-primary-tint",
  warn: "text-nego bg-nego-tint",
  info: "text-livrer bg-livrer-tint",
  danger: "text-danger bg-danger-tint",
  neutral: "text-ink-muted bg-secondary",
}

function Pill({
  tone,
  children,
  withDot = true,
  className,
}: {
  tone: Dot
  children: React.ReactNode
  withDot?: boolean
  className?: string
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11.5px] font-medium",
        PILL[tone],
        className,
      )}
    >
      {withDot && (
        <span className={cn("h-1.5 w-1.5 rounded-full", DOT_BG[tone])} />
      )}
      {children}
    </span>
  )
}

// ── Abonnement ─────────────────────────────────────────────────────────────

const PLAN_LABEL: Record<string, string> = {
  trial: "Essai",
  starter: "Starter",
  pro: "Pro",
  enterprise: "Entreprise",
};

export function SubscriptionBadge({
  subscription,
}: {
  subscription:
    | { plan: string; status: string; trialEndsAt: number | null }
    | null;
}) {
  if (!subscription) {
    return (
      <Pill tone="neutral" withDot={false}>
        Aucun abonnement
      </Pill>
    )
  }
  const planLabel = PLAN_LABEL[subscription.plan] ?? subscription.plan
  const tone: Dot =
    subscription.status === "active"
      ? subscription.plan === "trial"
        ? "info"
        : "ok"
      : "danger"
  const statusLabel = subscription.status === "active" ? "actif" : "expiré"
  return (
    <Pill tone={tone}>
      {planLabel} · {statusLabel}
    </Pill>
  )
}

// ── WhatsApp ───────────────────────────────────────────────────────────────

export function WhatsAppBadge({
  status,
}: {
  status: "connected" | "disconnected" | "unknown"
}) {
  if (status === "connected") return <Pill tone="ok">Connecté</Pill>
  if (status === "disconnected") return <Pill tone="danger">Non connecté</Pill>
  // unknown : statut non suivi côté Convex pour l'instant (placeholder).
  return (
    <Pill tone="neutral" withDot={false}>
      Non suivi
    </Pill>
  )
}

// ── Code d'activation ──────────────────────────────────────────────────────

export function CodeStatusBadge({
  status,
}: {
  status: "pending" | "used" | "expired"
}) {
  if (status === "used") return <Pill tone="ok">Utilisé</Pill>
  if (status === "expired") return <Pill tone="neutral">Expiré</Pill>
  return <Pill tone="warn">En attente</Pill>
}
