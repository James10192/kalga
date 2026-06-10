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
  // `useUserSession().user` est typé par cette interface `User` : on la fait
  // porter la forme complète de notre session (id, email, role, merchant_id…).
  // L'augmentation de module impose une `interface` (un `type` ne fusionne pas),
  // d'où l'interface vide qui hérite de SessionUser — exception assumée.
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  interface User extends SessionUser {}

  interface UserSession {
    user: SessionUser
  }

  // Données stockées en session mais NE JAMAIS renvoyées au client.
  interface SecureSessionData {
    /** JWT renvoyé par le backend FastAPI au login admin. Absent pour un
     *  marchand (auth WhatsApp, pas de JWT) → optionnel. */
    accessToken?: string
  }
}

export {}
