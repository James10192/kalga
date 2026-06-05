/**
 * Client API — feature `conversations`.
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 + 9.4
 *
 * Toutes les requêtes passent par le proxy `/api/proxy/*`.
 * Backend correspondant : kalga-api/app/routers/chat.py + ChatService.
 */

import type { Paginated } from '@/types/api'
import type { Conversation, MerchantReplyInput, Message } from './types'

function proxyUrl(path: string): string {
  const config = useRuntimeConfig()
  const base = config.public.apiUrl.endsWith('/')
    ? config.public.apiUrl.slice(0, -1)
    : config.public.apiUrl
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

export interface ConversationsListParams {
  merchantPhone: string
  status?: string
  page?: number
}

export const conversationsApi = {
  /** Liste paginée des conversations d'un marchand (filtrable par statut). */
  list: ({
    merchantPhone,
    status,
    page = 1,
  }: ConversationsListParams): Promise<Paginated<Conversation>> =>
    $fetch<Paginated<Conversation>>(proxyUrl(`/chat/conversations/${merchantPhone}`), {
      query: { status, page },
    }),

  /** Détail d'une conversation par ID. */
  getById: (id: number): Promise<Conversation> =>
    $fetch<Conversation>(proxyUrl(`/chat/conversations/${id}`)),

  /** Liste ordonnée des messages d'une conversation. */
  getMessages: (conversationId: number): Promise<Message[]> =>
    $fetch<Message[]>(proxyUrl(`/chat/conversations/${conversationId}/messages`)),

  /** Marchand répond manuellement (human takeover). */
  sendMerchantReply: (data: MerchantReplyInput): Promise<{ sent: boolean }> =>
    $fetch<{ sent: boolean }>(proxyUrl('/chat/merchant-reply'), {
      method: 'POST',
      body: data,
    }),
}
