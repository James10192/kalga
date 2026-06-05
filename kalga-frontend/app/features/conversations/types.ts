/**
 * Types inférés — feature `conversations`
 */

import type { z } from 'zod'

import type {
  conversationListFilterSchema,
  conversationSchema,
  merchantReplyInputSchema,
  messageSchema,
} from './schemas'

export type Conversation = z.infer<typeof conversationSchema>
export type Message = z.infer<typeof messageSchema>
export type MerchantReplyInput = z.infer<typeof merchantReplyInputSchema>
export type ConversationListFilter = z.infer<typeof conversationListFilterSchema>
