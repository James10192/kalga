/**
 * GET /api/auth/me
 *
 * Renvoie l'utilisateur courant depuis la session HttpOnly.
 * Le JWT n'est jamais inclus (il reste serveur-side dans la session).
 *
 * Renvoie 401 si non connecté (via requireUserSession).
 */

export default defineEventHandler(async (event) => {
  const session = await requireUserSession(event)
  return { user: session.user }
})
