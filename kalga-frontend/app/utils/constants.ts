/**
 * Constantes globales KALGA — Source unique de vérité pour les valeurs magiques.
 * Référence : ARCHITECTURE_FRONTEND.md section 5.4 (Single Source of Truth)
 *
 * Règle : aucune valeur littérale ne doit apparaître dans le code applicatif.
 * Tout ce qui pourrait être hardcodé vit ici, exporté nommément.
 */

// =============================================================================
// PRODUITS
// =============================================================================

/** Code produit format strict : #K001, #K042, #K999 */
export const PRODUCT_CODE_REGEX = /^#K\d{3}$/

export const PRODUCT_NAME_MIN_LEN = 2
export const PRODUCT_NAME_MAX_LEN = 100
export const PRODUCT_DESCRIPTION_MAX_LEN = 1000
export const VARIANT_NAME_MAX_LEN = 80

// =============================================================================
// PRIX (F CFA — valeurs entières uniquement)
// =============================================================================

export const PRICE_MIN = 100
export const PRICE_MAX = 10_000_000

// =============================================================================
// TÉLÉPHONE (numéros internationaux WhatsApp)
// =============================================================================

export const PHONE_MIN_LEN = 10
export const PHONE_MAX_LEN = 15
/** Numéro nettoyé = chiffres uniquement, indicatif inclus */
export const PHONE_DIGITS_ONLY_REGEX = /^\d{10,15}$/

// =============================================================================
// MARCHAND
// =============================================================================

export const MERCHANT_NAME_MIN_LEN = 2
export const MERCHANT_NAME_MAX_LEN = 100
export const BUSINESS_NAME_MAX_LEN = 200
export const ADDRESS_MAX_LEN = 500
export const BOT_CATCHPHRASE_MAX_LEN = 200
export const AWAY_MESSAGE_MAX_LEN = 500

// Limites géographiques (standard ISO 6709)
export const LATITUDE_MIN = -90
export const LATITUDE_MAX = 90
export const LONGITUDE_MIN = -180
export const LONGITUDE_MAX = 180

// =============================================================================
// MESSAGES (conversation client)
// =============================================================================

export const MESSAGE_MAX_LEN = 2000

// =============================================================================
// VITRINE / COMMANDE CLIENT
// =============================================================================

export const CLIENT_NAME_MIN_LEN = 2
export const CLIENT_NAME_MAX_LEN = 100
export const ORDER_MESSAGE_MAX_LEN = 500

// =============================================================================
// AUTH
// =============================================================================

export const PASSWORD_MIN_LEN = 8
export const PASSWORD_MAX_LEN = 128
export const EMAIL_MAX_LEN = 320 // RFC 5321
export const JWT_MIN_LEN = 32

// =============================================================================
// CODE D'ACTIVATION
// =============================================================================

/** Code d'activation : 6 chiffres */
export const ACTIVATION_CODE_REGEX = /^\d{6}$/
export const ACTIVATION_CODE_LEN = 6

// =============================================================================
// RÔLES (enum-as-const)
// =============================================================================

export const ROLE = {
  ADMIN: 'admin',
  MERCHANT: 'merchant',
} as const

export type Role = (typeof ROLE)[keyof typeof ROLE]
export const ROLE_VALUES = Object.values(ROLE) as Role[]

// =============================================================================
// STATUTS CONVERSATION
// Aligné sur kalga-api/app/models/enums.py:ConversationStatus
// =============================================================================

export const CONVERSATION_STATUS = {
  ACTIVE: 'active',
  NEGOTIATING: 'negotiating',
  AGREED: 'agreed',
  PENDING_DELIVERY: 'pending_delivery',
  PENDING_PICKUP: 'pending_pickup',
  COMPLETED: 'completed',
  ABANDONED: 'abandoned',
  ENDED: 'ended',
  EXPIRED: 'expired',
} as const

export type ConversationStatusValue = (typeof CONVERSATION_STATUS)[keyof typeof CONVERSATION_STATUS]
export const CONVERSATION_STATUS_VALUES = Object.values(
  CONVERSATION_STATUS,
) as ConversationStatusValue[]

