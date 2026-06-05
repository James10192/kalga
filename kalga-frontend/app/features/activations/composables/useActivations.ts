/**
 * Composables TanStack Query — feature `activations`.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRef } from 'vue'

import { CACHE_STALE_TIME_DEFAULT, CACHE_STALE_TIME_SHORT } from '@/utils/constants'
import { activationsApi } from '../api'
import type { SendActivationCodeInput } from '../types'

export const activationsKeys = {
  all: ['activations'] as const,
  list: (page: number, status: string | undefined) =>
    ['activations', 'list', page, status ?? 'all'] as const,
  pending: () => ['activations', 'pending'] as const,
}

export function useActivationsList(
  page: MaybeRef<number>,
  status: MaybeRef<string | undefined>,
) {
  return useQuery({
    queryKey: computed(() => activationsKeys.list(unref(page), unref(status))),
    queryFn: () => activationsApi.list(unref(page), unref(status)),
    staleTime: CACHE_STALE_TIME_DEFAULT,
  })
}

export function usePendingActivations() {
  return useQuery({
    queryKey: activationsKeys.pending(),
    queryFn: () => activationsApi.listPending(),
    staleTime: CACHE_STALE_TIME_SHORT,
  })
}

export function useSendActivationCode() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: SendActivationCodeInput) => activationsApi.send(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: activationsKeys.all })
    },
  })
}
