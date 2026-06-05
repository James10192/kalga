/**
 * Proxy transparent /api/proxy/* → FastAPI backend
 *
 * Référence : ARCHITECTURE_FRONTEND.md sections 3 (flow) + 4 (server/) + 7.1 (auth)
 *
 * Rôle :
 *  - Cacher l'URL réelle du backend au browser
 *  - Injecter X-Internal-Key (jamais exposée au browser)
 *  - Injecter Authorization: Bearer <JWT> depuis la session HttpOnly
 *  - Préserver méthode, body, query, status code
 *
 * Sécurité :
 *  - Pas d'auth requise au niveau du proxy (le backend FastAPI fait l'autorisation)
 *  - Les endpoints publics (vitrine) passent sans JWT
 *  - Les endpoints privés requièrent une session valide côté Nuxt
 */

import { callBackend, getAccessTokenFromSession } from '~/server/utils/api-client'

/** En-têtes à ne PAS forwarder du browser vers le backend */
const STRIPPED_INCOMING_HEADERS = new Set([
  'host',
  'connection',
  'content-length',
  'cookie', // les cookies Nuxt restent côté Nitro
  'authorization', // on injecte le JWT depuis la session, pas du browser
  'x-internal-key', // jamais accepté du browser
])

export default defineEventHandler(async (event) => {
  const path = getRouterParam(event, 'path') ?? ''
  if (!path) {
    throw createError({ statusCode: 400, statusMessage: 'Chemin proxy manquant' })
  }

  // Forward les headers du browser sauf ceux strippés
  const headers: Record<string, string> = {}
  for (const [key, value] of Object.entries(getRequestHeaders(event))) {
    if (typeof value === 'string' && !STRIPPED_INCOMING_HEADERS.has(key.toLowerCase())) {
      headers[key] = value
    }
  }

  // Lit le JWT depuis la session HttpOnly (si l'utilisateur est connecté)
  const accessToken = await getAccessTokenFromSession(event)

  // Forward méthode + body + query
  const method = getMethod(event) as 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  const query = getQuery(event) as Record<string, string | number | boolean | undefined>
  const body = method !== 'GET' && method !== 'DELETE' ? await readRawBody(event) : undefined

  try {
    return await callBackend(`/api/${path}`, {
      method,
      body: body ? JSON.parse(body) : undefined,
      query,
      accessToken,
      headers,
    })
  } catch (err: unknown) {
    // Re-throw createError pour préserver le status code remonté par $fetch
    if (err && typeof err === 'object' && 'statusCode' in err) {
      throw err
    }
    throw createError({
      statusCode: 502,
      statusMessage: 'Erreur de proxy vers le backend',
      cause: err,
    })
  }
})
