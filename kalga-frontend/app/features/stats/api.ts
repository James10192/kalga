/**
 * Client API — feature `stats`.
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 + 9.4
 *
 * Backend correspondant : kalga-api/app/routers/stats.py
 */

import type { MerchantStats, StatsTimeseries } from './types'

function proxyUrl(path: string): string {
  const config = useRuntimeConfig()
  const base = config.public.apiUrl.endsWith('/')
    ? config.public.apiUrl.slice(0, -1)
    : config.public.apiUrl
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

export type TimeseriesMetric = 'revenue' | 'sales' | 'conversations' | 'messages'

export interface TimeseriesParams {
  merchantId: number
  metric: TimeseriesMetric
  from: string
  to: string
}

export const statsApi = {
  /** KPIs agrégés du marchand. */
  getMerchantStats: (merchantId: number): Promise<MerchantStats> =>
    $fetch<MerchantStats>(proxyUrl(`/stats/${merchantId}`)),

  /** Série temporelle pour un métrique donné. */
  getTimeseries: ({
    merchantId,
    metric,
    from,
    to,
  }: TimeseriesParams): Promise<StatsTimeseries> =>
    $fetch<StatsTimeseries>(proxyUrl(`/stats/${merchantId}/timeseries`), {
      query: { metric, from, to },
    }),
}
