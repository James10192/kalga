/**
 * Client HTTP serveur vers le backend FastAPI.
 * Référence : ARCHITECTURE_FRONTEND.md sections 4 (server/utils/) + 7.1 (auth)
 *
 * Ce client est utilisé UNIQUEMENT côté serveur (Nitro).
 * Il injecte automatiquement la clé interne `X-Internal-Key` pour
 * authentifier le frontend auprès du backend.
 *
 * Le browser n'a jamais accès à cette clé.
 */

import type { H3Event } from 'h3'

/** Options de requête vers le backend FastAPI */
export interface BackendRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  query?: Record<string, string | number | boolean | undefined>
  /** JWT utilisateur si la route requiert l'auth (lu depuis la session) */
  accessToken?: string
  /** Headers additionnels (Content-Type, etc.) */
  headers?: Record<string, string>
}

/**
 * Construit l'URL absolue du backend pour un chemin donné.
 * Lance une erreur si `apiBackendUrl` n'est pas configuré (fail-fast).
 */
function buildBackendUrl(path: string): string {
  const config = useRuntimeConfig()
  const base = config.apiBackendUrl

  if (!base) {
    throw createError({
      statusCode: 500,
      statusMessage: 'NUXT_API_BACKEND_URL non configurée',
    })
  }

  const normalizedBase = base.endsWith('/') ? base.slice(0, -1) : base
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${normalizedBase}${normalizedPath}`
}

/**
 * Construit les headers à envoyer au backend FastAPI.
 * - Injecte X-Internal-Key (jamais exposé au browser)
 * - Injecte Authorization si un JWT utilisateur est fourni
 * - Ajoute Content-Type JSON par défaut si body présent
 */
function buildHeaders(opts: BackendRequestOptions): HeadersInit {
  const config = useRuntimeConfig()
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...opts.headers,
  }

  if (config.proxyInternalApiKey) {
    headers['X-Internal-Key'] = config.proxyInternalApiKey
  }

  if (opts.accessToken) {
    headers['Authorization'] = `Bearer ${opts.accessToken}`
  }

  if (opts.body !== undefined && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  return headers
}

/**
 * Appelle un endpoint du backend FastAPI depuis le code serveur Nitro.
 *
 * @param path     Chemin relatif (ex: '/api/auth/login')
 * @param opts     Options de requête
 * @returns        La réponse JSON parsée et typée
 * @throws         createError() si le backend renvoie un code >=400
 */
export async function callBackend<T = unknown>(
  path: string,
  opts: BackendRequestOptions = {},
): Promise<T> {
  return $fetch<T>(buildBackendUrl(path), {
    method: opts.method ?? 'GET',
    headers: buildHeaders(opts),
    body: opts.body,
    query: opts.query,
  })
}

/**
 * Lit le JWT utilisateur depuis la session HttpOnly cookie.
 * Retourne undefined si l'utilisateur n'est pas authentifié.
 */
export async function getAccessTokenFromSession(event: H3Event): Promise<string | undefined> {
  const session = await getUserSession(event)
  // Le JWT est stocké en partie sécurisée de la session (non sérialisée vers le client)
  const secure = session?.secure as { accessToken?: string } | undefined
  return secure?.accessToken
}
