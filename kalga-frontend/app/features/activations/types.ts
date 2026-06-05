/**
 * Types inférés — feature `activations`
 */

import type { z } from 'zod'

import type {
  activationSchema,
  sendActivationCodeInputSchema,
  useActivationCodeInputSchema,
} from './schemas'

export type Activation = z.infer<typeof activationSchema>
export type SendActivationCodeInput = z.infer<typeof sendActivationCodeInputSchema>
export type UseActivationCodeInput = z.infer<typeof useActivationCodeInputSchema>
