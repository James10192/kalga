/**
 * Composable TanStack Query — connexion WhatsApp marchand (page login).
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 (Data fetching) + 7.5 (une page ne fetch pas)
 *
 * Encapsule l'appel `authApi.connectWhatsapp` dans une mutation pour que la
 * page `login.vue` n'ait pas à faire de `$fetch` direct (anti-pattern §10).
 * Expose `isPending` pour piloter l'état de chargement du bouton.
 */

import { useMutation } from '@tanstack/vue-query'

import { authApi } from '../api'

export function useWhatsappConnect() {
  return useMutation({
    mutationFn: authApi.connectWhatsapp,
  })
}
