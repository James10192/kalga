/**
 * Client infra — bridge WhatsApp (Node/Baileys, :3001).
 * Référence : kalga-whatsapp/src/api/routes/status.routes.js.
 *
 * Le bridge expose `GET /status/:phone` :
 *  - 404 si aucun client pour ce numéro (jamais lancé) ;
 *  - 200 avec `{ connected, ready, qrCode, realPhone }` sinon.
 *
 * Côté serveur Nitro uniquement — l'URL du bridge n'est jamais exposée au client.
 */

import type { BridgeStatus } from './merchant-session'

/** Statut enrichi (ajoute le QR pour l'écran d'onboarding). */
export interface BridgeClientStatus extends BridgeStatus {
  qrCode: string | null
}

interface RawBridgeStatus {
  connected?: boolean
  ready?: boolean
  qrCode?: string | null
  realPhone?: string | null
}

function bridgeBaseUrl(): string {
  const config = useRuntimeConfig()
  if (!config.whatsappBridgeUrl) {
    throw createError({
      statusCode: 500,
      statusMessage: 'NUXT_WHATSAPP_BRIDGE_URL non configuré',
    })
  }
  return config.whatsappBridgeUrl.replace(/\/$/, '')
}

/**
 * Lit le statut WhatsApp d'un numéro. Retourne `null` si le bridge ne connaît
 * pas ce numéro (404) — c.-à-d. aucune session WhatsApp en cours.
 */
export async function fetchBridgeStatus(phone: string): Promise<BridgeClientStatus | null> {
  const url = `${bridgeBaseUrl()}/status/${encodeURIComponent(phone)}`
  try {
    const data = await $fetch<RawBridgeStatus>(url)
    return {
      connected: Boolean(data.connected ?? data.ready),
      ready: Boolean(data.ready),
      realPhone: data.realPhone ?? null,
      qrCode: data.qrCode ?? null,
    }
  } catch (error) {
    if (isNotFound(error)) {
      return null
    }
    throw error
  }
}

function isNotFound(error: unknown): boolean {
  return (
    typeof error === 'object' &&
    error !== null &&
    'statusCode' in error &&
    (error as { statusCode?: number }).statusCode === 404
  )
}
