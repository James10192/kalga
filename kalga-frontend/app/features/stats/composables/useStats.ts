/**
 * Composables TanStack Query — feature `stats`.
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 + 9.4 ; stats par téléphone.
 */

import { useQuery } from '@tanstack/vue-query'
import type { MaybeRef } from 'vue'

import { CACHE_STALE_TIME_LONG } from '@/utils/constants'
import { statsApi } from '../api'
import type { TimeseriesMetric } from '../api'

export const statsKeys = {
  all: ['stats'] as const,
  merchant: (phone: string, days: number) => ['stats', 'merchant', phone, days] as const,
  timeseries: (phone: string, metric: TimeseriesMetric, from: string, to: string) =>
    ['stats', 'timeseries', phone, metric, from, to] as const,
}

export function useMerchantStats(
  phone: MaybeRef<string>,
  merchantId: MaybeRef<number>,
  days: MaybeRef<number>,
) {
  return useQuery({
    queryKey: computed(() => statsKeys.merchant(unref(phone), unref(days))),
    queryFn: () =>
      statsApi.getMerchantStats({
        phone: unref(phone),
        merchantId: unref(merchantId),
        days: unref(days),
      }),
    staleTime: CACHE_STALE_TIME_LONG,
    enabled: computed(() => unref(phone).length > 0 && unref(merchantId) > 0),
  })
}

export function useStatsTimeseries(
  phone: MaybeRef<string>,
  metric: MaybeRef<TimeseriesMetric>,
  from: MaybeRef<string>,
  to: MaybeRef<string>,
) {
  return useQuery({
    queryKey: computed(() =>
      statsKeys.timeseries(unref(phone), unref(metric), unref(from), unref(to)),
    ),
    queryFn: () =>
      statsApi.getTimeseries({
        phone: unref(phone),
        metric: unref(metric),
        from: unref(from),
        to: unref(to),
      }),
    staleTime: CACHE_STALE_TIME_LONG,
    enabled: computed(
      () => unref(phone).length > 0 && unref(from).length > 0 && unref(to).length > 0,
    ),
  })
}
