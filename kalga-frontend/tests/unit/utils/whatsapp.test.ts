/**
 * Tests Vitest — utils/whatsapp.ts (fonction pure)
 */

import { describe, expect, it } from 'vitest'

import { buildWhatsAppLink } from '../../../app/utils/whatsapp'

describe('buildWhatsAppLink', () => {
  it('construit un lien wa.me à partir du numéro', () => {
    expect(buildWhatsAppLink('2250161407534')).toBe('https://wa.me/2250161407534')
  })

  it('nettoie les caractères non-chiffres du numéro', () => {
    expect(buildWhatsAppLink('+225 01-61-40-75-34')).toBe('https://wa.me/2250161407534')
  })

  it('ajoute le texte URL-encodé', () => {
    const link = buildWhatsAppLink('2250161407534', 'Bonjour #K001 !')
    expect(link).toBe('https://wa.me/2250161407534?text=Bonjour%20%23K001%20!')
  })

  it('retourne "#" si le numéro ne contient aucun chiffre', () => {
    expect(buildWhatsAppLink('abc')).toBe('#')
    expect(buildWhatsAppLink('')).toBe('#')
  })

  it('omet le paramètre text si non fourni ou vide', () => {
    expect(buildWhatsAppLink('2250161407534', '')).toBe('https://wa.me/2250161407534')
  })
})
