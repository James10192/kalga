/**
 * Tests Vitest — features/storefront/schemas.ts
 *
 * Verrouille les schémas sur les réponses RÉELLES du backend
 * (kalga-api/app/routers/storefront.py : _merchant_to_storefront,
 * get_product_detail, get_merchant_products). Garde-fou anti-dérive : si le
 * backend ou le port change le shape, ces tests cassent.
 */

import { describe, expect, it } from 'vitest'

import {
  storefrontBoutiqueSchema,
  storefrontMerchantSchema,
  storefrontProductDetailSchema,
  storefrontProductSchema,
} from '../../../../app/features/storefront/schemas'

// Fixtures alignées sur _product_to_storefront / _merchant_to_storefront.
const product = {
  id: 1,
  code: '#K001',
  name: 'Sac tissé',
  description: 'Fait main',
  price: 25000,
  image_url: '/uploads/k001.jpg',
  variant_name: null,
  group_id: null,
  in_stock: true,
}

const merchant = {
  name: 'Awa',
  business_name: 'Awa Boutique',
  phone: '2250161407534',
  address: 'Abidjan',
  logo_url: '/uploads/logo.jpg',
  banner_url: null,
  about: null,
  tagline: 'Le meilleur du tissu',
}

describe('storefrontProductSchema', () => {
  it('accepte un produit vitrine valide', () => {
    expect(storefrontProductSchema.safeParse(product).success).toBe(true)
  })

  it('rejette un code produit hors format #K000', () => {
    expect(storefrontProductSchema.safeParse({ ...product, code: 'K001' }).success).toBe(false)
  })

  it('rejette l’absence de min_price… qui ne doit PAS exister (vitrine publique)', () => {
    // min_price ne fait pas partie du schéma vitrine : un champ en trop est ignoré,
    // mais le prix reste requis et entier.
    expect(storefrontProductSchema.safeParse({ ...product, price: -1 }).success).toBe(false)
  })
})

describe('storefrontMerchantSchema (_merchant_to_storefront)', () => {
  it('accepte un marchand public valide (champ `phone`, nullables tolérés)', () => {
    expect(storefrontMerchantSchema.safeParse(merchant).success).toBe(true)
  })

  it('rejette un téléphone marchand invalide', () => {
    expect(storefrontMerchantSchema.safeParse({ ...merchant, phone: 'abc' }).success).toBe(false)
  })
})

describe('storefrontProductDetailSchema (GET /product/{code})', () => {
  it('accepte { product, variants, merchant }', () => {
    const payload = { product, variants: [product], merchant }
    expect(storefrontProductDetailSchema.safeParse(payload).success).toBe(true)
  })

  it('accepte des variants vides', () => {
    const payload = { product, variants: [], merchant }
    expect(storefrontProductDetailSchema.safeParse(payload).success).toBe(true)
  })
})

describe('storefrontBoutiqueSchema (GET /{phone}/products)', () => {
  it('accepte { merchant, products }', () => {
    const payload = { merchant, products: [product, { ...product, id: 2, code: '#K002' }] }
    expect(storefrontBoutiqueSchema.safeParse(payload).success).toBe(true)
  })

  it('accepte une boutique sans produits', () => {
    expect(storefrontBoutiqueSchema.safeParse({ merchant, products: [] }).success).toBe(true)
  })
})
