/**
 * Middleware global — charge la session puis garde les zones protégées.
 * Référence : ARCHITECTURE_FRONTEND.md section 7.1 (Auth flow).
 *
 * Le gating est fait ICI, par chemin, plutôt que via `routeRules.appMiddleware` :
 * ce dernier dépend de l'app manifest Nuxt, non résolu en dev sur ce chemin
 * Windows/Unicode (import « #app-manifest »). On reste robuste et explicite.
 */

import { ROLE } from '@/utils/constants'

export default defineNuxtRouteMiddleware(async (to) => {
  const { loggedIn, user, fetch } = useUserSession()

  // Charge la session si pas encore connue (sans erreur si non connecté).
  if (!loggedIn.value) {
    try {
      await fetch()
    } catch {
      // Pas de session active — on continue ; les gardes ci-dessous décident.
    }
  }

  // Retire le préfixe de langue (/en, /ar) pour détecter la zone.
  const path = to.path.replace(/^\/(?:en|ar)(?=\/|$)/, '') || '/'

  // Zone marchand : connexion + compte actif requis.
  if (path.startsWith('/dashboard')) {
    if (!loggedIn.value || !user.value) {
      return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
    }
    if (!user.value.is_active) {
      return navigateTo('/account-suspended')
    }
  }

  // Zone admin (sauf la page de login admin) : rôle admin requis.
  if (path.startsWith('/admin') && path !== '/admin/login') {
    if (!loggedIn.value || !user.value) {
      return navigateTo({ path: '/admin/login', query: { redirect: to.fullPath } })
    }
    if (user.value.role !== ROLE.ADMIN) {
      return navigateTo('/dashboard')
    }
  }
})