// =============================================================================
// PLANS D'ABONNEMENT
// =============================================================================

export const SUBSCRIPTION_PLAN = {
  TRIAL: 'trial',
  STARTER: 'starter',
  PRO: 'pro',
  ENTERPRISE: 'enterprise',
} as const

export type SubscriptionPlanValue = (typeof SUBSCRIPTION_PLAN)[keyof typeof SUBSCRIPTION_PLAN]
export const SUBSCRIPTION_PLAN_VALUES = Object.values(
  SUBSCRIPTION_PLAN,
) as SubscriptionPlanValue[]

// =============================================================================
// STATUTS ABONNEMENT
// =============================================================================

export const SUBSCRIPTION_STATUS = {
  ACTIVE: 'active',
  TRIAL: 'trial',
  EXPIRED: 'expired',
  CANCELLED: 'cancelled',
  SUSPENDED: 'suspended',
} as const

export type SubscriptionStatusValue =
  (typeof SUBSCRIPTION_STATUS)[keyof typeof SUBSCRIPTION_STATUS]
export const SUBSCRIPTION_STATUS_VALUES = Object.values(
  SUBSCRIPTION_STATUS,
) as SubscriptionStatusValue[]

// =============================================================================
// STATUTS ACTIVATION
// =============================================================================

export const ACTIVATION_STATUS = {
  PENDING: 'pending',
  SENT: 'sent',
  USED: 'used',
  EXPIRED: 'expired',
} as const

export type ActivationStatusValue = (typeof ACTIVATION_STATUS)[keyof typeof ACTIVATION_STATUS]
export const ACTIVATION_STATUS_VALUES = Object.values(
  ACTIVATION_STATUS,
) as ActivationStatusValue[]

// =============================================================================
// STATUTS STOCK
// =============================================================================

export const STOCK_STATUS = {
  NORMAL: 'normal',
  LOW: 'low',
  OUT_OF_STOCK: 'out_of_stock',
} as const

export type StockStatusValue = (typeof STOCK_STATUS)[keyof typeof STOCK_STATUS]
export const STOCK_STATUS_VALUES = Object.values(STOCK_STATUS) as StockStatusValue[]

// =============================================================================
// TYPES DE LIVRAISON
// =============================================================================

export const DELIVERY_TYPE = {
  DELIVERY: 'delivery',
  PICKUP: 'pickup',
} as const

export type DeliveryType = (typeof DELIVERY_TYPE)[keyof typeof DELIVERY_TYPE]

// =============================================================================
// PAGINATION
// =============================================================================

export const PAGINATION_DEFAULT_PER_PAGE = 20
export const PAGINATION_MAX_PER_PAGE = 100
export const PAGINATION_DEFAULT_PAGE = 1

// =============================================================================
// CACHE TanStack Query (en millisecondes)
// =============================================================================

export const CACHE_STALE_TIME_SHORT = 30_000 // 30s
export const CACHE_STALE_TIME_DEFAULT = 60_000 // 1 min
export const CACHE_STALE_TIME_LONG = 300_000 // 5 min

// =============================================================================
// LIMITES TRIAL (aligné sur kalga-api/app/core/config.py)
// =============================================================================

export const TRIAL_DURATION_DAYS = 14
export const TRIAL_MESSAGES_LIMIT = 500
export const TRIAL_PRODUCTS_LIMIT = 10

// =============================================================================
// EXPIRATION CONVERSATION
// =============================================================================

export const CONVERSATION_EXPIRY_DAYS = 7

// =============================================================================
// STOCK
// =============================================================================

export const STOCK_ADJUST_REASON_MAX_LEN = 200

// =============================================================================
// FORMATS STANDARDS
// =============================================================================

/** Format de date ISO 8601 simple : YYYY-MM-DD (sans heure ni timezone) */
export const ISO_DATE_REGEX = /^\d{4}-\d{2}-\d{2}$/
