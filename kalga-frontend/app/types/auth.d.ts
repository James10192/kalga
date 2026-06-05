/**
 * Type augmentation pour `nuxt-auth-utils`.
 * Référence : ARCHITECTURE_FRONTEND.md section 7.1 (Auth flow)
 *
 * La session HttpOnly stocke :
 *  - user       : infos publiques de l'utilisateur (id, email, role, merchant_id)
 *  - accessToken: JWT du backend FastAPI — JAMAIS envoyé au browser
 */

import type { SessionUser } from '@/features/auth/types'

declare module '#auth-utils' {
  interface UserSession {
    user: SessionUser
  }

  // Données stockées en session mais NE JAMAIS renvoyées au client.
  interface SecureSessionData {
    /** JWT renvoyé par le backend FastAPI au login */
    accessToken: string
  }
}

export {}
