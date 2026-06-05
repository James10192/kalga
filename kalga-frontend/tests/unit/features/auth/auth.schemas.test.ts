/**
 * Tests Vitest — Schémas Zod feature auth
 */

import { describe, expect, it } from 'vitest'

import {
  changePasswordInputSchema,
  forgotPasswordInputSchema,
  loginInputSchema,
  sessionUserSchema,
} from '../../../../app/features/auth/schemas'

describe('loginInputSchema', () => {
  it('accepte des credentials valides', () => {
    const result = loginInputSchema.safeParse({
      email: 'admin@kalga.com',
      password: 'monMotDePasse123',
    })
    expect(result.success).toBe(true)
  })

  it("rejette un email mal formé", () => {
    const result = loginInputSchema.safeParse({
      email: 'pas-un-email',
      password: 'monMotDePasse123',
    })
    expect(result.success).toBe(false)
  })

  it('rejette un mot de passe trop court', () => {
    const result = loginInputSchema.safeParse({
      email: 'admin@kalga.com',
      password: 'court',
    })
    expect(result.success).toBe(false)
  })

  it('rejette des champs manquants', () => {
    const result = loginInputSchema.safeParse({ email: 'admin@kalga.com' })
    expect(result.success).toBe(false)
  })
})

describe('forgotPasswordInputSchema', () => {
  it('accepte un email valide', () => {
    const result = forgotPasswordInputSchema.safeParse({ email: 'user@example.com' })
    expect(result.success).toBe(true)
  })

  it("rejette un email vide", () => {
    const result = forgotPasswordInputSchema.safeParse({ email: '' })
    expect(result.success).toBe(false)
  })
})

describe('changePasswordInputSchema', () => {
  it('accepte deux mots de passe identiques valides', () => {
    const result = changePasswordInputSchema.safeParse({
      current_password: 'ancien123',
      new_password: 'nouveauMotDePasse',
      confirm_password: 'nouveauMotDePasse',
    })
    expect(result.success).toBe(true)
  })

  it('rejette si new_password != confirm_password', () => {
    const result = changePasswordInputSchema.safeParse({
      current_password: 'ancien123',
      new_password: 'nouveauMotDePasse',
      confirm_password: 'different',
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0]?.path).toEqual(['confirm_password'])
    }
  })

  it('rejette si new_password trop court', () => {
    const result = changePasswordInputSchema.safeParse({
      current_password: 'ancien123',
      new_password: 'court',
      confirm_password: 'court',
    })
    expect(result.success).toBe(false)
  })
})

describe('sessionUserSchema', () => {
  it('accepte un admin valide', () => {
    const result = sessionUserSchema.safeParse({
      id: 1,
      email: 'admin@kalga.com',
      role: 'admin',
      is_active: true,
      merchant_id: null,
    })
    expect(result.success).toBe(true)
  })

  it('accepte un merchant valide', () => {
    const result = sessionUserSchema.safeParse({
      id: 2,
      email: 'merchant@kalga.com',
      role: 'merchant',
      is_active: true,
      merchant_id: 42,
    })
    expect(result.success).toBe(true)
  })

  it("rejette un rôle inconnu", () => {
    const result = sessionUserSchema.safeParse({
      id: 1,
      email: 'admin@kalga.com',
      role: 'superuser',
      is_active: true,
      merchant_id: null,
    })
    expect(result.success).toBe(false)
  })
})
