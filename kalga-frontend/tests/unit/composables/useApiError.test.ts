/**
 * Tests Vitest — composables/useApiError.ts
 *
 * `extractApiErrorMessage` est une fonction pure (pas de runtime Nuxt requis) :
 * on teste l'ordre de priorité des sources de message et les cas limites.
 */

import { describe, expect, it } from 'vitest'

import { extractApiErrorMessage } from '../../../app/composables/useApiError'

const FALLBACK = 'Une erreur est survenue'

describe('extractApiErrorMessage', () => {
  it('retourne le fallback pour null / undefined', () => {
    expect(extractApiErrorMessage(null, FALLBACK)).toBe(FALLBACK)
    expect(extractApiErrorMessage(undefined, FALLBACK)).toBe(FALLBACK)
  })

  it('retourne le fallback pour une valeur primitive (string, number)', () => {
    expect(extractApiErrorMessage('boom', FALLBACK)).toBe(FALLBACK)
    expect(extractApiErrorMessage(500, FALLBACK)).toBe(FALLBACK)
  })

  it('priorise data.detail (FastAPI) sur tout le reste', () => {
    const err = {
      data: { detail: 'Produit introuvable', message: 'ignored' },
      statusMessage: 'ignored',
      message: 'ignored',
    }
    expect(extractApiErrorMessage(err, FALLBACK)).toBe('Produit introuvable')
  })

  it('utilise statusMessage quand data.detail est absent', () => {
    const err = { statusMessage: 'Bad Gateway', message: 'ignored' }
    expect(extractApiErrorMessage(err, FALLBACK)).toBe('Bad Gateway')
  })

  it('utilise data.message quand detail et statusMessage sont absents', () => {
    const err = { data: { message: 'Champ invalide' }, message: 'ignored' }
    expect(extractApiErrorMessage(err, FALLBACK)).toBe('Champ invalide')
  })

  it('utilise message en avant-dernier recours', () => {
    const err = { message: 'Network Error' }
    expect(extractApiErrorMessage(err, FALLBACK)).toBe('Network Error')
  })

  it('retombe sur le fallback pour un objet sans champ de message', () => {
    expect(extractApiErrorMessage({ statusCode: 503 }, FALLBACK)).toBe(FALLBACK)
    expect(extractApiErrorMessage({}, FALLBACK)).toBe(FALLBACK)
  })
})
