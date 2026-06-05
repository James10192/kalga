/**
 * Types du domaine métier KALGA.
 * Référence : ARCHITECTURE_FRONTEND.md section 5.4 (SSOT pour types domaine)
 *
 * Source de vérité backend : kalga-api/app/models/schemas.py + enums.py
 * Mapping : tout champ qui existe côté Python doit avoir son équivalent ici.
 *
 * Les types sont **dérivés des schémas Zod** des features (via z.infer)
 * pour les inputs (création/édition). Ici on a les types du domaine pur,
 * tels que renvoyés par l'API.
 */

import type {
  Role,
  ConversationStatusValue,
  SubscriptionPlanValue,
  SubscriptionStatusValue,
  ActivationStatusValue,
  StockStatusValue,
  DeliveryType,
} from '@/utils/constants'
import type { EntityId, IsoDate, Uuid } from './api'

// =============================================================================
// MARCHAND
// =============================================================================

export interface Merchant {
  readonly id: EntityId
  readonly name: string
  readonly phone: string
  readonly business_name: string | null
  readonly address: string | null
  readonly city: string | null
  readonly commune: string | null
  readonly quarter: string | null
  readonly latitude: number | null
  readonly longitude: number | null
  readonly payment_info: string | null
  readonly payment_methods: string | null
  readonly bot_tone: string | null
  readonly bot_style: string | null
  readonly bot_catchphrase: string | null
  readonly away_mode_enabled: boolean
  readonly away_message: string | null
  readonly is_active: boolean
  readonly created_at: IsoDate
}

// =============================================================================
// PRODUIT
// =============================================================================

export interface Product {
  readonly id: EntityId
  readonly merchant_id: EntityId
  /** Format strict : #K001 */
  readonly code: string
  readonly name: string
  readonly description: string | null
  readonly price: number
  readonly min_price: number
  readonly image_path: string | null
  /** Variant group identifier (toutes les variantes d'un produit partagent ce group_id) */
  readonly group_id: Uuid | null
  readonly variant_name: string | null
  readonly stock_quantity: number | null
  readonly low_stock_threshold: number | null
  readonly out_of_stock_mode: 'waitlist' | 'suspend'
  readonly is_available: boolean
  readonly created_at: IsoDate
}

/** Variante d'un produit (même group_id, variant_name différent) */
export interface ProductVariant extends Product {
  readonly variant_name: string
  readonly group_id: Uuid
}

// =============================================================================
// CONVERSATION
// =============================================================================

export interface Conversation {
  readonly id: EntityId
  readonly merchant_id: EntityId
  readonly product_id: EntityId
  readonly client_phone: string
  readonly client_name: string | null
  readonly status: ConversationStatusValue
  readonly current_offer: number | null
  readonly selected_variant_id: EntityId | null
  readonly created_at: IsoDate
  readonly updated_at: IsoDate
}

// =============================================================================
// MESSAGE
// =============================================================================

export interface Message {
  readonly id: EntityId
  readonly conversation_id: EntityId
  readonly content: string
  readonly is_from_client: boolean
  readonly created_at: IsoDate
}

// =============================================================================
// USER (auth)
// =============================================================================

export interface User {
  readonly id: EntityId
  readonly email: string
  readonly role: Role
  readonly is_active: boolean
  readonly merchant_id: EntityId | null
  readonly last_login: IsoDate | null
  readonly created_at: IsoDate
}

// =============================================================================
// ABONNEMENT
// =============================================================================

export interface Subscription {
  readonly id: EntityId
  readonly merchant_id: EntityId
  readonly plan: SubscriptionPlanValue
  readonly status: SubscriptionStatusValue
  readonly messages_used: number
  readonly messages_limit: number
  readonly products_limit: number
  readonly trial_ends_at: IsoDate | null
  readonly start_date: IsoDate
  readonly end_date: IsoDate | null
  readonly created_at: IsoDate
}

// =============================================================================
// ACTIVATION
// =============================================================================

export interface Activation {
  readonly id: EntityId
  readonly merchant_id: EntityId
  readonly merchant_name: string | null
  readonly merchant_phone: string | null
  readonly code: string
  readonly status: ActivationStatusValue
  readonly admin_email: string | null
  readonly sent_at: IsoDate | null
  readonly used_at: IsoDate | null
  readonly expires_at: IsoDate | null
  readonly created_at: IsoDate
}

// =============================================================================
// STOCK
// =============================================================================

export interface StockStatus {
  readonly product_id: EntityId
  readonly quantity: number
  readonly low_stock_threshold: number | null
  readonly status: StockStatusValue
  readonly is_out_of_stock: boolean
  readonly is_low: boolean
}

export interface StockEvent {
  readonly id: EntityId
  readonly merchant_id: EntityId
  readonly product_id: EntityId
  readonly event_type: 'sale' | 'restock' | 'adjustment' | 'out_of_stock'
  readonly quantity_delta: number
  readonly quantity_after: number
  readonly conversation_id: EntityId | null
  readonly created_at: IsoDate
}

export interface WaitlistEntry {
  readonly id: EntityId
  readonly merchant_id: EntityId
  readonly product_id: EntityId
  readonly client_phone: string
  readonly client_name: string | null
  readonly conversation_id: EntityId | null
  readonly offered_price: number | null
  readonly position: number
  readonly created_at: IsoDate
}

// =============================================================================
// STATS
// =============================================================================

export interface MerchantStats {
  readonly merchant_id: EntityId
  readonly products: number
  readonly conversations: number
  readonly sales: number
  readonly revenue: number
  readonly messages_used: number
  readonly conversion_rate: number
}

export interface AnalyticsEvent {
  readonly id: EntityId
  readonly merchant_id: EntityId
  readonly event_type: string
  readonly product_id: EntityId | null
  readonly conversation_id: EntityId | null
  readonly client_phone: string | null
  readonly data: Readonly<Record<string, unknown>> | null
  readonly created_at: IsoDate
}

// =============================================================================
// KNOWLEDGE BASE (apprentissage IA)
// =============================================================================

export interface KnowledgeBaseEntry {
  readonly id: EntityId
  readonly merchant_id: EntityId
  readonly question: string
  readonly answer: string
  readonly source: 'manual' | 'client_correction' | 'auto_learned_deal' | 'auto_flagged'
  readonly created_at: IsoDate
}

// =============================================================================
// VITRINE PUBLIQUE (storefront)
// =============================================================================

/** Produit tel qu'affiché publiquement (SANS min_price !) */
export interface StorefrontProduct {
  readonly id: EntityId
  readonly code: string
  readonly name: string
  readonly description: string | null
  readonly price: number
  readonly image_url: string | null
  readonly variant_name: string | null
  readonly group_id: Uuid | null
  readonly in_stock: boolean
}

// =============================================================================
// AUDIT LOGS (admin)
// =============================================================================

export interface AuditLogEntry {
  readonly id: EntityId
  readonly admin_id: EntityId | null
  readonly admin_email: string | null
  readonly action: string
  readonly target_type: string | null
  readonly target_id: EntityId | null
  readonly details: Readonly<Record<string, unknown>> | null
  readonly ip_address: string | null
  readonly created_at: IsoDate
}

// =============================================================================
// EXPORTS UTILITAIRES
// =============================================================================

export type { DeliveryType }
