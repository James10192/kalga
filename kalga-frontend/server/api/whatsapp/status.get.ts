/**
 * GET /api/whatsapp/status?phone=...
 * Relaie le statut de connexion WhatsApp d'un numéro (pour l'écran /connecting :
 * affichage du QR + détection de la connexion). HTTP only — la logique d'accès
 * au bridge est dans server/utils/whatsapp-bridge.ts.
 */

import { z } from 'zod'

import { PHONE_DIGITS_ONLY_REGEX } from '@/utils/constants'

const querySchema = z.object({
  phone: z.string().regex(PHONE_DIGITS_ONLY_REGEX, 'Numéro WhatsApp invalide'),
})

export default defineEventHandler(async (event) => {
  const { phone } = await getValidatedQuery(event, querySchema.parse)
  const status = await fetchBridgeStatus(phone)
  return {
    connected: status?.connected ?? false,
    qrCode: status?.qrCode ?? null,
  }
})
