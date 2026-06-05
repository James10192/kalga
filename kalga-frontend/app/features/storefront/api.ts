/**
 * Client API — feature `storefront` (zone publique acheteur).
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 + 9.4
 *
 * Endpoints publics : pas d'auth requise, le proxy /api/proxy/* transmet sans JWT.
 * Backend correspondant : kalga-api/app/routers/storefront.py
 */

import type {
  StorefrontMerchant,
  StorefrontOrderInput,
  StorefrontProduct,
} from './types'

function proxyUrl(path: string): string {
  const config = useRuntimeConfig()
  const base = config.public.apiUrl.endsWith('/')
    ? config.public.apiUrl.slice(0, -1)
    : config.public.apiUrl
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

export const storefrontApi = {
  /** Récupère la vitrine d'un marchand par son téléphone. */
  getMerchant: (phone: string): Promise<StorefrontMerchant> =>
    $fetch<StorefrontMerchant>(proxyUrl(`/storefront/${phone}`)),

  /** Détail d'un produit public par code (#K001). */
  getProduct: (code: string): Promise<StorefrontProduct> =>
    $fetch<StorefrontProduct>(proxyUrl(`/storefront/products/${code}`)),

  /** Soumission d'une commande depuis la vitrine. */
  submitOrder: (data: StorefrontOrderInput): Promise<{ sent: boolean }> =>
    $fetch<{ sent: boolean }>(proxyUrl('/storefront/orders'), {
      method: 'POST',
      body: data,
    }),
}
