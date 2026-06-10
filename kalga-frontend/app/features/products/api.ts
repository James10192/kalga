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
  /**
   * Liste les produits du marchand courant (paginé).
   * Le backend renvoie { products, total, page, limit, pages } — on le mappe
   * vers le contrat `Paginated<Product>` ({ items, per_page, total_pages }).
   */
  list: (merchantId: number, page = 1): Promise<Paginated<Product>> =>
    $fetch<{
      products: Product[]
      total: number
      page: number
      limit: number
      pages: number
    }>(proxyUrl(`/merchants/${merchantId}/products`), {
      query: { page },
    }).then((r) => ({
      items: r.products,
      total: r.total,
      page: r.page,
      per_page: r.limit,
      total_pages: r.pages,
    })),

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
