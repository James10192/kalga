/**
 * Types inférés — feature `storefront`
 */

import type { z } from 'zod'

import type {
  storefrontMerchantSchema,
  storefrontOrderInputSchema,
  storefrontProductSchema,
} from './schemas'

export type StorefrontProduct = z.infer<typeof storefrontProductSchema>
export type StorefrontMerchant = z.infer<typeof storefrontMerchantSchema>
export type StorefrontOrderInput = z.infer<typeof storefrontOrderInputSchema>
