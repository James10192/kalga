/**
 * Composables TanStack Query — feature `conversations`.
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 + 9.4
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRef } from 'vue'

import { CACHE_STALE_TIME_DEFAULT, CACHE_STALE_TIME_SHORT } from '@/utils/constants'
import { conversationsApi } from '../api'
import type { MerchantReplyInput } from '../types'

export const conversationsKeys = {
  all: ['conversations'] as const,
  list: (merchantPhone: string, status: string | undefined, page: number) =>
    ['conversations', 'list', merchantPhone, status ?? 'all', page] as const,
  detail: (id: number) => ['conversations', 'detail', id] as const,
  messages: (id: number) => ['conversations', 'messages', id] as const,
}

export function useConversationsList(
  merchantPhone: MaybeRef<string>,
  status: MaybeRef<string | undefined>,
  page: MaybeRef<number>,
) {
  return useQuery({
    queryKey: computed(() =>
      conversationsKeys.list(unref(merchantPhone), unref(status), unref(page)),
    ),
    queryFn: () =>
      conversationsApi.list({
        merchantPhone: unref(merchantPhone),
        status: unref(status),
        page: unref(page),
      }),
    staleTime: CACHE_STALE_TIME_DEFAULT,
    enabled: computed(() => unref(merchantPhone).length > 0),
  })
}

/**
 * Messages d'une conversation.
 * Refetch plus fréquent (30 s) pour donner un effet "presque temps réel"
 * en l'absence de WebSocket/SSE.
 */
export function useConversationMessages(id: MaybeRef<number>) {
  return useQuery({
    queryKey: computed(() => conversationsKeys.messages(unref(id))),
    queryFn: () => conversationsApi.getMessages(unref(id)),
    staleTime: CACHE_STALE_TIME_SHORT,
    refetchInterval: 30_000,
    enabled: computed(() => unref(id) > 0),
  })
}

/**
 * Mutation : marchand répond manuellement à une conversation.
 * Invalide les messages + la conversation après succès.
 */
export function useSendMerchantReply() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: MerchantReplyInput) => conversationsApi.sendMerchantReply(data),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: conversationsKeys.messages(variables.conversation_id),
      })
      void queryClient.invalidateQueries({
        queryKey: conversationsKeys.detail(variables.conversation_id),
      })
      void queryClient.invalidateQueries({
        queryKey: ['conversations', 'list'],
      })
    },
  })
}

/** Mutation : accepte l'offre / marque la vente faite. Invalide les listes. */
export function useAcceptConversation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => conversationsApi.accept(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: conversationsKeys.all })
    },
  })
}

/** Mutation : rejette l'offre du client. Invalide les listes. */
export function useRejectConversation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => conversationsApi.reject(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: conversationsKeys.all })
    },
  })
}
