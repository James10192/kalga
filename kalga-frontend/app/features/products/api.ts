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
import type { Product, ProductCreateInput } from './types'

/** Statut de stock d'un produit (GET /products/{code}/stock). */
export interface ProductStock {
  product_code: string
  product_name: string
  quantity: number
  is_low: boolean
  is_out_of_stock: boolean
  is_unlimited: boolean
}

/** Corps de mise à jour du stock (PUT /products/{code}/stock). */
export interface StockUpdateInput {
  quantity: number
  low_stock_threshold?: number | null
}

/** Code produit sans le « # » de tête (le backend accepte les deux ; on évite
 *  d'encoder « # » à travers le proxy). */
function bareCode(code: string): string {
  return code.replace(/^#/, '')
}

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

  /**
   * Crée un produit. Backend : POST /api/products/ avec merchant_id dans le
   * corps, réponse { product }. (Il n'y a PAS de modification de produit côté
   * KALGA : on supprime et on recrée — cf. guide utilisateur.)
   */
  create: (merchantId: number, data: ProductCreateInput): Promise<Product> =>
    $fetch<{ product: Product }>(proxyUrl('/products/'), {
      method: 'POST',
      body: { ...data, merchant_id: merchantId },
    }).then((r) => r.product),

  /** Supprime (désactive) un produit. Backend : DELETE /{identifier} (accepte l'id). */
  remove: (id: number): Promise<{ success: boolean }> =>
    $fetch<{ success: boolean }>(proxyUrl(`/products/${id}`), {
      method: 'DELETE',
    }),

  /** Met à jour le stock d'un produit (par code). */
  updateStock: (code: string, data: StockUpdateInput): Promise<ProductStock> =>
    $fetch<ProductStock>(proxyUrl(`/products/${bareCode(code)}/stock`), {
      method: 'PUT',
      body: data,
    }),
}
