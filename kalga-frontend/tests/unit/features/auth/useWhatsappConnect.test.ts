/**
 * Tests Vitest — features/auth/composables/useWhatsappConnect.ts
 *
 * Composable mutation minimal : on vérifie que la mutationFn relaie bien vers
 * la route serveur interne /api/whatsapp/connect (via authApi.connectWhatsapp).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@tanstack/vue-query', async () => (await import('../../helpers/tanstack')).tanstackMock)

import { fetchMock, resetTanstack, stubNuxtGlobals } from '../../helpers/tanstack'
import { useWhatsappConnect } from '../../../../app/features/auth/composables/useWhatsappConnect'

beforeEach(() => {
  resetTanstack()
  stubNuxtGlobals()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useWhatsappConnect', () => {
  it('la mutationFn poste le numéro sur /api/whatsapp/connect', async () => {
    const opts = useWhatsappConnect() as Record<string, any>
    await opts.mutationFn({ merchant_phone: '2250161407534' })

    expect(fetchMock).toHaveBeenCalledWith('/api/whatsapp/connect', {
      method: 'POST',
      body: { merchant_phone: '2250161407534' },
    })
  })
})
