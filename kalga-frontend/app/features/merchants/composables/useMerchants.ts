/**
 * Composables TanStack Query — feature `merchants`.
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 + 9.4
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRef } from 'vue'

import { CACHE_STALE_TIME_DEFAULT } from '@/utils/constants'
import { merchantsApi } from '../api'
import type {
  MerchantAwayModeUpdate,
  MerchantBotPersonaUpdate,
  MerchantLocationUpdate,
  MerchantProfileUpdate,
} from '../types'

export const merchantsKeys = {
  all: ['merchants'] as const,
  detail: (id: number) => ['merchants', 'detail', id] as const,
  list: (page: number, search: string) => ['merchants', 'list', page, search] as const,
}

export function useMerchant(id: MaybeRef<number>) {
  return useQuery({
    queryKey: computed(() => merchantsKeys.detail(unref(id))),
    queryFn: () => merchantsApi.getById(unref(id)),
    staleTime: CACHE_STALE_TIME_DEFAULT,
    enabled: computed(() => unref(id) > 0),
  })
}

export function useMerchantsList(page: MaybeRef<number>, search: MaybeRef<string>) {
  return useQuery({
    queryKey: computed(() => merchantsKeys.list(unref(page), unref(search))),
    queryFn: () => merchantsApi.list(unref(page), unref(search) || undefined),
    staleTime: CACHE_STALE_TIME_DEFAULT,
  })
}

/** Helper interne — invalide les queries d'un marchand après mutation. */
function invalidateMerchant(queryClient: ReturnType<typeof useQueryClient>, id: number): void {
  void queryClient.invalidateQueries({ queryKey: merchantsKeys.detail(id) })
  void queryClient.invalidateQueries({ queryKey: ['merchants', 'list'] })
}

export function useUpdateMerchantProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: MerchantProfileUpdate }) =>
      merchantsApi.updateProfile(id, data),
    onSuccess: (updated) => invalidateMerchant(queryClient, updated.id),
  })
}

export function useUpdateMerchantLocation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: MerchantLocationUpdate }) =>
      merchantsApi.updateLocation(id, data),
    onSuccess: (updated) => invalidateMerchant(queryClient, updated.id),
  })
}

export function useUpdateBotPersona() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: MerchantBotPersonaUpdate }) =>
      merchantsApi.updateBotPersona(id, data),
    onSuccess: (updated) => invalidateMerchant(queryClient, updated.id),
  })
}

export function useUpdateAwayMode() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: MerchantAwayModeUpdate }) =>
      merchantsApi.updateAwayMode(id, data),
    onSuccess: (updated) => invalidateMerchant(queryClient, updated.id),
  })
}
