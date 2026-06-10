/**
 * Schémas Zod — feature `auth`
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.1 (Auth) + 7.4 (Validation)
 *
 * Source de vérité : les schémas Zod ci-dessous.
 * Les types TypeScript sont inférés via `z.infer` dans `./types.ts`.
 */

import { z } from 'zod'

import {
  EMAIL_MAX_LEN,
  PASSWORD_MAX_LEN,
  PASSWORD_MIN_LEN,
  PHONE_DIGITS_ONLY_REGEX,
  ROLE_VALUES,
} from '@/utils/constants'

// =============================================================================
// INPUTS UTILISATEUR
// =============================================================================

/** Form de login */
export const loginInputSchema = z.object({
  email: z.string().email('Email invalide').max(EMAIL_MAX_LEN),
  password: z
    .string()
    .min(PASSWORD_MIN_LEN, `Mot de passe : ${PASSWORD_MIN_LEN} caractères minimum`)
    .max(PASSWORD_MAX_LEN),
})

/** Form mot de passe oublié */
export const forgotPasswordInputSchema = z.object({
  email: z.string().email('Email invalide').max(EMAIL_MAX_LEN),
})

/** Form de connexion WhatsApp marchand (page login) — numéro complet indicatif + local */
export const whatsappConnectInputSchema = z.object({
  merchant_phone: z.string().regex(PHONE_DIGITS_ONLY_REGEX, 'Numéro WhatsApp invalide'),
})

/** Form changement de mot de passe */
export const changePasswordInputSchema = z
  .object({
    current_password: z.string().min(1, 'Mot de passe actuel requis'),
    new_password: z
      .string()
      .min(PASSWORD_MIN_LEN, `Nouveau mot de passe : ${PASSWORD_MIN_LEN} caractères minimum`)
      .max(PASSWORD_MAX_LEN),
    confirm_password: z.string().min(1, 'Confirmation requise'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    path: ['confirm_password'],
    message: 'Les mots de passe ne correspondent pas',
  })

// =============================================================================
// RÉPONSES SERVEUR
// =============================================================================

/** Session utilisateur (lue depuis HttpOnly cookie côté serveur, exposée au client) */
export const sessionUserSchema = z.object({
  id: z.number().int().positive(),
  /** Email (admin). `null` pour un marchand : il s'authentifie par WhatsApp, sans email. */
  email: z.string().email().nullable(),
  role: z.enum(ROLE_VALUES as [string, ...string[]]),
  is_active: z.boolean(),
  merchant_id: z.number().int().positive().nullable(),
  /** Téléphone du marchand (null pour les admins) */
  merchant_phone: z.string().nullable(),
})

/** Réponse de l'endpoint /api/auth/login */
export const loginResponseSchema = z.object({
  user: sessionUserSchema,
})
