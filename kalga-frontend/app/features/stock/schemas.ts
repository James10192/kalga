/**
 * Schémas Zod — feature `stock`
 *
 * Gestion stock + waitlist + journal d'événements stock.
 */

import { z } from 'zod'

import {
  PHONE_DIGITS_ONLY_REGEX,
  PRICE_MAX,
  PRICE_MIN,
  STOCK_ADJUST_REASON_MAX_LEN,
  STOCK_STATUS_VALUES,
} from '@/utils/constants'

// =============================================================================
// STATUT STOCK
// =============================================================================

export const stockStatusSchema = z.object({
  product_id: z.number().int().positive(),
  quantity: z.number().int().min(0),
  low_stock_threshold: z.number().int().min(0).nullable(),
  status: z.enum(STOCK_STATUS_VALUES as unknown as readonly [string, ...string[]]),
  is_out_of_stock: z.boolean(),
  is_low: z.boolean(),
})

// =============================================================================
// JOURNAL ÉVÉNEMENT STOCK
// =============================================================================

export const stockEventSchema = z.object({
  id: z.number().int().positive(),
  merchant_id: z.number().int().positive(),
  product_id: z.number().int().positive(),
  event_type: z.enum(['sale', 'restock', 'adjustment', 'out_of_stock']),
  quantity_delta: z.number().int(),
  quantity_after: z.number().int().min(0),
  conversation_id: z.number().int().positive().nullable(),
  created_at: z.string().datetime(),
})

// =============================================================================
// WAITLIST
// =============================================================================

export const waitlistEntrySchema = z.object({
  id: z.number().int().positive(),
  merchant_id: z.number().int().positive(),
  product_id: z.number().int().positive(),
  client_phone: z.string().regex(PHONE_DIGITS_ONLY_REGEX),
  client_name: z.string().nullable(),
  conversation_id: z.number().int().positive().nullable(),
  offered_price: z.number().int().min(PRICE_MIN).max(PRICE_MAX).nullable(),
  position: z.number().int().positive(),
  created_at: z.string().datetime(),
})

// =============================================================================
// INPUTS — édition stock
// =============================================================================

/** Ajuster manuellement la quantité de stock (marchand) */
export const stockAdjustInputSchema = z.object({
  product_id: z.number().int().positive(),
  quantity_delta: z.number().int(), // peut être négatif
  reason: z.string().max(STOCK_ADJUST_REASON_MAX_LEN).optional(),
})

/** Configurer le seuil d'alerte stock bas */
export const lowStockThresholdInputSchema = z.object({
  product_id: z.number().int().positive(),
  low_stock_threshold: z.number().int().min(0),
})

// =============================================================================
// OVERVIEW (table de gestion du stock)
// Réf : GET /stock/merchant/{id}/overview + dashboard/static/app.js
// =============================================================================

/** Statuts renvoyés par l'overview (distincts de STOCK_STATUS_VALUES). */
export const STOCK_OVERVIEW_STATUS = ['out_of_stock', 'low_stock', 'ok', 'unlimited'] as const

/** Mode appliqué en rupture (cf. select de la table). */
export const STOCK_MODE_VALUES = ['waitlist', 'alert_only', 'suspend', 'preorder'] as const

export const stockOverviewItemSchema = z.object({
  id: z.number().int().positive(),
  name: z.string(),
  code: z.string(),
  stock_quantity: z.number().int(),
  low_stock_threshold: z.number().int().nullable(),
  stock_status: z.enum(STOCK_OVERVIEW_STATUS),
  waitlist_count: z.number().int().min(0),
})

/** Réapprovisionnement (PUT /stock/product/{code}/restock). */
export const restockInputSchema = z.object({
  quantity_to_add: z.number().int().positive(),
  merchant_id: z.number().int().positive(),
  broadcast_waitlist: z.boolean(),
  store_name: z.string(),
})

// =============================================================================
// STOCK CRITIQUE (widget Aperçu)
// Réf : GET /stock/merchant/{id}/critique + dashboard/static/app.js
//       (loadStockCritiqueWidget). Les champs produit en trop sont ignorés.
// =============================================================================

export const criticalStockProductSchema = z.object({
  id: z.number().int().positive(),
  name: z.string(),
  code: z.string(),
  stock_status: z.enum(['out_of_stock', 'low_stock']),
  waitlist_count: z.number().int().min(0),
})

export const stockCritiqueSchema = z.object({
  out_of_stock_count: z.number().int().min(0),
  low_stock_count: z.number().int().min(0),
  total_waitlist: z.number().int().min(0),
  lost_revenue_estimate: z.number().int().min(0),
  critical_products: z.array(criticalStockProductSchema),
})
