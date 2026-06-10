/**
 * Client API — feature `stats`.
 * Référence : kalga-api/app/routers/stats.py (stats par merchant_phone).
 *
 * Le backend expose :
 *  - GET /stats/{phone}/summary?days=N            → KPIs agrégés
 *  - GET /stats/{phone}/daily?start_date&end_date → série journalière
 * Le compte de produits ne fait PAS partie des stats → on le lit depuis
 * /merchants/{id}/products (champ `total`).
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

interface RawSummary {
  merchant_id: number
  total_conversations: number
  total_messages: number
  total_sales: number
  total_revenue: number
  conversion_rate: number
}

interface RawDailyPoint {
  date: string
  conversations_count: number
  messages_count: number
  sales_count: number
  revenue: number
}

/** Champ de `RawDailyPoint` correspondant à chaque métrique de graphe. */
const METRIC_FIELD: Record<TimeseriesMetric, keyof Omit<RawDailyPoint, 'date'>> = {
  revenue: 'revenue',
  sales: 'sales_count',
  conversations: 'conversations_count',
  messages: 'messages_count',
}

export interface MerchantStatsParams {
  phone: string
  merchantId: number
  days: number
}

export interface TimeseriesParams {
  phone: string
  metric: TimeseriesMetric
  from: string
  to: string
}

export const statsApi = {
  /** KPIs agrégés du marchand (summary backend + compte produits). */
  getMerchantStats: async ({
    phone,
    merchantId,
    days,
  }: MerchantStatsParams): Promise<MerchantStats> => {
    const [summary, products] = await Promise.all([
      $fetch<RawSummary>(proxyUrl(`/stats/${phone}/summary`), { query: { days } }),
      $fetch<{ total: number }>(proxyUrl(`/merchants/${merchantId}/products`), {
        query: { page: 1 },
      }),
    ])
    return {
      merchant_id: summary.merchant_id,
      products: products.total,
      conversations: summary.total_conversations,
      sales: summary.total_sales,
      revenue: summary.total_revenue,
      messages_used: summary.total_messages,
      conversion_rate: summary.conversion_rate,
    }
  },

  /** Série temporelle journalière pour une métrique donnée. */
  getTimeseries: async ({
    phone,
    metric,
    from,
    to,
  }: TimeseriesParams): Promise<StatsTimeseries> => {
    const daily = await $fetch<{ data: RawDailyPoint[] }>(proxyUrl(`/stats/${phone}/daily`), {
      query: { start_date: from, end_date: to },
    })
    const field = METRIC_FIELD[metric]
    return {
      label: metric,
      points: daily.data.map((point) => ({ date: point.date, value: Number(point[field]) })),
    }
  },
}
