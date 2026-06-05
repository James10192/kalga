/**
 * Helpers de calcul de plages de dates pour les graphes stats.
 * Référence : ARCHITECTURE_FRONTEND.md section 4 (utils/)
 *
 * Toutes les sorties sont au format YYYY-MM-DD (ISO_DATE_REGEX).
 */

import { ISO_DATE_REGEX } from '@/utils/constants'

/** Plages prédéfinies disponibles dans le sélecteur stats. */
export type RangePreset = '7d' | '30d' | '90d'

/** Toutes les valeurs de preset autorisées (utilisé pour les selects). */
export const RANGE_PRESET_VALUES: ReadonlyArray<RangePreset> = ['7d', '30d', '90d']

/** Combien de jours représente chaque preset. */
const PRESET_DAYS: Record<RangePreset, number> = {
  '7d': 7,
  '30d': 30,
  '90d': 90,
}

/** Convertit un Date en chaîne YYYY-MM-DD. */
export function toIsoDate(date: Date): string {
  const year = date.getUTCFullYear()
  const month = String(date.getUTCMonth() + 1).padStart(2, '0')
  const day = String(date.getUTCDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * Renvoie la plage `[from, to]` pour un preset donné.
 * `to` = aujourd'hui ; `from` = aujourd'hui - days.
 */
export function rangeFromPreset(preset: RangePreset): { from: string; to: string } {
  const today = new Date()
  const past = new Date(today.getTime() - PRESET_DAYS[preset] * 24 * 60 * 60 * 1000)
  return { from: toIsoDate(past), to: toIsoDate(today) }
}

/** Vérifie qu'une chaîne respecte le format YYYY-MM-DD. */
export function isValidIsoDate(value: string): boolean {
  return ISO_DATE_REGEX.test(value)
}
