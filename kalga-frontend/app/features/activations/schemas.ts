/**
 * Schémas Zod — feature `activations`
 *
 * Codes d'activation à 6 chiffres envoyés par WhatsApp au marchand
 * après paiement, pour activer son compte.
 */

import { z } from 'zod'

import {
  ACTIVATION_CODE_REGEX,
  ACTIVATION_STATUS_VALUES,
  PHONE_DIGITS_ONLY_REGEX,
} from '@/utils/constants'

export const activationSchema = z.object({
  id: z.number().int().positive(),
  merchant_id: z.number().int().positive(),
  merchant_name: z.string().nullable(),
  merchant_phone: z.string().regex(PHONE_DIGITS_ONLY_REGEX).nullable(),
  code: z.string().regex(ACTIVATION_CODE_REGEX, 'Code d\'activation invalide (6 chiffres)'),
  status: z.enum(ACTIVATION_STATUS_VALUES as unknown as readonly [string, ...string[]]),
  admin_email: z.string().email().nullable(),
  sent_at: z.string().datetime().nullable(),
  used_at: z.string().datetime().nullable(),
  expires_at: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
})

/** Input pour envoyer un code (admin déclenche) */
export const sendActivationCodeInputSchema = z.object({
  merchant_id: z.number().int().positive(),
})

/** Input pour utiliser un code (marchand saisit) */
export const useActivationCodeInputSchema = z.object({
  code: z.string().regex(ACTIVATION_CODE_REGEX, 'Code à 6 chiffres requis'),
})
