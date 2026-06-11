/**
 * Types inférés — feature `storefront`
 */

import type { z } from 'zod'

import type {
  storefrontBoutiqueSchema,
  storefrontMerchantSchema,
  storefrontOrderInputSchema,
  storefrontProductDetailSchema,
  storefrontProductSchema,
} from './schemas'

export type StorefrontProduct = z.infer<typeof storefrontProductSchema>
export type StorefrontMerchant = z.infer<typeof storefrontMerchantSchema>
export type StorefrontOrderInput = z.infer<typeof storefrontOrderInputSchema>
export type StorefrontProductDetail = z.infer<typeof storefrontProductDetailSchema>
export type StorefrontBoutique = z.infer<typeof storefrontBoutiqueSchema>
