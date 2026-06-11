/**
 * Client API — feature `storefront` (zone publique acheteur).
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 + 9.4
 *
 * Endpoints publics : pas d'auth requise, le proxy /api/proxy/* transmet sans JWT.
 * Backend correspondant : kalga-api/app/routers/storefront.py
 */

import type {
  StorefrontBoutique,
  StorefrontOrderInput,
  StorefrontProductDetail,
} from './types'

function proxyUrl(path: string): string {
  const config = useRuntimeConfig()
  const base = config.public.apiUrl.endsWith('/')
    ? config.public.apiUrl.slice(0, -1)
    : config.public.apiUrl
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

export const storefrontApi = {
  /**
   * Récupère la vitrine d'un marchand (marchand + produits) par téléphone.
   * Backend : GET /api/storefront/{phone}/products → { merchant, products }
   * (un seul appel, cf. storefront.js). NB : GET /{phone} ne renvoie PAS les
   * produits (juste product_count), d'où l'usage de /{phone}/products ici.
   */
  getMerchant: (phone: string): Promise<StorefrontBoutique> =>
    $fetch<StorefrontBoutique>(proxyUrl(`/storefront/${phone}/products`)),

  /**
   * Détail d'un produit public par code (#K001).
   * Backend : GET /api/storefront/product/{code} → { product, variants, merchant }.
   */
  getProduct: (code: string): Promise<StorefrontProductDetail> =>
    $fetch<StorefrontProductDetail>(proxyUrl(`/storefront/product/${code}`)),

  /**
   * Soumission d'une commande depuis la vitrine.
   * Backend : POST /api/storefront/order → { success, order_id, message }.
   */
  submitOrder: (
    data: StorefrontOrderInput,
  ): Promise<{ success: boolean; order_id: number; message: string }> =>
    $fetch(proxyUrl('/storefront/order'), {
      method: 'POST',
      body: data,
    }),
}
