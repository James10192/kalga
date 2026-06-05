/**
 * POST /api/auth/logout
 *
 * Référence : ARCHITECTURE_FRONTEND.md section 7.1
 *
 * Détruit la session HttpOnly cookie.
 * Idempotent : OK même si pas de session active.
 */

export default defineEventHandler(async (event) => {
  await clearUserSession(event)
  return { ok: true }
})
