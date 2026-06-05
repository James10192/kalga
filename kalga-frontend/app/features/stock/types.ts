/**
 * Types inférés — feature `stock`
 */

import type { z } from 'zod'

import type {
  lowStockThresholdInputSchema,
  stockAdjustInputSchema,
  stockEventSchema,
  stockStatusSchema,
  waitlistEntrySchema,
} from './schemas'

export type StockStatus = z.infer<typeof stockStatusSchema>
export type StockEvent = z.infer<typeof stockEventSchema>
export type WaitlistEntry = z.infer<typeof waitlistEntrySchema>
export type StockAdjustInput = z.infer<typeof stockAdjustInputSchema>
export type LowStockThresholdInput = z.infer<typeof lowStockThresholdInputSchema>
