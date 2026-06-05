/**
 * Client API — feature `merchants`.
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 + 9.4
 *
 * Backend correspondant : kalga-api/app/routers/merchants.py
 */

import type { Paginated } from '@/types/api'
import type {
  Merchant,
  MerchantAwayModeUpdate,
  MerchantBotPersonaUpdate,
  MerchantLocationUpdate,
  MerchantProfileUpdate,
} from './types'

function proxyUrl(path: string): string {
  const config = useRuntimeConfig()
  const base = config.public.apiUrl.endsWith('/')
    ? config.public.apiUrl.slice(0, -1)
    : config.public.apiUrl
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

export const merchantsApi = {
  /** Détail d'un marchand par ID. */
  getById: (id: number): Promise<Merchant> => $fetch<Merchant>(proxyUrl(`/merchants/${id}`)),

  /** Liste paginée (admin). */
  list: (page = 1, search?: string): Promise<Paginated<Merchant>> =>
    $fetch<Paginated<Merchant>>(proxyUrl('/merchants'), { query: { page, search } }),

  /** Met à jour le profil (nom, business_name, paiement). */
  updateProfile: (id: number, data: MerchantProfileUpdate): Promise<Merchant> =>
    $fetch<Merchant>(proxyUrl(`/merchants/${id}/profile`), { method: 'PUT', body: data }),

  /** Met à jour la localisation (adresse + GPS). */
  updateLocation: (id: number, data: MerchantLocationUpdate): Promise<Merchant> =>
    $fetch<Merchant>(proxyUrl(`/merchants/${id}/location`), { method: 'PUT', body: data }),

  /** Met à jour la persona du bot IA. */
  updateBotPersona: (id: number, data: MerchantBotPersonaUpdate): Promise<Merchant> =>
    $fetch<Merchant>(proxyUrl(`/merchants/${id}/bot-persona`), { method: 'PUT', body: data }),

  /** Active/désactive le mode absence. */
  updateAwayMode: (id: number, data: MerchantAwayModeUpdate): Promise<Merchant> =>
    $fetch<Merchant>(proxyUrl(`/merchants/${id}/away-mode`), { method: 'PUT', body: data }),
}
