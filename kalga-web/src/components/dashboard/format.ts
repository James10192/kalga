/**
 * Helpers de formatage pour le dashboard marchand (français chaleureux, FCFA).
 * Pas d'em dash, espaces fines pour les milliers, statuts métier KALGA.
 */

import type { Doc } from "~/../convex/_generated/dataModel"

/** Montant FCFA avec séparateur de milliers par espace (45 000). */
export function formatAmount(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—"
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 })
    .format(value)
    .replace(/ /g, " ") // normalise l'espace fine insécable en espace simple
}

/** Initiales depuis un nom ou un numéro de téléphone. */
export function initials(name: string): string {
  const trimmed = name.trim()
  if (!trimmed) return "?"
  // Numéro de téléphone : pas d'initiales lettrées, on laisse l'icône gérer.
  if (/^[+\d][\d\s]*$/.test(trimmed)) return ""
  const parts = trimmed.split(/\s+/).filter(Boolean)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

/** Détecte si l'identité est un numéro brut (pas un nom de client connu). */
export function isPhoneIdentity(name: string): boolean {
  return /^[+\d][\d\s]*$/.test(name.trim())
}

/** Temps écoulé court et chaleureux : "2 min", "1 h", "hier", "3 j". */
export function timeAgo(epochMs: number, now: number = Date.now()): string {
  const diff = Math.max(0, now - epochMs)
  const min = Math.floor(diff / 60000)
  if (min < 1) return "à l'instant"
  if (min < 60) return `${min} min`
  const hours = Math.floor(min / 60)
  if (hours < 24) return `${hours} h`
  const days = Math.floor(hours / 24)
  if (days === 1) return "hier"
  return `${days} j`
}

/** Formate un numéro brut en identité lisible (+225 07 88 41 20). */
export function prettyPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "")
  if (digits.startsWith("225") && digits.length >= 12) {
    const local = digits.slice(3)
    const groups = local.match(/.{1,2}/g) ?? [local]
    return `+225 ${groups.join(" ")}`
  }
  return `+${digits}`
}

/** Heure courte d'une vente : "14:30". */
export function timeOfDay(epochMs: number): string {
  return new Intl.DateTimeFormat("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(epochMs))
}

/**
 * Libellé de groupe de jour pour le registre des ventes :
 * "Aujourd'hui", "Hier", sinon date longue ("lundi 9 juin").
 */
export function dayGroupLabel(epochMs: number, now: number = Date.now()): string {
  const startOf = (ms: number) => {
    const d = new Date(ms)
    return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  }
  const day = startOf(epochMs)
  const today = startOf(now)
  const oneDay = 24 * 60 * 60 * 1000
  if (day === today) return "Aujourd'hui"
  if (day === today - oneDay) return "Hier"
  return new Intl.DateTimeFormat("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date(epochMs))
}

export type ConversationStatus = Doc<"conversations">["status"]

/** Variante d'affichage pour la puce de statut (StatusChip / BottomTabBar). */
export type StatusKind = "nego" | "livrer" | "paye" | "rupture" | "nouveau"

/**
 * Mappe un statut Convex métier vers une variante d'affichage UI.
 * - active = nouveau (prospect / message entrant non traité)
 * - negotiating = négo
 * - agreed / pending_delivery / pending_pickup = à livrer
 * - completed = payé
 * - autres (abandoned/ended/expired) = nouveau (neutre)
 */
export function statusKind(status: ConversationStatus): StatusKind {
  switch (status) {
    case "negotiating":
      return "nego"
    case "agreed":
    case "pending_delivery":
    case "pending_pickup":
      return "livrer"
    case "completed":
      return "paye"
    case "active":
    default:
      return "nouveau"
  }
}
