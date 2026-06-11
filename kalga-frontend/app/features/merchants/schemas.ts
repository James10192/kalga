/**
 * Schémas Zod — feature `merchants`
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.4 + 10
 *
 * Aligné sur kalga-api/app/models/schemas.py (MerchantCreate / Merchant).
 */

import { z } from 'zod'

import {
  ADDRESS_MAX_LEN,
  AWAY_MESSAGE_MAX_LEN,
  BOT_CATCHPHRASE_MAX_LEN,
  BUSINESS_NAME_MAX_LEN,
  LATITUDE_MAX,
  LATITUDE_MIN,
  LONGITUDE_MAX,
  LONGITUDE_MIN,
  MERCHANT_NAME_MAX_LEN,
  MERCHANT_NAME_MIN_LEN,
  PHONE_DIGITS_ONLY_REGEX,
} from '@/utils/constants'

// =============================================================================
// MARCHAND — REPRÉSENTATION SERVEUR
// =============================================================================

export const merchantSchema = z.object({
  id: z.number().int().positive(),
  name: z.string().min(MERCHANT_NAME_MIN_LEN).max(MERCHANT_NAME_MAX_LEN),
  phone: z.string().regex(PHONE_DIGITS_ONLY_REGEX, 'Téléphone invalide'),
  business_name: z.string().max(BUSINESS_NAME_MAX_LEN).nullable(),
  address: z.string().max(ADDRESS_MAX_LEN).nullable(),
  city: z.string().nullable(),
  commune: z.string().nullable(),
  quarter: z.string().nullable(),
  latitude: z.number().min(LATITUDE_MIN).max(LATITUDE_MAX).nullable(),
  longitude: z.number().min(LONGITUDE_MIN).max(LONGITUDE_MAX).nullable(),
  payment_info: z.string().nullable(),
  payment_methods: z.string().nullable(),
  bot_tone: z.string().nullable(),
  bot_style: z.string().nullable(),
  bot_catchphrase: z.string().nullable(),
  away_mode_enabled: z.boolean(),
  away_message: z.string().nullable(),
  // Champs vitrine (Ma Vitrine)
  tagline: z.string().nullable().optional(),
  about: z.string().nullable().optional(),
  logo_path: z.string().nullable().optional(),
  banner_path: z.string().nullable().optional(),
  is_active: z.boolean(),
  created_at: z.string().datetime(),
})

// =============================================================================
// INPUTS
// =============================================================================

/** Création marchand (admin uniquement) */
export const merchantCreateInputSchema = z.object({
  name: z
    .string()
    .min(MERCHANT_NAME_MIN_LEN, `Nom : ${MERCHANT_NAME_MIN_LEN} caractères minimum`)
    .max(MERCHANT_NAME_MAX_LEN),
  phone: z
    .string()
    .regex(PHONE_DIGITS_ONLY_REGEX, 'Numéro invalide (10-15 chiffres, indicatif inclus)'),
  business_name: z.string().max(BUSINESS_NAME_MAX_LEN).optional().nullable(),
})

/** Édition profil marchand (inclut les champs vitrine : tagline, about). */
export const merchantProfileUpdateSchema = z.object({
  name: z.string().min(MERCHANT_NAME_MIN_LEN).max(MERCHANT_NAME_MAX_LEN).optional(),
  business_name: z.string().max(BUSINESS_NAME_MAX_LEN).nullable().optional(),
  payment_info: z.string().nullable().optional(),
  payment_methods: z.string().nullable().optional(),
  tagline: z.string().max(120).nullable().optional(),
  about: z.string().max(500).nullable().optional(),
})

/** Configuration localisation marchand */
export const merchantLocationUpdateSchema = z
  .object({
    address: z.string().max(ADDRESS_MAX_LEN).nullable().optional(),
    city: z.string().nullable().optional(),
    commune: z.string().nullable().optional(),
    quarter: z.string().nullable().optional(),
    latitude: z.number().min(LATITUDE_MIN).max(LATITUDE_MAX).nullable().optional(),
    longitude: z.number().min(LONGITUDE_MIN).max(LONGITUDE_MAX).nullable().optional(),
  })
  .refine(
    (data) => {
      // Si latitude est défini, longitude doit l'être aussi (et inversement)
      const hasLat = data.latitude !== null && data.latitude !== undefined
      const hasLng = data.longitude !== null && data.longitude !== undefined
      return hasLat === hasLng
    },
    { message: 'latitude et longitude doivent être fournis ensemble' },
  )

/** Configuration de la persona IA du marchand */
export const merchantBotPersonaUpdateSchema = z.object({
  bot_tone: z.enum(['casual', 'formal', 'friendly']).nullable().optional(),
  bot_style: z.enum(['flexible', 'firm', 'aggressive']).nullable().optional(),
  bot_catchphrase: z.string().max(BOT_CATCHPHRASE_MAX_LEN).nullable().optional(),
})

/** Mode absence */
export const merchantAwayModeUpdateSchema = z.object({
  away_mode_enabled: z.boolean(),
  away_message: z.string().max(AWAY_MESSAGE_MAX_LEN).nullable().optional(),
})
