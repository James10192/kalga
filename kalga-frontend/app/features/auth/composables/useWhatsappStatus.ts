/**
 * Statut de connexion WhatsApp du marchand — pour le badge de l'en-tête dashboard.
 *
 * Interroge périodiquement GET /api/whatsapp/status?phone=... (relais bridge).
 * Léger et autonome — distinct de useWhatsappConnection (onboarding : QR + session).
 */

import { useQuery } from '@tanstack/vue-query'
import type { MaybeRef } from 'vue'

/** Intervalle de rafraîchissement du statut (30 s). */
const STATUS_POLL_INTERVAL_MS = 30_000

export function useWhatsappStatus(phone: MaybeRef<string>) {
  return useQuery({
    queryKey: computed(() => ['whatsapp', 'status', unref(phone)]),
    queryFn: () =>
      $fetch<{ connected: boolean }>('/api/whatsapp/status', {
        query: { phone: unref(phone) },
      }),
    enabled: computed(() => unref(phone).length > 0),
    refetchInterval: STATUS_POLL_INTERVAL_MS,
    staleTime: STATUS_POLL_INTERVAL_MS / 2,
  })
}
