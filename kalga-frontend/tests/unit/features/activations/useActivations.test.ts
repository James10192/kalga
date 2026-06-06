/**
 * Tests Vitest — features/activations/composables/useActivations.ts
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@tanstack/vue-query', async () => (await import('../../helpers/tanstack')).tanstackMock)

import {
  fetchMock,
  invalidateQueries,
  resetTanstack,
  stubNuxtGlobals,
} from '../../helpers/tanstack'
import {
  activationsKeys,
  useActivationsList,
  usePendingActivations,
  useSendActivationCode,
} from '../../../../app/features/activations/composables/useActivations'

beforeEach(() => {
  resetTanstack()
  stubNuxtGlobals()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('activationsKeys', () => {
  it('génère les clés, status par défaut "all"', () => {
    expect(activationsKeys.all).toEqual(['activations'])
    expect(activationsKeys.list(2, 'pending')).toEqual(['activations', 'list', 2, 'pending'])
    expect(activationsKeys.list(1, undefined)).toEqual(['activations', 'list', 1, 'all'])
    expect(activationsKeys.pending()).toEqual(['activations', 'pending'])
  })
})

describe('queries activations', () => {
  it('useActivationsList câble la clé et appelle l’API', async () => {
    const opts = useActivationsList(2, 'pending') as Record<string, any>
    expect(opts.queryKey.value).toEqual(['activations', 'list', 2, 'pending'])
    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()
  })

  it('usePendingActivations a une clé statique', async () => {
    const opts = usePendingActivations() as Record<string, any>
    expect(opts.queryKey).toEqual(['activations', 'pending'])
    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()
  })
})

describe('useSendActivationCode', () => {
  it('envoie le code et invalide les activations au succès', async () => {
    const opts = useSendActivationCode() as Record<string, any>
    await opts.mutationFn({ merchant_id: 1 })
    expect(fetchMock).toHaveBeenCalledOnce()
    opts.onSuccess()
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['activations'] })
  })
})
