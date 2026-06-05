/**
 * Middleware route — protège l'accès aux zones admin.
 * Référence : ARCHITECTURE_FRONTEND.md section 7.1 (Auth flow)
 *
 * Appliqué via `routeRules: { '/admin/**': { appMiddleware: ['merchant', 'admin'] } }`.
 * `merchant` vérifie déjà la connexion ; ici on contrôle juste le rôle.
 */

import { ROLE } from '@/utils/constants'

export default defineNuxtRouteMiddleware(() => {
  const { user } = useUserSession()

  if (user.value?.role !== ROLE.ADMIN) {
    return navigateTo('/dashboard')
  }
})
