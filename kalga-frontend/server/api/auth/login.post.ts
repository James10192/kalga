/**
 * POST /api/auth/login
 *
 * Référence : ARCHITECTURE_FRONTEND.md section 7.1 (Auth flow)
 *
 * Flow :
 *  1. Lit { email, password } du body, validé par Zod
 *  2. Appelle le backend FastAPI POST /api/auth/login
 *  3. Pose le HttpOnly cookie via setUserSession (user + JWT en secure)
 *  4. Renvoie le user au browser (PAS le JWT)
 */

import { loginInputSchema } from '@/features/auth/schemas'
import { callBackend } from '~/server/utils/api-client'

interface BackendLoginResponse {
  access_token: string
  refresh_token?: string
  token_type: string
  user: {
    id: number
    email: string
    role: 'admin' | 'merchant'
    is_active: boolean
    merchant_id: number | null
    merchant_phone: string | null
  }
}

export default defineEventHandler(async (event) => {
  const body = await readValidatedBody(event, loginInputSchema.safeParse)

  if (!body.success) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Données de connexion invalides',
      data: { errors: body.error.issues },
    })
  }

  let result: BackendLoginResponse
  try {
    result = await callBackend<BackendLoginResponse>('/api/auth/login', {
      method: 'POST',
      body: body.data,
    })
  } catch (err) {
    // Le backend renvoie 401 ou 422 — on remappe en message standardisé
    throw createError({
      statusCode: 401,
      statusMessage: 'Identifiants invalides',
      cause: err,
    })
  }

  if (!result.user.is_active) {
    throw createError({ statusCode: 403, statusMessage: 'Compte désactivé' })
  }

  const publicUser = {
    id: result.user.id,
    email: result.user.email,
    role: result.user.role,
    is_active: result.user.is_active,
    merchant_id: result.user.merchant_id,
    merchant_phone: result.user.merchant_phone,
  }

  // Pose la session HttpOnly. Le JWT est stocké dans `secure` (non exposé client-side).
  await setUserSession(event, {
    user: publicUser,
    secure: {
      accessToken: result.access_token,
    },
  })

  return { user: publicUser }
})
