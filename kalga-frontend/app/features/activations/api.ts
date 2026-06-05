/**
 * Client API — feature `activations`.
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 + 9.4
 *
 * Backend correspondant : kalga-api/app/routers/activation.py
 */

import type { Paginated } from '@/types/api'
import type { Activation, SendActivationCodeInput } from './types'

function proxyUrl(path: string): string {
  const config = useRuntimeConfig()
  const base = config.public.apiUrl.endsWith('/')
    ? config.public.apiUrl.slice(0, -1)
    : config.public.apiUrl
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

export const activationsApi = {
  /** Liste paginée des activations (toutes ou filtrées par statut). */
  list: (page = 1, status?: string): Promise<Paginated<Activation>> =>
    $fetch<Paginated<Activation>>(proxyUrl('/admin/activations'), {
      query: { page, status },
    }),

  /** Activations en attente d'envoi (alimentent la file admin). */
  listPending: (): Promise<ReadonlyArray<Activation>> =>
    $fetch<ReadonlyArray<Activation>>(proxyUrl('/admin/activations/pending')),

  /** Déclenche l'envoi d'un code d'activation pour un marchand. */
  send: (data: SendActivationCodeInput): Promise<Activation> =>
    $fetch<Activation>(proxyUrl('/admin/activations/send'), {
      method: 'POST',
      body: data,
    }),
}
