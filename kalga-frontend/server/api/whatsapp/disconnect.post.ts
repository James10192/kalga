/**
 * POST /api/whatsapp/disconnect
 * Déconnecte le WhatsApp du marchand puis ferme sa session Nuxt.
 * Référence : dashboard/static/app.js (disconnectWhatsApp).
 *
 * Best-effort sur le bridge (POST {bridge}/disconnect/{phone}) — on ferme la
 * session quoi qu'il arrive. Le téléphone vient de la session, jamais du client.
 */

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const session = await getUserSession(event)
  // L'augmentation de type #auth-utils vit côté app ; côté serveur on narrow.
  const phone = (session.user as { merchant_phone?: string | null } | undefined)?.merchant_phone

  if (phone && config.whatsappBridgeUrl) {
    const base = config.whatsappBridgeUrl.replace(/\/$/, '')
    try {
      await $fetch(`${base}/disconnect/${encodeURIComponent(phone)}`, {
        method: 'POST',
        headers: config.proxyInternalApiKey
          ? { 'X-Internal-Key': config.proxyInternalApiKey }
          : undefined,
      })
    } catch {
      // Best-effort : on ferme la session même si le bridge ne répond pas.
    }
  }

  await clearUserSession(event)
  return { success: true }
})
