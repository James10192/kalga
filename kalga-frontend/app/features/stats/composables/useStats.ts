/**
 * Composables TanStack Query — feature `stats`.
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 + 9.4
 */

import { useQuery } from '@tanstack/vue-query'
import type { MaybeRef } from 'vue'

import { CACHE_STALE_TIME_LONG } from '@/utils/constants'
import { statsApi } from '../api'
import type { TimeseriesMetric } from '../api'

export const statsKeys = {
  all: ['stats'] as const,
  merchant: (merchantId: number) => ['stats', 'merchant', merchantId] as const,
  timeseries: (merchantId: number, metric: TimeseriesMetric, from: string, to: string) =>
    ['stats', 'timeseries', merchantId, metric, from, to] as const,
}

export function useMerchantStats(merchantId: MaybeRef<number>) {
  return useQuery({
    queryKey: computed(() => statsKeys.merchant(unref(merchantId))),
    queryFn: () => statsApi.getMerchantStats(unref(merchantId)),
    staleTime: CACHE_STALE_TIME_LONG,
    enabled: computed(() => unref(merchantId) > 0),
  })
}

export function useStatsTimeseries(
  merchantId: MaybeRef<number>,
  metric: MaybeRef<TimeseriesMetric>,
  from: MaybeRef<string>,
  to: MaybeRef<string>,
) {
  return useQuery({
    queryKey: computed(() =>
      statsKeys.timeseries(unref(merchantId), unref(metric), unref(from), unref(to)),
    ),
    queryFn: () =>
      statsApi.getTimeseries({
        merchantId: unref(merchantId),
        metric: unref(metric),
        from: unref(from),
        to: unref(to),
      }),
    staleTime: CACHE_STALE_TIME_LONG,
    enabled: computed(() => unref(merchantId) > 0 && unref(from).length > 0 && unref(to).length > 0),
  })
}
