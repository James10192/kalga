/**
 * Types inférés — feature `products`
 * Référence : ARCHITECTURE_FRONTEND.md section 5.4 (SSOT)
 */

import type { z } from 'zod'

import type {
  productCreateInputSchema,
  productSchema,
  storefrontProductSchema,
} from './schemas'

export type Product = z.infer<typeof productSchema>
export type ProductCreateInput = z.infer<typeof productCreateInputSchema>
export type StorefrontProduct = z.infer<typeof storefrontProductSchema>
