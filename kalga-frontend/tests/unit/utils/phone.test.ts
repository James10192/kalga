/**
 * Tests Vitest — utils/phone.ts
 * Couvre la normalisation qui a causé le 404 marchand (0 de tête non retiré).
 */

import { describe, expect, it } from 'vitest'

import { buildInternationalPhone } from '../../../app/utils/phone'

describe('buildInternationalPhone', () => {
  it('retire le 0 de tête du numéro local (cas du bug 404)', () => {
    expect(buildInternationalPhone('225', '0544210112')).toBe('225544210112')
  })

  it('ignore espaces, tirets et parenthèses', () => {
    expect(buildInternationalPhone('225', '05 44 21 01 12')).toBe('225544210112')
    expect(buildInternationalPhone('225', '(05)-44-21-01-12')).toBe('225544210112')
  })

  it('laisse intact un local déjà sans 0 de tête', () => {
    expect(buildInternationalPhone('225', '544210112')).toBe('225544210112')
  })

  it('retire plusieurs 0 de tête', () => {
    expect(buildInternationalPhone('33', '00612345678')).toBe('33612345678')
  })

  it('gère un numéro local vide', () => {
    expect(buildInternationalPhone('225', '')).toBe('225')
  })
})
