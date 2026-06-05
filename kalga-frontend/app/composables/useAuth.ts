/**
 * Composable d'auth — wrapper autour de `useUserSession` (nuxt-auth-utils).
 * Référence : ARCHITECTURE_FRONTEND.md section 7.1 (Auth flow)
 *
 * Expose :
 *  - user           : ref de l'utilisateur courant (ou null)
 *  - isLoggedIn     : bool réactif
 *  - isAdmin        : bool réactif (role admin)
 *  - isMerchant     : bool réactif (role merchant)
 *  - login(credentials)
 *  - logout()
 *
 * À utiliser dans tout composant qui dépend de l'auth.
 * Ne PAS appeler $fetch('/api/auth/login') directement.
 */

import { ROLE } from '@/utils/constants'
import { ROUTES } from '@/utils/routes'
import type { LoginInput, LoginResponse } from '@/features/auth/types'

export function useAuth() {
  const { user, loggedIn, fetch: refreshSession, clear } = useUserSession()
  const router = useRouter()

  const isAdmin = computed(() => user.value?.role === ROLE.ADMIN)
  const isMerchant = computed(() => user.value?.role === ROLE.MERCHANT)

  /**
   * Authentifie un utilisateur via /api/auth/login.
   * Le cookie HttpOnly est posé côté serveur, on rafraîchit ensuite la session.
   */
  async function login(credentials: LoginInput): Promise<LoginResponse> {
    const response = await $fetch<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: credentials,
    })
    await refreshSession()
    return response
  }

  /**
   * Déconnecte l'utilisateur et redirige vers la page de login.
   */
  async function logout(): Promise<void> {
    await $fetch('/api/auth/logout', { method: 'POST' })
    await clear()
    await router.push(ROUTES.login)
  }

  return {
    user,
    isLoggedIn: loggedIn,
    isAdmin,
    isMerchant,
    login,
    logout,
  }
}
