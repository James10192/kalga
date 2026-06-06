/**
 * Helpers de formatage purs (pas d'état, pas d'I/O).
 * Référence : ARCHITECTURE_FRONTEND.md section 4 (utils/) + 5.4 (SSOT)
 *
 * Toutes ces fonctions doivent être :
 *  - 100% testées (Vitest)
 *  - Sans dépendance à Vue, Nuxt ou un composable
 *  - Locale-aware via Intl.* quand pertinent
 */

const F_CFA_SUFFIX = ' F'

/**
 * Formate un prix en F CFA avec séparateur d'espace insécable.
 *
 * @example formatPriceFCFA(25000)       // "25 000 F"
 * @example formatPriceFCFA(1500000)     // "1 500 000 F"
 * @example formatPriceFCFA(0)           // "0 F"
 */
export function formatPriceFCFA(amount: number): string {
  if (!Number.isFinite(amount)) {
    return `0${F_CFA_SUFFIX}`
  }
  // Intl.NumberFormat 'fr-FR' utilise l'espace insécable comme séparateur de milliers.
  const formatted = new Intl.NumberFormat('fr-FR', {
    useGrouping: true,
    maximumFractionDigits: 0,
  }).format(Math.trunc(amount))
  return `${formatted}${F_CFA_SUFFIX}`
}

/**
 * Formate une date ISO 8601 en chaîne lisible selon la locale.
 *
 * @example formatDate('2026-06-04T10:00:00Z', 'fr-FR') // "4 juin 2026"
 * @example formatDate('2026-06-04T10:00:00Z', 'en-US') // "Jun 4, 2026"
 */
export function formatDate(iso: string, locale: string = 'fr-FR'): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date)
}

/**
 * Formate une date ISO 8601 avec heure et minutes.
 *
 * @example formatDateTime('2026-06-04T10:30:00Z', 'fr-FR') // "4 juin 2026, 10:30"
 */
export function formatDateTime(iso: string, locale: string = 'fr-FR'): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

/**
 * Affiche un numéro de téléphone international avec indicatif et groupes lisibles.
 *
 * Heuristique simple : sépare l'indicatif présumé (3 premiers chiffres) puis
 * groupe le reste par 2 ou 4.
 *
 * @example formatPhone('2250161407534') // "+225 01 61 40 75 34"
 * @example formatPhone('33612345678')   // "+33 6 12 34 56 78"
 */
export function formatPhone(phone: string): string {
  if (!phone) {
    return ''
  }
  const digits = phone.replace(/\D/g, '')
  if (digits.length < 8) {
    return phone
  }
  // 3 premiers = indicatif (heuristique 225 / 33 / 234 etc.)
  // Pour 33 (France) on prend 2 chiffres, sinon 3
  const ccLen = digits.startsWith('33') || digits.startsWith('34') ? 2 : 3
  const cc = digits.slice(0, ccLen)
  const rest = digits.slice(ccLen)
  // Si le reste a un nombre impair de chiffres (ex: France +33 6 12 34 56 78),
  // on isole le 1er chiffre puis on groupe le reste par paires. Sinon (ex: 225,
  // 10 chiffres pairs) on groupe directement par paires.
  const lead = rest.length % 2 === 1 ? rest.slice(0, 1) : ''
  const body = lead ? rest.slice(1) : rest
  const grouped = body.replace(/(\d{2})(?=\d)/g, '$1 ')
  return lead ? `+${cc} ${lead} ${grouped}` : `+${cc} ${grouped}`
}

/**
 * Tronque un texte à `maxLen` caractères en ajoutant un ellipsis.
 *
 * @example truncate('Hello world', 5) // "Hell…"
 */
export function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) {
    return text
  }
  return `${text.slice(0, Math.max(0, maxLen - 1))}…`
}

/**
 * Renvoie les initiales (2 max) à partir d'un nom complet ou d'un email.
 *
 * @example initialsFrom('Aïcha Diabaté')   // "AD"
 * @example initialsFrom('admin@kalga.com') // "AD"
 */
export function initialsFrom(name: string | null | undefined): string {
  if (!name) {
    return '?'
  }
  const cleaned = name.includes('@') ? name.split('@')[0]! : name
  const parts = cleaned
    .split(/[\s.\-_]+/)
    .filter(Boolean)
    .slice(0, 2)
  if (parts.length === 0) {
    return '?'
  }
  return parts
    .map((part) => part.charAt(0).toUpperCase())
    .join('')
}
