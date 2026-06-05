/**
 * Configuration des items de navigation par zone.
 * Référence : ARCHITECTURE_FRONTEND.md section 5.4 (SSOT)
 *
 * Chaque item référence une clé i18n (jamais de texte hardcodé) et
 * un nom d'icône Lucide (lucide-vue-next).
 */

import { ROUTES } from './routes'

/** Un item de navigation (sidebar, menu) */
export interface NavItem {
  /** Clé i18n pour le label (ex: 'nav.products') */
  readonly i18nKey: string
  /** Chemin vers lequel naviguer */
  readonly to: string
  /** Nom de l'icône Lucide (ex: 'Package') */
  readonly icon: string
}

// =============================================================================
// NAVIGATION ZONE MARCHAND
// =============================================================================

export const MERCHANT_NAV: ReadonlyArray<NavItem> = [
  { i18nKey: 'nav.overview', to: ROUTES.dashboard.home, icon: 'LayoutDashboard' },
  { i18nKey: 'nav.products', to: ROUTES.dashboard.products, icon: 'Package' },
  { i18nKey: 'nav.conversations', to: ROUTES.dashboard.conversations, icon: 'MessageSquare' },
  { i18nKey: 'nav.stats', to: ROUTES.dashboard.stats, icon: 'BarChart3' },
  { i18nKey: 'nav.settings', to: ROUTES.dashboard.settings, icon: 'Settings' },
] as const

// =============================================================================
// NAVIGATION ZONE ADMIN
// =============================================================================

export const ADMIN_NAV: ReadonlyArray<NavItem> = [
  { i18nKey: 'nav.adminOverview', to: ROUTES.admin.home, icon: 'LayoutDashboard' },
  { i18nKey: 'nav.merchants', to: ROUTES.admin.merchants, icon: 'Users' },
  { i18nKey: 'nav.activations', to: ROUTES.admin.activations, icon: 'KeyRound' },
  { i18nKey: 'nav.auditLogs', to: ROUTES.admin.auditLogs, icon: 'ScrollText' },
] as const

// =============================================================================
// NAVIGATION ZONE PUBLIQUE (storefront — header)
// =============================================================================

export const PUBLIC_NAV: ReadonlyArray<NavItem> = [
  { i18nKey: 'nav.home', to: ROUTES.home, icon: 'Home' },
] as const
