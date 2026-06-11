/**
 * Tests Vitest — composables/useToast.ts
 *
 * `useToast` dépend de l'auto-import Nuxt `useState`. On le mocke via
 * `vi.stubGlobal` avec une implémentation `ref`-backed (équivalent au state
 * partagé Nuxt côté test). `import.meta.client` est falsy en test → pas de
 * timer d'auto-dismiss à gérer.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import { useToast } from '../../../app/composables/useToast'

// Store partagé simulant le comportement singleton de Nuxt useState (par clé).
const stateStore = new Map<string, ReturnType<typeof ref>>()

beforeEach(() => {
  stateStore.clear()
  vi.stubGlobal('useState', (key: string, init: () => unknown) => {
    if (!stateStore.has(key)) {
      stateStore.set(key, ref(init()))
    }
    return stateStore.get(key)
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useToast', () => {
  it('push.success ajoute un toast de type success', () => {
    const { toasts, push } = useToast()
    const id = push.success('Produit créé')

    expect(toasts.value).toHaveLength(1)
    expect(toasts.value[0]).toMatchObject({ id, type: 'success', message: 'Produit créé' })
  })

  it('push.error et push.info posent le bon type', () => {
    const { toasts, push } = useToast()
    push.error('Échec')
    push.info('Info')

    expect(toasts.value.map((t) => t.type)).toEqual(['error', 'info'])
  })

  it('génère des id uniques', () => {
    const { push } = useToast()
    const id1 = push.success('a')
    const id2 = push.success('b')
    expect(id1).not.toBe(id2)
  })

  it('dismiss retire le toast par id', () => {
    const { toasts, push, dismiss } = useToast()
    const id = push.success('à fermer')
    expect(toasts.value).toHaveLength(1)

    dismiss(id)
    expect(toasts.value).toHaveLength(0)
  })

  it('dismiss sur un id inconnu ne casse rien', () => {
    const { toasts, push, dismiss } = useToast()
    push.success('garde-moi')
    dismiss('toast-inexistant')
    expect(toasts.value).toHaveLength(1)
  })

  it('plafonne la file à 5 toasts (pousse les plus anciens dehors)', () => {
    const { toasts, push } = useToast()
    for (let i = 1; i <= 7; i += 1) {
      push.info(`msg-${i}`)
    }
    expect(toasts.value).toHaveLength(5)
    // Les 2 plus anciens (msg-1, msg-2) ont été évincés.
    expect(toasts.value[0]?.message).toBe('msg-3')
    expect(toasts.value[4]?.message).toBe('msg-7')
  })

  it('partage le même state entre deux appels de useToast (singleton)', () => {
    const first = useToast()
    first.push.success('partagé')

    const second = useToast()
    expect(second.toasts.value).toHaveLength(1)
  })
})
