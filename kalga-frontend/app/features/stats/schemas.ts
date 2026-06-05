/**
 * Schémas Zod — feature `stats`
 *
 * KPIs marchand + événements analytics.
 */

import { z } from 'zod'

import { ISO_DATE_REGEX } from '@/utils/constants'

// =============================================================================
// KPI MARCHAND
// =============================================================================

export const merchantStatsSchema = z.object({
  merchant_id: z.number().int().positive(),
  products: z.number().int().min(0),
  conversations: z.number().int().min(0),
  sales: z.number().int().min(0),
  revenue: z.number().int().min(0),
  messages_used: z.number().int().min(0),
  conversion_rate: z.number().min(0).max(1),
})

// =============================================================================
// SÉRIE TEMPORELLE (pour graphes Chart.js)
// =============================================================================

/** Un point dans une série temporelle */
export const statsTimeseriesPointSchema = z.object({
  date: z.string().regex(ISO_DATE_REGEX, 'Format date attendu : YYYY-MM-DD'),
  value: z.number(),
})



/** Série complète (label + points) */
export const statsTimeseriesSchema = z.object({
  label: z.string(),
  points: z.array(statsTimeseriesPointSchema),
})

// =============================================================================
// ÉVÉNEMENT ANALYTICS (audit-like)
// =============================================================================

export const analyticsEventSchema = z.object({
  id: z.number().int().positive(),
  merchant_id: z.number().int().positive(),
  event_type: z.string().min(1),
  product_id: z.number().int().positive().nullable(),
  conversation_id: z.number().int().positive().nullable(),
  client_phone: z.string().nullable(),
  data: z.record(z.unknown()).nullable(),
  created_at: z.string().datetime(),
})

// =============================================================================
// PARAMÈTRES DE REQUÊTE
// =============================================================================

/** Plage de dates pour requêter les stats */
export const statsDateRangeSchema = z
  .object({
    from: z.string().regex(ISO_DATE_REGEX),
    to: z.string().regex(ISO_DATE_REGEX),
  })
  .refine((data) => data.from <= data.to, {
    path: ['from'],
    message: 'La date de début doit être avant la date de fin',
  })
