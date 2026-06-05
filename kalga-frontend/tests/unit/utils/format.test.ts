/**
 * Tests Vitest — utils/format.ts
 */

import { describe, expect, it } from 'vitest'

import {
  formatDate,
  formatDateTime,
  formatPhone,
  formatPriceFCFA,
  initialsFrom,
  truncate,
} from '../../../app/utils/format'

describe('formatPriceFCFA', () => {
  it('formate un prix simple', () => {
    expect(formatPriceFCFA(25000)).toContain('25')
    expect(formatPriceFCFA(25000)).toContain('000')
    expect(formatPriceFCFA(25000).endsWith(' F')).toBe(true)
  })

  it('gère le zéro', () => {
    expect(formatPriceFCFA(0)).toBe('0 F')
  })

  it('tronque les décimales', () => {
    expect(formatPriceFCFA(25000.99)).not.toContain('.99')
  })

  it('gère les nombres invalides (NaN, Infinity)', () => {
    expect(formatPriceFCFA(Number.NaN)).toBe('0 F')
    expect(formatPriceFCFA(Number.POSITIVE_INFINITY)).toBe('0 F')
  })

  it('formate les grands montants', () => {
    const result = formatPriceFCFA(1_500_000)
    expect(result).toContain('1')
    expect(result).toContain('500')
    expect(result).toContain('000')
  })
})

describe('formatDate', () => {
  it('formate une date ISO valide', () => {
    const result = formatDate('2026-06-04T10:00:00Z', 'fr-FR')
    expect(result).toContain('2026')
    expect(result.length).toBeGreaterThan(0)
  })

  it('retourne une chaîne vide pour une date invalide', () => {
    expect(formatDate('not-a-date')).toBe('')
  })
})

describe('formatDateTime', () => {
  it('inclut une heure dans le résultat', () => {
    const result = formatDateTime('2026-06-04T10:30:00Z', 'fr-FR')
    expect(result).toMatch(/\d{2}:\d{2}/)
  })

  it('retourne une chaîne vide pour une date invalide', () => {
    expect(formatDateTime('')).toBe('')
  })
})

describe('formatPhone', () => {
  it('formate un numéro ivoirien avec indicatif 225', () => {
    expect(formatPhone('2250161407534')).toBe('+225 01 61 40 75 34')
  })

  it('formate un numéro français avec indicatif 33', () => {
    expect(formatPhone('33612345678')).toBe('+33 06 12 34 56 78')
  })

  it('retourne le numéro tel quel si trop court', () => {
    expect(formatPhone('123')).toBe('123')
  })

  it('retourne une chaîne vide pour input vide', () => {
    expect(formatPhone('')).toBe('')
  })

  it('ignore les caractères non-chiffres', () => {
    expect(formatPhone('+225-01-61-40-75-34')).toBe('+225 01 61 40 75 34')
  })
})

describe('truncate', () => {
  it("ne tronque pas si plus court", () => {
    expect(truncate('Hello', 10)).toBe('Hello')
  })

  it("tronque avec ellipsis", () => {
    expect(truncate('Hello world', 5)).toBe('Hell…')
  })

  it("gère maxLen 0", () => {
    expect(truncate('Hello', 0)).toBe('…')
  })
})

describe('initialsFrom', () => {
  it("extrait les initiales d'un nom complet", () => {
    expect(initialsFrom('Aïcha Diabaté')).toBe('AD')
  })

  it("extrait l'initiale d'un nom simple", () => {
    expect(initialsFrom('Aicha')).toBe('A')
  })

  it("extrait de la partie locale d'un email", () => {
    expect(initialsFrom('admin@kalga.com')).toBe('A')
  })

  it("limite à 2 initiales", () => {
    expect(initialsFrom('Jean Marie Pierre Paul')).toBe('JM')
  })

  it("gère null/undefined", () => {
    expect(initialsFrom(null)).toBe('?')
    expect(initialsFrom(undefined)).toBe('?')
    expect(initialsFrom('')).toBe('?')
  })

  it("gère un séparateur point", () => {
    expect(initialsFrom('aicha.diabate')).toBe('AD')
  })
})
