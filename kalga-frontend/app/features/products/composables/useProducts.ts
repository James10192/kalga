/**
 * Composables TanStack Query — feature `products`.
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 (Data fetching) + 9.4
 *
 * Pattern :
 *  - 1 fonction par cas d'usage (liste, détail, create, update, delete)
 *  - Les mutations invalident les queries impactées via `invalidateQueries`
 *  - Les paramètres acceptent des `Ref` pour la réactivité
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRef } from 'vue'

import { CACHE_STALE_TIME_DEFAULT } from '@/utils/constants'
import { productsApi } from '../api'
import type { ProductCreateInput, ProductUpdateInput } from '../types'

/** Clés de cache standardisées pour la feature products. */
export const productsKeys = {
  /** Toute la feature */
  all: ['products'] as const,
  /** Liste des produits d'un marchand */
  list: (merchantId: number, page: number) =>
    ['products', 'list', merchantId, page] as const,
  /** Détail d'un produit par id */
  detail: (id: number) => ['products', 'detail', id] as const,
  /** Variantes d'un produit */
  variants: (productId: number) => ['products', 'variants', productId] as const,
}

/**
 * Liste paginée des produits du marchand.
 * Re-fetch automatique quand `page` change.
 */
export function useProductsList(merchantId: MaybeRef<number>, page: MaybeRef<number>) {
  return useQuery({
    queryKey: computed(() => productsKeys.list(unref(merchantId), unref(page))),
    queryFn: () => productsApi.list(unref(merchantId), unref(page)),
    staleTime: CACHE_STALE_TIME_DEFAULT,
    enabled: computed(() => unref(merchantId) > 0),
  })
}

/** Détail d'un produit par id. */
export function useProduct(id: MaybeRef<number>) {
  return useQuery({
    queryKey: computed(() => productsKeys.detail(unref(id))),
    queryFn: () => productsApi.getById(unref(id)),
    staleTime: CACHE_STALE_TIME_DEFAULT,
    enabled: computed(() => unref(id) > 0),
  })
}

/** Liste des variantes d'un produit. */
export function useProductVariants(productId: MaybeRef<number>) {
  return useQuery({
    queryKey: computed(() => productsKeys.variants(unref(productId))),
    queryFn: () => productsApi.listVariants(unref(productId)),
    staleTime: CACHE_STALE_TIME_DEFAULT,
    enabled: computed(() => unref(productId) > 0),
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

/** Mutation : mise à jour d'un produit. Invalide détail + liste. */
export function useUpdateProduct() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProductUpdateInput }) =>
      productsApi.update(id, data),
    onSuccess: (updated) => {
      void queryClient.invalidateQueries({ queryKey: productsKeys.detail(updated.id) })
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
