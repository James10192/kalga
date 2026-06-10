/**
 * POST /api/whatsapp/connect
 *
 * Proxy vers le bridge WhatsApp (POST /connect, port 3001 par défaut).
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.1 + 7.2 + 9.4
 *
 * Backend (Node bridge) : kalga-whatsapp/src/api/routes/connect.routes.js
 * Le bridge accepte `{ merchant_phone }` et provisionne la session WhatsApp
 * du marchand. Le QR Code et le status sont ensuite consultés via d'autres
 * endpoints (couverts dans une PR ultérieure : onboarding QR).
 *
 * Sécurité : le bridge protège ses POST par un header `X-Internal-Key`
 * (cf. kalga-whatsapp/src/loaders/express.js) = la clé interne partagée
 * (NUXT_PROXY_INTERNAL_API_KEY, identique à INTERNAL_API_KEY du bridge/API).
 * On l'injecte côté serveur, jamais exposée au browser. On valide aussi le
 * payload pour rejeter vite les requêtes mal formées.
 */

import { z } from 'zod'

// `~/` en Nuxt 4 compatibility alias = srcDir (= `app/`), donc on utilise
// `@/utils/*` qui pointe explicitement vers `app/utils/*` (cf tsconfig.json paths).
import { PHONE_DIGITS_ONLY_REGEX } from '@/utils/constants'

const bodySchema = z.object({
  merchant_phone: z
    .string()
    .regex(PHONE_DIGITS_ONLY_REGEX, 'Phone must be digits only, 10-15 length'),
})

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  if (!config.whatsappBridgeUrl) {
    throw createError({
      statusCode: 503,
      statusMessage: 'WhatsApp bridge not configured (NUXT_WHATSAPP_BRIDGE_URL)',
    })
  }

  const body = await readValidatedBody(event, (raw) => bodySchema.parse(raw))

  const url = `${config.whatsappBridgeUrl.replace(/\/$/, '')}/connect`

  try {
    return await $fetch(url, {
      method: 'POST',
      body,
      headers: config.proxyInternalApiKey
        ? { 'X-Internal-Key': config.proxyInternalApiKey }
        : undefined,
    })
  } catch (err) {
    const status = (err as { statusCode?: number }).statusCode ?? 502
    throw createError({
      statusCode: status,
      statusMessage:
        (err as { statusMessage?: string }).statusMessage ?? 'WhatsApp bridge error',
      data: (err as { data?: unknown }).data,
    })
  }
})
