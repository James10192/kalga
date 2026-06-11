/**
 * Client API — feature `auth`.
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.1 (Auth) + 7.2 (Data fetching) + 9.4
 *
 * Note : le login email/password est porté par `useAuth` (composable transverse)
 * qui appelle `/api/auth/login` — un composable a le droit de fetch (l'anti-pattern
 * §10 ne vise que les pages/composants .vue). Ici on regroupe les appels auth
 * restants qui doivent être consommés depuis une page via un composable dédié.
 *
 * `connectWhatsapp` cible la route serveur interne Nuxt `/api/whatsapp/connect`
 * (qui relaie vers le bridge WhatsApp), pas le proxy `/api/proxy/*`.
 */

import type { WhatsappConnectInput } from './types'

export const authApi = {
  /**
   * Provisionne la session WhatsApp d'un marchand (page login).
   * Le QR / status sont consultés ensuite (onboarding, PR ultérieure).
   * La réponse du bridge est opaque côté front → `unknown`.
   */
  connectWhatsapp: (data: WhatsappConnectInput): Promise<unknown> =>
    $fetch('/api/whatsapp/connect', {
      method: 'POST',
      body: data,
    }),
}
