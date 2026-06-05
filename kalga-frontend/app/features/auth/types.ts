/**
 * Types inférés — feature `auth`
 * Référence : ARCHITECTURE_FRONTEND.md section 5.4 (SSOT : schémas Zod)
 */

import type { z } from 'zod'

import type {
  changePasswordInputSchema,
  forgotPasswordInputSchema,
  loginInputSchema,
  loginResponseSchema,
  sessionUserSchema,
} from './schemas'

export type LoginInput = z.infer<typeof loginInputSchema>
export type ForgotPasswordInput = z.infer<typeof forgotPasswordInputSchema>
export type ChangePasswordInput = z.infer<typeof changePasswordInputSchema>
export type SessionUser = z.infer<typeof sessionUserSchema>
export type LoginResponse = z.infer<typeof loginResponseSchema>
