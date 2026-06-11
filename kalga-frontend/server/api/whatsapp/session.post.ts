/**
 * POST /api/whatsapp/session  { merchant_phone }
 * Établit la session marchand APRÈS que le QR a été scanné.
 *
 * HTTP only : valide l'entrée, délègue la logique métier au service pur
 * `resolveMerchantSession` (server/utils/merchant-session.ts) en lui injectant
 * les clients réels (bridge + backend), puis pose la session HttpOnly.
 *
 * Sécurité : la session n'est ouverte que si le bridge confirme une session
 * WhatsApp connectée pour ce numéro — vérifié côté serveur, jamais sur la simple
 * affirmation du client.
 */

import { z } from 'zod'

import { PHONE_DIGITS_ONLY_REGEX } from '@/utils/constants'

const bodySchema = z.object({
  merchant_phone: z.string().regex(PHONE_DIGITS_ONLY_REGEX, 'Numéro WhatsApp invalide'),
})

export default defineEventHandler(async (event) => {
  const { merchant_phone } = await readValidatedBody(event, bodySchema.parse)

  try {
    const user = await resolveMerchantSession(merchant_phone, {
      getStatus: fetchBridgeStatus,
      getMerchant: fetchMerchantByPhone,
    })

    await setUserSession(event, { user })
    return { user }
  } catch (error) {
    if (error instanceof WhatsappNotConnectedError) {
      throw createError({
        statusCode: 425, // Too Early — WhatsApp pas encore connecté
        statusMessage: 'WhatsApp pas encore connecté',
      })
    }
    if (error instanceof MerchantNotFoundError) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Aucun marchand pour ce numéro',
      })
    }
    throw error
  }
})
