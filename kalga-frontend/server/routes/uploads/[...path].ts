/**
 * Relais des fichiers /uploads/* vers le backend FastAPI.
 * Référence : ARCHITECTURE_FRONTEND.md §3 (flow) — le browser ne connaît jamais
 * l'URL réelle du backend.
 *
 * Le backend sert les images publiques (logos, bannières, photos produits) à
 * `/uploads/...`. Le frontend reçoit ces chemins relatifs dans les réponses API
 * (ex: image_url = "/uploads/logo_7_xxx.jpg") et les rend via `<img src="/uploads/...">`.
 * Sans ce relais, le browser chercherait l'image sur l'origine Nuxt (404).
 *
 * Public : pas d'auth (images de vitrine). On relaie tel quel vers le backend.
 */

export default defineEventHandler((event) => {
  const config = useRuntimeConfig()
  const path = getRouterParam(event, 'path') ?? ''
  const base = config.apiBackendUrl.replace(/\/$/, '')
  return proxyRequest(event, `${base}/uploads/${path}`)
})
