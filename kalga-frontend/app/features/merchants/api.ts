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
  /** Détail d'un marchand par ID (contexte admin). */
  getById: (id: number): Promise<Merchant> => $fetch<Merchant>(proxyUrl(`/merchants/${id}`)),

  /** Détail d'un marchand par téléphone (le marchand consulte son propre profil). */
  getByPhone: (phone: string): Promise<Merchant> =>
    $fetch<Merchant>(proxyUrl(`/merchants/${phone}`)),

  /** Liste paginée (admin). */
  list: (page = 1, search?: string): Promise<Paginated<Merchant>> =>
    $fetch<Paginated<Merchant>>(proxyUrl('/merchants'), { query: { page, search } }),

  /** Met à jour le profil (nom, business_name, vitrine : tagline/about). Backend : PUT /{id}. */
  updateProfile: (id: number, data: MerchantProfileUpdate): Promise<Merchant> =>
    $fetch<Merchant>(proxyUrl(`/merchants/${id}`), { method: 'PUT', body: data }),

  /**
   * Upload logo ou bannière (multipart). Passe par la route serveur dédiée
   * /api/merchant-upload/{id} (le proxy JSON ne gère pas le multipart).
   */
  uploadImage: (id: number, formData: FormData): Promise<{ success: boolean; url: string }> =>
    $fetch<{ success: boolean; url: string }>(`/api/merchant-upload/${id}`, {
      method: 'POST',
      body: formData,
    }),

  /** Met à jour la localisation (adresse + GPS). */
  updateLocation: (id: number, data: MerchantLocationUpdate): Promise<Merchant> =>
    $fetch<Merchant>(proxyUrl(`/merchants/${id}/location`), { method: 'PUT', body: data }),

  /** Met à jour la persona du bot IA. Backend : PUT /{id}/persona. */
  updateBotPersona: (id: number, data: MerchantBotPersonaUpdate): Promise<Merchant> =>
    $fetch<Merchant>(proxyUrl(`/merchants/${id}/persona`), { method: 'PUT', body: data }),

  /** Met à jour le mode absence. Backend : PUT /{phone}/away-settings (par téléphone). */
  updateAwayMode: (phone: string, data: MerchantAwayModeUpdate): Promise<Merchant> =>
    $fetch<Merchant>(proxyUrl(`/merchants/${phone}/away-settings`), { method: 'PUT', body: data }),
}
