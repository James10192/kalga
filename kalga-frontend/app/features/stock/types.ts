/**
 * Types inférés — feature `stock`
 */

import type { z } from 'zod'

import type {
  criticalStockProductSchema,
  lowStockThresholdInputSchema,
  restockInputSchema,
  stockAdjustInputSchema,
  stockCritiqueSchema,
  stockEventSchema,
  stockOverviewItemSchema,
  STOCK_MODE_VALUES,
  STOCK_OVERVIEW_STATUS,
  stockStatusSchema,
  waitlistEntrySchema,
} from './schemas'

export type StockStatus = z.infer<typeof stockStatusSchema>
export type StockEvent = z.infer<typeof stockEventSchema>
export type WaitlistEntry = z.infer<typeof waitlistEntrySchema>
export type StockAdjustInput = z.infer<typeof stockAdjustInputSchema>
export type LowStockThresholdInput = z.infer<typeof lowStockThresholdInputSchema>

export type StockOverviewItem = z.infer<typeof stockOverviewItemSchema>
export type RestockInput = z.infer<typeof restockInputSchema>
export type StockOverviewStatus = (typeof STOCK_OVERVIEW_STATUS)[number]
export type StockMode = (typeof STOCK_MODE_VALUES)[number]

export type CriticalStockProduct = z.infer<typeof criticalStockProductSchema>
export type StockCritique = z.infer<typeof stockCritiqueSchema>
