/**
 * Middleware route — protège l'accès aux zones marchand.
 * Référence : ARCHITECTURE_FRONTEND.md section 7.1 (Auth flow)
 *
 * Appliqué via `routeRules: { '/dashboard/**': { appMiddleware: ['merchant'] } }`.
 * Redirige vers /login si non connecté.
 */

export default defineNuxtRouteMiddleware((to) => {
  const { loggedIn, user } = useUserSession()

  if (!loggedIn.value || !user.value) {
    return navigateTo({
      path: '/login',
      query: { redirect: to.fullPath },
    })
  }

  if (!user.value.is_active) {
    return navigateTo('/account-suspended')
  }
})
