/**
 * Constantes de routes — KALGA Frontend.
 * Référence : ARCHITECTURE_FRONTEND.md section 5.4 (SSOT)
 *
 * Toute route utilisée dans des liens (`<NuxtLink :to="...">`,
 * `navigateTo(...)`, `router.push(...)`) doit venir d'ici.
 *
 * Avantage : si on renomme `/dashboard/produits` en `/dashboard/products`,
 * un seul fichier à modifier.
 */

export const ROUTES = {
  // === ZONE PUBLIQUE ===
  home: '/',
  login: '/login',
  /** Page d'attente après soumission du numéro WhatsApp (QR scan).
   *  Implémenté entièrement dans la PR onboarding. */
  connecting: '/connecting',
  storefront: {
    /** Vitrine d'un marchand : /boutique/:phone */
    merchant: (phone: string): string => `/boutique/${phone}`,
    /** Détail produit : /produit/:code */
    product: (code: string): string => `/produit/${code}`,
    /** Formulaire de commande : /commander/:code */
    order: (code: string): string => `/commander/${code}`,
  },

  // === ZONE MARCHAND ===
  dashboard: {
    home: '/dashboard',
    products: '/dashboard/produits',
    productNew: '/dashboard/produits/nouveau',
    productDetail: (id: number): string => `/dashboard/produits/${id}`,
    conversations: '/dashboard/conversations',
    conversationDetail: (id: number): string => `/dashboard/conversations/${id}`,
    stats: '/dashboard/stats',
    settings: '/dashboard/parametres',
  },

  // === ZONE ADMIN ===
  admin: {
    /** Login admin — bypass middleware (page publique). */
    login: '/admin/login',
    home: '/admin',
    merchants: '/admin/marchands',
    merchantDetail: (id: number): string => `/admin/marchands/${id}`,
    activations: '/admin/activations',
    auditLogs: '/admin/audit-logs',
  },

  // === ERREURS ===
  errors: {
    accountSuspended: '/account-suspended',
    forbidden: '/forbidden',
  },
} as const
