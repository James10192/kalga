/**
 * Types inférés — feature `merchants`
 */

import type { z } from 'zod'

import type {
  merchantAwayModeUpdateSchema,
  merchantBotPersonaUpdateSchema,
  merchantCreateInputSchema,
  merchantLocationUpdateSchema,
  merchantProfileUpdateSchema,
  merchantSchema,
} from './schemas'

export type Merchant = z.infer<typeof merchantSchema>
export type MerchantCreateInput = z.infer<typeof merchantCreateInputSchema>
export type MerchantProfileUpdate = z.infer<typeof merchantProfileUpdateSchema>
export type MerchantLocationUpdate = z.infer<typeof merchantLocationUpdateSchema>
export type MerchantBotPersonaUpdate = z.infer<typeof merchantBotPersonaUpdateSchema>
export type MerchantAwayModeUpdate = z.infer<typeof merchantAwayModeUpdateSchema>
