/**
 * Tests Vitest — features/merchants/composables/useMerchants.ts
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@tanstack/vue-query', async () => (await import('../../helpers/tanstack')).tanstackMock)

import {
  fetchMock,
  invalidateQueries,
  resetTanstack,
  stubNuxtGlobals,
} from '../../helpers/tanstack'
import {
  merchantsKeys,
  useMerchant,
  useMerchantsList,
  useUpdateAwayMode,
  useUpdateBotPersona,
  useUpdateMerchantLocation,
  useUpdateMerchantProfile,
} from '../../../../app/features/merchants/composables/useMerchants'

beforeEach(() => {
  resetTanstack()
  stubNuxtGlobals()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('merchantsKeys', () => {
  it('génère les clés de cache', () => {
    expect(merchantsKeys.all).toEqual(['merchants'])
    expect(merchantsKeys.detail(7)).toEqual(['merchants', 'detail', 7])
    expect(merchantsKeys.list(2, 'aïcha')).toEqual(['merchants', 'list', 2, 'aïcha'])
  })
})

describe('queries merchants', () => {
  it('useMerchant : clé détail + désactive si id<=0', async () => {
    const opts = useMerchant(7) as Record<string, any>
    expect(opts.queryKey.value).toEqual(['merchants', 'detail', 7])
    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()
    expect((useMerchant(0) as Record<string, any>).enabled.value).toBe(false)
  })

  it('useMerchantsList : clé liste + queryFn', async () => {
    const opts = useMerchantsList(2, 'aïcha') as Record<string, any>
    expect(opts.queryKey.value).toEqual(['merchants', 'list', 2, 'aïcha'])
    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()
  })
})

describe('mutations merchants — invalident détail + liste au succès', () => {
  const updates = [
    useUpdateMerchantProfile,
    useUpdateMerchantLocation,
    useUpdateBotPersona,
    useUpdateAwayMode,
  ]

  it.each(updates)('%o : mutationFn + onSuccess invalident le marchand', async (useUpdate) => {
    const opts = useUpdate() as Record<string, any>
    await opts.mutationFn({ id: 7, data: {} })
    expect(fetchMock).toHaveBeenCalledOnce()

    opts.onSuccess({ id: 7 })
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['merchants', 'detail', 7] })
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['merchants', 'list'] })
  })
})
