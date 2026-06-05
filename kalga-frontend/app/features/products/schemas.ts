/**
 * Schémas Zod — feature `products`
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.4 + 10 (validation)
 *
 * Aligné sur kalga-api/app/models/schemas.py (ProductCreate / Product).
 */

import { z } from 'zod'

import {
  PRICE_MAX,
  PRICE_MIN,
  PRODUCT_CODE_REGEX,
  PRODUCT_DESCRIPTION_MAX_LEN,
  PRODUCT_NAME_MAX_LEN,
  PRODUCT_NAME_MIN_LEN,
  VARIANT_NAME_MAX_LEN,
} from '@/utils/constants'

// =============================================================================
// REPRÉSENTATION SERVEUR
// =============================================================================

/** Schéma d'un produit tel que renvoyé par l'API */
export const productSchema = z.object({
  id: z.number().int().positive(),
  merchant_id: z.number().int().positive(),
  code: z.string().regex(PRODUCT_CODE_REGEX, 'Code invalide (format attendu : #K001)'),
  name: z.string().min(PRODUCT_NAME_MIN_LEN).max(PRODUCT_NAME_MAX_LEN),
  description: z.string().max(PRODUCT_DESCRIPTION_MAX_LEN).nullable(),
  price: z.number().int().min(PRICE_MIN).max(PRICE_MAX),
  min_price: z.number().int().min(PRICE_MIN).max(PRICE_MAX),
  image_path: z.string().nullable(),
  group_id: z.string().uuid().nullable(),
  variant_name: z.string().max(VARIANT_NAME_MAX_LEN).nullable(),
  stock_quantity: z.number().int().min(0).nullable(),
  low_stock_threshold: z.number().int().min(0).nullable(),
  out_of_stock_mode: z.enum(['waitlist', 'suspend']),
  is_available: z.boolean(),
  created_at: z.string().datetime(),
})

// =============================================================================
// INPUTS — création / édition
// =============================================================================

/** Form de création produit (par le marchand) */
export const productCreateInputSchema = z
  .object({
    name: z
      .string()
      .min(PRODUCT_NAME_MIN_LEN, `Nom : ${PRODUCT_NAME_MIN_LEN} caractères minimum`)
      .max(PRODUCT_NAME_MAX_LEN, `Nom : ${PRODUCT_NAME_MAX_LEN} caractères maximum`),
    description: z.string().max(PRODUCT_DESCRIPTION_MAX_LEN).optional().nullable(),
    price: z
      .number({ message: 'Prix requis' })
      .int('Le prix doit être un entier')
      .min(PRICE_MIN, `Prix minimum : ${PRICE_MIN} F CFA`)
      .max(PRICE_MAX, `Prix maximum : ${PRICE_MAX} F CFA`),
    min_price: z
      .number({ message: 'Prix minimum requis' })
      .int('Le prix minimum doit être un entier')
      .min(PRICE_MIN)
      .max(PRICE_MAX),
    image_path: z.string().optional().nullable(),
    group_id: z.string().uuid().optional().nullable(),
    variant_name: z.string().max(VARIANT_NAME_MAX_LEN).optional().nullable(),
    stock_quantity: z.number().int().min(0).optional().nullable(),
    low_stock_threshold: z.number().int().min(0).optional().nullable(),
    out_of_stock_mode: z.enum(['waitlist', 'suspend']).default('waitlist'),
  })
  .refine((data) => data.min_price <= data.price, {
    path: ['min_price'],
    message: 'Le prix minimum doit être inférieur ou égal au prix de vente',
  })

/** Form d'édition produit — tous les champs optionnels sauf validation prix */
export const productUpdateInputSchema = productCreateInputSchema.partial()

// =============================================================================
// PRODUIT VITRINE PUBLIQUE (sans min_price !)
// =============================================================================

export const storefrontProductSchema = z.object({
  id: z.number().int().positive(),
  code: z.string().regex(PRODUCT_CODE_REGEX),
  name: z.string(),
  description: z.string().nullable(),
  price: z.number().int().positive(),
  image_url: z.string().nullable(),
  variant_name: z.string().nullable(),
  group_id: z.string().uuid().nullable(),
  in_stock: z.boolean(),
})
