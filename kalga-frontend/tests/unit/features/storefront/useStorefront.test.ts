/**
 * Tests Vitest — features/storefront/composables/useStorefront.ts
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@tanstack/vue-query', async () => (await import('../../helpers/tanstack')).tanstackMock)

import { fetchMock, resetTanstack, stubNuxtGlobals } from '../../helpers/tanstack'
import {
  storefrontKeys,
  useStorefrontMerchant,
  useStorefrontProduct,
  useSubmitOrder,
} from '../../../../app/features/storefront/composables/useStorefront'

beforeEach(() => {
  resetTanstack()
  stubNuxtGlobals()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('storefrontKeys', () => {
  it('génère les clés de cache', () => {
    expect(storefrontKeys.all).toEqual(['storefront'])
    expect(storefrontKeys.merchant('2250161407534')).toEqual([
      'storefront',
      'merchant',
      '2250161407534',
    ])
    expect(storefrontKeys.product('K001')).toEqual(['storefront', 'product', 'K001'])
  })
})

describe('queries storefront', () => {
  it('useStorefrontMerchant : clé + enabled selon phone non vide', async () => {
    const opts = useStorefrontMerchant('2250161407534') as Record<string, any>
    expect(opts.queryKey.value).toEqual(['storefront', 'merchant', '2250161407534'])
    expect(opts.enabled.value).toBe(true)
    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()
    expect((useStorefrontMerchant('') as Record<string, any>).enabled.value).toBe(false)
  })

  it('useStorefrontProduct : clé + enabled selon code non vide', async () => {
    const opts = useStorefrontProduct('K001') as Record<string, any>
    expect(opts.queryKey.value).toEqual(['storefront', 'product', 'K001'])
    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()
    expect((useStorefrontProduct('') as Record<string, any>).enabled.value).toBe(false)
  })
})

describe('useSubmitOrder', () => {
  it('la mutationFn envoie la commande via l’API', async () => {
    const opts = useSubmitOrder() as Record<string, any>
    await opts.mutationFn({ product_code: 'K001', client_phone: '2250161407534' })
    expect(fetchMock).toHaveBeenCalledOnce()
  })
})
