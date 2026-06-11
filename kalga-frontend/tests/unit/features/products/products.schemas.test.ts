/**
 * Tests Vitest — Schémas Zod feature products
 */

import { describe, expect, it } from 'vitest'

import {
  productCreateInputSchema,
  productSchema,
  storefrontProductSchema,
} from '../../../../app/features/products/schemas'

const validProductServer = {
  id: 1,
  merchant_id: 10,
  code: '#K001',
  name: 'Robe Wax',
  description: 'Belle robe',
  price: 25000,
  min_price: 20000,
  image_path: 'uploads/wax.jpg',
  group_id: '550e8400-e29b-41d4-a716-446655440000',
  variant_name: 'Rouge',
  stock_quantity: 10,
  low_stock_threshold: 2,
  out_of_stock_mode: 'waitlist' as const,
  is_available: true,
  created_at: '2026-06-01T10:00:00Z',
}

describe('productSchema (réponse serveur)', () => {
  it('accepte un produit complet valide', () => {
    const result = productSchema.safeParse(validProductServer)
    expect(result.success).toBe(true)
  })

  it("rejette un code au mauvais format", () => {
    const result = productSchema.safeParse({ ...validProductServer, code: 'K001' })
    expect(result.success).toBe(false)
  })

  it("rejette un code en minuscules", () => {
    const result = productSchema.safeParse({ ...validProductServer, code: '#k001' })
    expect(result.success).toBe(false)
  })

  it("rejette un prix négatif", () => {
    const result = productSchema.safeParse({ ...validProductServer, price: -100 })
    expect(result.success).toBe(false)
  })

  it("accepte description null", () => {
    const result = productSchema.safeParse({ ...validProductServer, description: null })
    expect(result.success).toBe(true)
  })
})

describe('productCreateInputSchema (form marchand)', () => {
  const validInput = {
    name: 'Robe Wax',
    description: null,
    price: 25000,
    min_price: 20000,
  }

  it('accepte un produit valide', () => {
    const result = productCreateInputSchema.safeParse(validInput)
    expect(result.success).toBe(true)
  })

  it('rejette si min_price > price (refinement)', () => {
    const result = productCreateInputSchema.safeParse({
      ...validInput,
      price: 20000,
      min_price: 25000,
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0]?.path).toEqual(['min_price'])
    }
  })

  it('accepte si min_price === price (deal serré mais valide)', () => {
    const result = productCreateInputSchema.safeParse({
      ...validInput,
      price: 25000,
      min_price: 25000,
    })
    expect(result.success).toBe(true)
  })

  it("rejette un nom trop court", () => {
    const result = productCreateInputSchema.safeParse({ ...validInput, name: 'A' })
    expect(result.success).toBe(false)
  })

  it("rejette un prix non entier", () => {
    const result = productCreateInputSchema.safeParse({ ...validInput, price: 250.5 })
    expect(result.success).toBe(false)
  })

  it("définit out_of_stock_mode à 'waitlist' par défaut", () => {
    const result = productCreateInputSchema.safeParse(validInput)
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.out_of_stock_mode).toBe('waitlist')
    }
  })
})

describe('storefrontProductSchema (vitrine publique)', () => {
  it('ne contient PAS min_price (sécurité)', () => {
    const inputAvecMinPrice = {
      id: 1,
      code: '#K001',
      name: 'Robe',
      description: null,
      price: 25000,
      min_price: 20000, // tentative d'injection
      image_url: null,
      variant_name: null,
      group_id: null,
      in_stock: true,
    }
    const result = storefrontProductSchema.safeParse(inputAvecMinPrice)
    expect(result.success).toBe(true)
    if (result.success) {
      expect('min_price' in result.data).toBe(false)
    }
  })
})
