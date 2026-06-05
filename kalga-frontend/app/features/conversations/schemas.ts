/**
 * Schémas Zod — feature `conversations`
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.4 + 10
 *
 * Aligné sur kalga-api/app/models/{schemas.py,enums.py}.
 */

import { z } from 'zod'

import {
  CONVERSATION_STATUS_VALUES,
  MESSAGE_MAX_LEN,
  PHONE_DIGITS_ONLY_REGEX,
  PRICE_MAX,
  PRICE_MIN,
} from '@/utils/constants'

// =============================================================================
// CONVERSATION
// =============================================================================

export const conversationSchema = z.object({
  id: z.number().int().positive(),
  merchant_id: z.number().int().positive(),
  product_id: z.number().int().positive(),
  client_phone: z.string().regex(PHONE_DIGITS_ONLY_REGEX, 'Téléphone invalide'),
  client_name: z.string().nullable(),
  status: z.enum(
    CONVERSATION_STATUS_VALUES as unknown as readonly [string, ...string[]],
  ),
  current_offer: z.number().int().min(PRICE_MIN).max(PRICE_MAX).nullable(),
  selected_variant_id: z.number().int().positive().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
})

// =============================================================================
// MESSAGE
// =============================================================================

export const messageSchema = z.object({
  id: z.number().int().positive(),
  conversation_id: z.number().int().positive(),
  content: z.string().max(MESSAGE_MAX_LEN),
  is_from_client: z.boolean(),
  created_at: z.string().datetime(),
})

// =============================================================================
// HUMAN TAKEOVER (marchand répond manuellement)
// =============================================================================

export const merchantReplyInputSchema = z.object({
  merchant_id: z.number().int().positive(),
  conversation_id: z.number().int().positive(),
  client_phone: z.string().regex(PHONE_DIGITS_ONLY_REGEX),
  client_question: z.string().min(1).max(MESSAGE_MAX_LEN),
  merchant_answer: z
    .string()
    .min(1, 'Réponse requise')
    .max(MESSAGE_MAX_LEN, `Réponse : ${MESSAGE_MAX_LEN} caractères maximum`),
  save_to_kb: z.boolean().default(true),
})

// =============================================================================
// FILTRES LISTE
// =============================================================================

export const conversationListFilterSchema = z.object({
  status: z
    .enum(CONVERSATION_STATUS_VALUES as unknown as readonly [string, ...string[]])
    .optional(),
  client_phone: z.string().optional(),
  product_id: z.number().int().positive().optional(),
})
