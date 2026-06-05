/**
 * Schémas Zod — feature `storefront`
 *
 * Vitrine publique : produits affichés (sans min_price !) + commandes clients.
 * Aligné sur kalga-api/app/models/schemas.py (StorefrontProduct, StorefrontOrderCreate).
 */

import { z } from 'zod'

import {
  CLIENT_NAME_MAX_LEN,
  CLIENT_NAME_MIN_LEN,
  ORDER_MESSAGE_MAX_LEN,
  PHONE_DIGITS_ONLY_REGEX,
  PRICE_MIN,
  PRODUCT_CODE_REGEX,
} from '@/utils/constants'

// =============================================================================
// PRODUIT VITRINE
// =============================================================================

export const storefrontProductSchema = z.object({
  id: z.number().int().positive(),
  code: z.string().regex(PRODUCT_CODE_REGEX),
  name: z.string().min(1),
  description: z.string().nullable(),
  price: z.number().int().min(PRICE_MIN),
  image_url: z.string().nullable(),
  variant_name: z.string().nullable(),
  group_id: z.string().uuid().nullable(),
  in_stock: z.boolean(),
})

// =============================================================================
// VITRINE MARCHAND COMPLÈTE
// =============================================================================

export const storefrontMerchantSchema = z.object({
  merchant_phone: z.string().regex(PHONE_DIGITS_ONLY_REGEX),
  business_name: z.string().nullable(),
  banner_url: z.string().nullable(),
  logo_url: z.string().nullable(),
  description: z.string().nullable(),
  products: z.array(storefrontProductSchema),
})

// =============================================================================
// FORMULAIRE DE COMMANDE
// =============================================================================

export const storefrontOrderInputSchema = z.object({
  merchant_phone: z.string().regex(PHONE_DIGITS_ONLY_REGEX, 'Numéro marchand invalide'),
  product_code: z.string().regex(PRODUCT_CODE_REGEX),
  client_name: z
    .string()
    .min(CLIENT_NAME_MIN_LEN, `Nom : ${CLIENT_NAME_MIN_LEN} caractères minimum`)
    .max(CLIENT_NAME_MAX_LEN),
  client_phone: z
    .string()
    .regex(PHONE_DIGITS_ONLY_REGEX, 'Numéro invalide (10-15 chiffres, indicatif inclus)'),
  message: z
    .string()
    .max(ORDER_MESSAGE_MAX_LEN, `Message : ${ORDER_MESSAGE_MAX_LEN} caractères maximum`)
    .optional()
    .nullable(),
})
