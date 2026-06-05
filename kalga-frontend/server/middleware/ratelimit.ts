/**
 * Rate limiting basique en mémoire pour les endpoints d'auth.
 * Référence : ARCHITECTURE_FRONTEND.md section 7.1 (auth flow)
 *
 * Protège contre les attaques brute-force sur /api/auth/login.
 * Pour une prod multi-instances, à remplacer par un store Redis.
 *
 * Limites :
 *  - /api/auth/login : 10 tentatives / 5 min par IP
 */

const WINDOW_MS = 5 * 60 * 1000 // 5 minutes
const MAX_ATTEMPTS = 10

interface RateLimitEntry {
  count: number
  resetAt: number
}

const RATE_LIMITED_PATHS = ['/api/auth/login']
const buckets = new Map<string, RateLimitEntry>()

function getClientIp(event: ReturnType<typeof defineEventHandler> extends (e: infer T) => unknown ? T : never): string {
  const headers = getRequestHeaders(event)
  const forwardedFor = headers['x-forwarded-for']
  if (typeof forwardedFor === 'string') {
    return forwardedFor.split(',')[0]?.trim() ?? 'unknown'
  }
  return getRequestIP(event, { xForwardedFor: true }) ?? 'unknown'
}

export default defineEventHandler((event) => {
  const url = event.node.req.url ?? ''
  if (!RATE_LIMITED_PATHS.some((p) => url.startsWith(p))) {
    return
  }

  const ip = getClientIp(event)
  const key = `${ip}:${url}`
  const now = Date.now()
  const entry = buckets.get(key)

  if (!entry || entry.resetAt < now) {
    buckets.set(key, { count: 1, resetAt: now + WINDOW_MS })
    return
  }

  if (entry.count >= MAX_ATTEMPTS) {
    throw createError({
      statusCode: 429,
      statusMessage: 'Trop de tentatives. Réessayez dans quelques minutes.',
    })
  }

  entry.count += 1
})
