/**
 * Tests Vitest — Schémas Zod feature merchants
 */

import { describe, expect, it } from 'vitest'

import {
  merchantCreateInputSchema,
  merchantLocationUpdateSchema,
  merchantSchema,
} from '../../../../app/features/merchants/schemas'

const validMerchant = {
  id: 1,
  name: 'Aïcha Diabaté',
  phone: '2250161407534',
  business_name: 'Aïcha Mode',
  address: 'Cocody Riviera',
  city: 'Abidjan',
  commune: 'Cocody',
  quarter: 'Riviera',
  latitude: 5.349,
  longitude: -3.997,
  payment_info: null,
  payment_methods: null,
  bot_tone: 'friendly',
  bot_style: 'flexible',
  bot_catchphrase: null,
  away_mode_enabled: false,
  away_message: null,
  is_active: true,
  created_at: '2026-06-01T10:00:00Z',
}

describe('merchantSchema (réponse serveur)', () => {
  it('accepte un marchand valide', () => {
    const result = merchantSchema.safeParse(validMerchant)
    expect(result.success).toBe(true)
  })

  it("rejette une latitude > 90", () => {
    const result = merchantSchema.safeParse({ ...validMerchant, latitude: 200 })
    expect(result.success).toBe(false)
  })

  it("accepte latitude/longitude null", () => {
    const result = merchantSchema.safeParse({
      ...validMerchant,
      latitude: null,
      longitude: null,
    })
    expect(result.success).toBe(true)
  })
})

describe('merchantCreateInputSchema', () => {
  it('accepte une création minimale', () => {
    const result = merchantCreateInputSchema.safeParse({
      name: 'Aïcha',
      phone: '2250161407534',
    })
    expect(result.success).toBe(true)
  })

  it("rejette un nom trop court", () => {
    const result = merchantCreateInputSchema.safeParse({ name: 'A', phone: '2250161407534' })
    expect(result.success).toBe(false)
  })

  it("rejette un numéro avec lettres", () => {
    const result = merchantCreateInputSchema.safeParse({ name: 'Aïcha', phone: '225ABC123' })
    expect(result.success).toBe(false)
  })

  it("rejette un numéro trop court", () => {
    const result = merchantCreateInputSchema.safeParse({ name: 'Aïcha', phone: '123' })
    expect(result.success).toBe(false)
  })
})

describe('merchantLocationUpdateSchema (refinement lat/lng ensemble)', () => {
  it("accepte lat ET lng fournis", () => {
    const result = merchantLocationUpdateSchema.safeParse({
      latitude: 5.349,
      longitude: -3.997,
    })
    expect(result.success).toBe(true)
  })

  it("accepte address sans GPS", () => {
    const result = merchantLocationUpdateSchema.safeParse({ address: 'Cocody Riviera' })
    expect(result.success).toBe(true)
  })

  it("rejette lat sans lng", () => {
    const result = merchantLocationUpdateSchema.safeParse({ latitude: 5.349 })
    expect(result.success).toBe(false)
  })

  it("rejette lng sans lat", () => {
    const result = merchantLocationUpdateSchema.safeParse({ longitude: -3.997 })
    expect(result.success).toBe(false)
  })

  it("accepte un objet totalement vide", () => {
    const result = merchantLocationUpdateSchema.safeParse({})
    expect(result.success).toBe(true)
  })
})
