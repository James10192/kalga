/**
 * Tests Vitest — features/stats/composables/useStats.ts
 * Stats par merchant_phone (+ merchantId pour le compte produits).
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
  it('génère les clés de cache (par téléphone)', () => {
    expect(statsKeys.all).toEqual(['stats'])
    expect(statsKeys.merchant('225544210112', 30)).toEqual([
      'stats',
      'merchant',
      '225544210112',
      30,
    ])
    expect(statsKeys.timeseries('225544210112', 'sales', '2026-01-01', '2026-02-01')).toEqual([
      'stats',
      'timeseries',
      '225544210112',
      'sales',
      '2026-01-01',
      '2026-02-01',
    ])
  })
})

describe('useMerchantStats', () => {
  it('câble la clé et la queryFn appelle l’API (summary + produits)', async () => {
    const opts = useMerchantStats('225544210112', 10, 30) as Record<string, any>
    expect(opts.queryKey.value).toEqual(['stats', 'merchant', '225544210112', 30])
    expect(opts.enabled.value).toBe(true)
    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledTimes(2) // /summary + /products
  })

  it('désactive la query si téléphone vide ou merchantId<=0', () => {
    expect((useMerchantStats('', 10, 30) as Record<string, any>).enabled.value).toBe(false)
    expect((useMerchantStats('225544210112', 0, 30) as Record<string, any>).enabled.value).toBe(
      false,
    )
  })
})

describe('useStatsTimeseries', () => {
  it('enabled vrai seulement si téléphone et bornes non vides', async () => {
    const ok = useStatsTimeseries(
      '225544210112',
      'sales',
      '2026-01-01',
      '2026-02-01',
    ) as Record<string, any>
    expect(ok.enabled.value).toBe(true)
    fetchMock.mockResolvedValueOnce({ data: [] }) // réponse /daily mappée
    await ok.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()

    const ko = useStatsTimeseries('225544210112', 'sales', '', '2026-02-01') as Record<string, any>
    expect(ko.enabled.value).toBe(false)
  })
})
