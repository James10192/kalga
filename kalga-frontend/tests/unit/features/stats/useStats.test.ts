/**
 * Tests Vitest — features/stats/composables/useStats.ts
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@tanstack/vue-query', async () => (await import('../../helpers/tanstack')).tanstackMock)

import { fetchMock, resetTanstack, stubNuxtGlobals } from '../../helpers/tanstack'
import {
  statsKeys,
  useMerchantStats,
  useStatsTimeseries,
} from '../../../../app/features/stats/composables/useStats'

beforeEach(() => {
  resetTanstack()
  stubNuxtGlobals()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('statsKeys', () => {
  it('génère les clés de cache', () => {
    expect(statsKeys.all).toEqual(['stats'])
    expect(statsKeys.merchant(3)).toEqual(['stats', 'merchant', 3])
    expect(statsKeys.timeseries(3, 'sales', '2026-01-01', '2026-02-01')).toEqual([
      'stats',
      'timeseries',
      3,
      'sales',
      '2026-01-01',
      '2026-02-01',
    ])
  })
})

describe('useMerchantStats', () => {
  it('câble la clé et la queryFn appelle l’API', async () => {
    const opts = useMerchantStats(3) as Record<string, any>
    expect(opts.queryKey.value).toEqual(['stats', 'merchant', 3])
    expect(opts.enabled.value).toBe(true)
    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()
  })

  it('désactive la query si merchantId<=0', () => {
    expect((useMerchantStats(0) as Record<string, any>).enabled.value).toBe(false)
  })
})

describe('useStatsTimeseries', () => {
  it('enabled vrai seulement si merchantId>0 et bornes non vides', async () => {
    const ok = useStatsTimeseries(3, 'sales', '2026-01-01', '2026-02-01') as Record<string, any>
    expect(ok.enabled.value).toBe(true)
    await ok.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()

    const ko = useStatsTimeseries(3, 'sales', '', '2026-02-01') as Record<string, any>
    expect(ko.enabled.value).toBe(false)
  })
})
