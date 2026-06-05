/**
 * Types inférés — feature `stats`
 */

import type { z } from 'zod'

import type {
  analyticsEventSchema,
  merchantStatsSchema,
  statsDateRangeSchema,
  statsTimeseriesPointSchema,
  statsTimeseriesSchema,
} from './schemas'

export type MerchantStats = z.infer<typeof merchantStatsSchema>
export type StatsTimeseriesPoint = z.infer<typeof statsTimeseriesPointSchema>
export type StatsTimeseries = z.infer<typeof statsTimeseriesSchema>
export type AnalyticsEvent = z.infer<typeof analyticsEventSchema>
export type StatsDateRange = z.infer<typeof statsDateRangeSchema>
