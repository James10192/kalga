/**
 * Middleware global — charge l'utilisateur courant au début de chaque navigation.
 * Référence : ARCHITECTURE_FRONTEND.md section 7.1 (Auth flow)
 *
 * Utilise nuxt-auth-utils : useUserSession().fetch() interroge /api/auth/me.
 * Sans erreur si non connecté — c'est aux middlewares ciblés (merchant, admin)
 * de bloquer l'accès aux zones protégées.
 */

export default defineNuxtRouteMiddleware(async () => {
  const { loggedIn, fetch } = useUserSession()

  // Ne refait pas la requête si la session est déjà chargée
  if (loggedIn.value) {
    return
  }

  try {
    await fetch()
  } catch {
    // Pas de session active — on continue silencieusement
  }
})
