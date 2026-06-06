/**
 * Tests Vitest — features/products/composables/useProducts.ts
 *
 * Wrappers TanStack Query : on mocke @tanstack/vue-query (capture des options),
 * on stub les globals Nuxt (computed/unref/$fetch/useRuntimeConfig) et on vérifie
 * le câblage queryKey / queryFn / onSuccess de chaque composable.
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
  productsKeys,
  useCreateProduct,
  useDeleteProduct,
  useProduct,
  useProductsList,
  useProductVariants,
  useUpdateProduct,
} from '../../../../app/features/products/composables/useProducts'

beforeEach(() => {
  resetTanstack()
  stubNuxtGlobals()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('productsKeys', () => {
  it('génère des clés de cache stables et hiérarchiques', () => {
    expect(productsKeys.all).toEqual(['products'])
    expect(productsKeys.list(1, 2)).toEqual(['products', 'list', 1, 2])
    expect(productsKeys.detail(7)).toEqual(['products', 'detail', 7])
    expect(productsKeys.variants(3)).toEqual(['products', 'variants', 3])
  })
})

describe('useProductsList', () => {
  it('câble queryKey/enabled et la queryFn appelle l’API', async () => {
    const opts = useProductsList(5, 1) as Record<string, any>
    expect(opts.queryKey.value).toEqual(['products', 'list', 5, 1])
    expect(opts.enabled.value).toBe(true)

    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()
  })

  it('enabled=false quand merchantId <= 0', () => {
    const opts = useProductsList(0, 1) as Record<string, any>
    expect(opts.enabled.value).toBe(false)
  })
})

describe('useProduct / useProductVariants', () => {
  it('useProduct câble la clé détail et désactive si id<=0', async () => {
    const opts = useProduct(9) as Record<string, any>
    expect(opts.queryKey.value).toEqual(['products', 'detail', 9])
    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()
    expect((useProduct(0) as Record<string, any>).enabled.value).toBe(false)
  })

  it('useProductVariants câble la clé variantes', async () => {
    const opts = useProductVariants(4) as Record<string, any>
    expect(opts.queryKey.value).toEqual(['products', 'variants', 4])
    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()
  })
})

describe('mutations products', () => {
  it('useCreateProduct appelle l’API et invalide la liste au succès', async () => {
    const opts = useCreateProduct(5) as Record<string, any>
    await opts.mutationFn({ name: 'Sac', price: 1000, min_price: 800 })
    expect(fetchMock).toHaveBeenCalledOnce()

    opts.onSuccess()
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['products'] })
  })

  it('useUpdateProduct invalide le détail ET la liste au succès', async () => {
    const opts = useUpdateProduct() as Record<string, any>
    await opts.mutationFn({ id: 9, data: { name: 'Maj' } })
    expect(fetchMock).toHaveBeenCalledOnce()

    opts.onSuccess({ id: 9 })
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['products', 'detail', 9] })
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['products'] })
  })

  it('useDeleteProduct invalide la liste au succès', async () => {
    const opts = useDeleteProduct() as Record<string, any>
    await opts.mutationFn(9)
    expect(fetchMock).toHaveBeenCalledOnce()

    opts.onSuccess()
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['products'] })
  })
})
