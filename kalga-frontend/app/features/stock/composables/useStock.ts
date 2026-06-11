/**
 * Composables TanStack Query — feature `stock`.
 * Réf : dashboard/static/app.js (loadStockSection / renderStockTable).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRef } from 'vue'

import { CACHE_STALE_TIME_DEFAULT } from '@/utils/constants'
import { stockApi } from '../api'
import type { RestockInput, StockMode } from '../types'

export const stockKeys = {
  all: ['stock'] as const,
  overview: (merchantId: number) => ['stock', 'overview', merchantId] as const,
  critique: (merchantId: number) => ['stock', 'critique', merchantId] as const,
}

/** Vue d'ensemble du stock du marchand. */
export function useStockOverview(merchantId: MaybeRef<number>) {
  return useQuery({
    queryKey: computed(() => stockKeys.overview(unref(merchantId))),
    queryFn: () => stockApi.getOverview(unref(merchantId)),
    staleTime: CACHE_STALE_TIME_DEFAULT,
    enabled: computed(() => unref(merchantId) > 0),
  })
}

/** Synthèse « stock critique » pour le widget de l'Aperçu. */
export function useStockCritique(merchantId: MaybeRef<number>) {
  return useQuery({
    queryKey: computed(() => stockKeys.critique(unref(merchantId))),
    queryFn: () => stockApi.getCritique(unref(merchantId)),
    staleTime: CACHE_STALE_TIME_DEFAULT,
    enabled: computed(() => unref(merchantId) > 0),
  })
}

/** Mutation : change le mode rupture d'un produit. Invalide l'overview. */
export function useUpdateStockMode() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (vars: { code: string; mode: StockMode; merchantId: number }) =>
      stockApi.updateMode(vars.code, vars.mode, vars.merchantId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: stockKeys.all })
    },
  })
}

/** Mutation : réapprovisionne un produit. Invalide l'overview + la liste produits. */
export function useRestock() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (vars: { code: string; data: RestockInput }) =>
      stockApi.restock(vars.code, vars.data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: stockKeys.all })
      void queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}
