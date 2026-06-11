/**
 * POST /api/merchant-upload/{id}
 * → backend POST /api/merchants/{id}/upload-image (multipart : file + image_type).
 *
 * Le proxy JSON générique (/api/proxy/*) fait `JSON.parse(body)` → il casse sur
 * du multipart. Cette route dédiée FORWARD le corps multipart tel quel via
 * `proxyRequest`, en injectant la clé interne (jamais exposée au browser).
 */

export default defineEventHandler((event) => {
  const config = useRuntimeConfig()
  if (!config.apiBackendUrl) {
    throw createError({ statusCode: 500, statusMessage: 'NUXT_API_BACKEND_URL non configuré' })
  }
  const id = getRouterParam(event, 'id')
  const base = config.apiBackendUrl.replace(/\/$/, '')

  return proxyRequest(event, `${base}/api/merchants/${id}/upload-image`, {
    headers: config.proxyInternalApiKey
      ? { 'x-internal-key': config.proxyInternalApiKey }
      : undefined,
  })
})
