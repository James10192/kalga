/**
 * Composables TanStack Query — feature `products`.
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 + 9.4 ; dashboard/static/app.js.
 *
 * KALGA ne permet PAS la modification d'un produit (on supprime et on recrée via
 * WhatsApp) : pas de composable de détail/édition. On expose la liste, la
 * création, la suppression, et la gestion du stock (par code).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRef } from 'vue'

import { CACHE_STALE_TIME_DEFAULT } from '@/utils/constants'
import { productsApi, type StockUpdateInput } from '../api'
import type { ProductCreateInput } from '../types'

/** Clés de cache standardisées pour la feature products. */
export const productsKeys = {
  all: ['products'] as const,
  list: (merchantId: number, page: number) => ['products', 'list', merchantId, page] as const,
}

/** Liste paginée des produits du marchand (re-fetch quand `page` change). */
export function useProductsList(merchantId: MaybeRef<number>, page: MaybeRef<number>) {
  return useQuery({
    queryKey: computed(() => productsKeys.list(unref(merchantId), unref(page))),
    queryFn: () => productsApi.list(unref(merchantId), unref(page)),
    staleTime: CACHE_STALE_TIME_DEFAULT,
    enabled: computed(() => unref(merchantId) > 0),
  })
}

/** Mutation : création d'un produit. Invalide la liste après succès. */
export function useCreateProduct(merchantId: MaybeRef<number>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: ProductCreateInput) => productsApi.create(unref(merchantId), data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: productsKeys.all })
    },
  })
}

/** Mutation : suppression d'un produit. Invalide la liste. */
export function useDeleteProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => productsApi.remove(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: productsKeys.all })
    },
  })
}

/**
 * Mutation : mise à jour du stock (par code). Invalide la liste (qui porte
 * stock_quantity et low_stock_threshold), donc les cartes se rafraîchissent.
 */
export function useUpdateStock() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ code, data }: { code: string; data: StockUpdateInput }) =>
      productsApi.updateStock(code, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: productsKeys.all })
    },
  })
}
