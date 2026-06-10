/**
 * Composable — pilote l'onboarding WhatsApp du marchand sur /connecting.
 * Référence : ARCHITECTURE_FRONTEND.md §7.1 (auth) ; modèle réel KALGA.
 *
 * Flux : on interroge périodiquement `GET /api/whatsapp/status` (le bridge
 * fournit le QR puis l'état `connected`). Dès que connecté, on établit la
 * session marchand via `POST /api/whatsapp/session`, puis on redirige vers le
 * tableau de bord.
 *
 * Le polling impératif (jusqu'à connexion) ne relève pas de TanStack Query
 * (données mises en cache) : `useIntervalFn` + `$fetch` est l'outil adapté ici.
 */

import { useIntervalFn } from '@vueuse/core'
import type { MaybeRefOrGetter } from 'vue'

const POLL_INTERVAL_MS = 2500

interface WhatsappStatus {
  connected: boolean
  qrCode: string | null
}

export interface WhatsappConnectionState {
  /** Données du QR à afficher (null tant que le bridge ne l'a pas généré). */
  qrCode: Readonly<Ref<string | null>>
  /** WhatsApp connecté (QR scanné). */
  connected: Readonly<Ref<boolean>>
  /** Établissement de la session en cours (juste avant la redirection). */
  establishing: Readonly<Ref<boolean>>
  /** Message d'erreur à afficher (session échouée), sinon null. */
  error: Readonly<Ref<string | null>>
}

export function useWhatsappConnection(
  phone: MaybeRefOrGetter<string>,
): WhatsappConnectionState {
  const phoneRef = toRef(phone)
  const qrCode = ref<string | null>(null)
  const connected = ref(false)
  const establishing = ref(false)
  const error = ref<string | null>(null)

  const { pause, resume } = useIntervalFn(poll, POLL_INTERVAL_MS, { immediate: false })

  async function poll(): Promise<void> {
    if (!phoneRef.value) return
    try {
      const status = await $fetch<WhatsappStatus>('/api/whatsapp/status', {
        query: { phone: phoneRef.value },
      })
      qrCode.value = status.qrCode
      if (status.connected && !connected.value) {
        connected.value = true
        pause()
        await establishSession()
      }
    } catch {
      // Erreur transitoire (bridge qui démarre, réseau) : on continue de poller.
    }
  }

  async function establishSession(): Promise<void> {
    establishing.value = true
    error.value = null
    try {
      await $fetch('/api/whatsapp/session', {
        method: 'POST',
        body: { merchant_phone: phoneRef.value },
      })
      await navigateTo('/dashboard')
    } catch {
      // La connexion WhatsApp a été vue mais la session a échoué : on laisse
      // l'utilisateur reprendre (le polling reprend pour retenter).
      establishing.value = false
      connected.value = false
      error.value = 'session'
      resume()
    }
  }

  onMounted(() => {
    if (phoneRef.value) resume()
  })
  onScopeDispose(pause)

  return {
    qrCode: readonly(qrCode),
    connected: readonly(connected),
    establishing: readonly(establishing),
    error: readonly(error),
  }
}
