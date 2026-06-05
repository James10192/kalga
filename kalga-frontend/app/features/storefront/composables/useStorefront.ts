/**
 * Composables TanStack Query — feature `storefront`.
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 + 9.4
 */

import { useMutation, useQuery } from '@tanstack/vue-query'
import type { MaybeRef } from 'vue'

import { CACHE_STALE_TIME_LONG } from '@/utils/constants'
import { storefrontApi } from '../api'
import type { StorefrontOrderInput } from '../types'

export const storefrontKeys = {
  all: ['storefront'] as const,
  merchant: (phone: string) => ['storefront', 'merchant', phone] as const,
  product: (code: string) => ['storefront', 'product', code] as const,
}

export function useStorefrontMerchant(phone: MaybeRef<string>) {
  return useQuery({
    queryKey: computed(() => storefrontKeys.merchant(unref(phone))),
    queryFn: () => storefrontApi.getMerchant(unref(phone)),
    staleTime: CACHE_STALE_TIME_LONG,
    enabled: computed(() => unref(phone).length > 0),
  })
}

export function useStorefrontProduct(code: MaybeRef<string>) {
  return useQuery({
    queryKey: computed(() => storefrontKeys.product(unref(code))),
    queryFn: () => storefrontApi.getProduct(unref(code)),
    staleTime: CACHE_STALE_TIME_LONG,
    enabled: computed(() => unref(code).length > 0),
  })
}

/** Mutation : envoi d'une commande client. */
export function useSubmitOrder() {
  return useMutation({
    mutationFn: (data: StorefrontOrderInput) => storefrontApi.submitOrder(data),
  })
}
