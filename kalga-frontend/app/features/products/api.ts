/**
 * Client API — feature `products`.
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 (Data fetching) + 9.4
 *
 * Toutes les requêtes passent par le proxy `/api/proxy/*` qui :
 *  - Injecte la clé X-Internal-Key
 *  - Forward le JWT de la session HttpOnly
 *  - Renvoie le statut backend tel quel
 */

import type { Paginated } from '@/types/api'
import type { Product, ProductCreateInput, ProductUpdateInput } from './types'

/** Construit l'URL relative depuis le proxy public. */
function proxyUrl(path: string): string {
  const config = useRuntimeConfig()
  const base = config.public.apiUrl.endsWith('/')
    ? config.public.apiUrl.slice(0, -1)
    : config.public.apiUrl
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${base}${normalizedPath}`
}

export const productsApi = {
  /** Liste les produits du marchand courant (paginé). */
  list: (merchantId: number, page = 1): Promise<Paginated<Product>> =>
    $fetch<Paginated<Product>>(proxyUrl(`/merchants/${merchantId}/products`), {
      query: { page },
    }),

  /** Détail d'un produit par id. */
  getById: (id: number): Promise<Product> => $fetch<Product>(proxyUrl(`/products/${id}`)),

  /** Détail d'un produit par code (#K001). */
  getByCode: (code: string): Promise<Product> =>
    $fetch<Product>(proxyUrl(`/products/${code}`)),

  /** Liste des variantes (même group_id) d'un produit. */
  listVariants: (productId: number): Promise<Product[]> =>
    $fetch<Product[]>(proxyUrl(`/products/${productId}/variants`)),

  /** Crée un nouveau produit. */
  create: (merchantId: number, data: ProductCreateInput): Promise<Product> =>
    $fetch<Product>(proxyUrl(`/merchants/${merchantId}/products`), {
      method: 'POST',
      body: data,
    }),

  /** Met à jour un produit existant. */
  update: (id: number, data: ProductUpdateInput): Promise<Product> =>
    $fetch<Product>(proxyUrl(`/products/${id}`), {
      method: 'PUT',
      body: data,
    }),

  /** Supprime un produit. */
  remove: (id: number): Promise<{ deleted: boolean }> =>
    $fetch<{ deleted: boolean }>(proxyUrl(`/products/${id}`), {
      method: 'DELETE',
    }),
}
