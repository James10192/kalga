/**
 * Composable utilitaire — extrait un message d'erreur lisible
 * d'une erreur $fetch/createError (Nuxt/Nitro).
 *
 * Référence : ARCHITECTURE_FRONTEND.md section 7.9 (error handling)
 */

interface FetchError {
  statusCode?: number
  statusMessage?: string
  data?: { detail?: string; message?: string }
  message?: string
}

/**
 * Retourne un message d'erreur exploitable pour l'utilisateur.
 *
 * Ordre de priorité :
 *  1. `data.detail` du backend FastAPI
 *  2. `statusMessage` du proxy Nuxt
 *  3. `data.message`
 *  4. `message`
 *  5. fallback générique
 */
export function extractApiErrorMessage(err: unknown, fallback: string): string {
  if (!err || typeof err !== 'object') {
    return fallback
  }
  const e = err as FetchError
  return e.data?.detail ?? e.statusMessage ?? e.data?.message ?? e.message ?? fallback
}
