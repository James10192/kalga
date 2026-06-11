/**
 * Helper de test partagé pour les composables TanStack Query des features.
 *
 * - `tanstackMock` : module de remplacement de `@tanstack/vue-query` qui capture
 *   les options passées à `useQuery` / `useMutation` (pour inspecter queryKey,
 *   queryFn, onSuccess) et fournit un `useQueryClient` mockable.
 * - `stubNuxtGlobals()` : stub les auto-imports Nuxt utilisés par ces composables
 *   (`computed`, `unref` de Vue + `$fetch` + `useRuntimeConfig`).
 *
 * Usage dans un fichier de test :
 *   vi.mock('@tanstack/vue-query', async () =>
 *     (await import('../../helpers/tanstack')).tanstackMock)
 */

import { computed, unref } from 'vue'
import { vi } from 'vitest'

export const queryCalls: Array<Record<string, unknown>> = []
export const mutationCalls: Array<Record<string, unknown>> = []
export const invalidateQueries = vi.fn()
export const fetchMock = vi.fn().mockResolvedValue({ ok: true })

/** Module de remplacement de @tanstack/vue-query. */
export const tanstackMock = {
  useQuery: (opts: Record<string, unknown>) => {
    queryCalls.push(opts)
    return opts
  },
  useMutation: (opts: Record<string, unknown>) => {
    mutationCalls.push(opts)
    return opts
  },
  useQueryClient: () => ({ invalidateQueries }),
}

/** Stub des globals Nuxt/Vue requis par les composables (à appeler en beforeEach). */
export function stubNuxtGlobals(): void {
  vi.stubGlobal('computed', computed)
  vi.stubGlobal('unref', unref)
  vi.stubGlobal('$fetch', fetchMock)
  vi.stubGlobal('useRuntimeConfig', () => ({
    public: { apiUrl: '/api/proxy' },
    apiBackendUrl: 'http://backend.test',
    whatsappBridgeUrl: 'http://bridge.test',
  }))
}

/** Remet à zéro les captures entre deux tests. */
export function resetTanstack(): void {
  queryCalls.length = 0
  mutationCalls.length = 0
  invalidateQueries.mockClear()
  fetchMock.mockClear()
}
