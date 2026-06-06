/**
 * Tests Vitest — features/admin/composables/useAdmin.ts
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@tanstack/vue-query', async () => (await import('../../helpers/tanstack')).tanstackMock)

import { fetchMock, resetTanstack, stubNuxtGlobals } from '../../helpers/tanstack'
import { adminKeys, useAuditLogs } from '../../../../app/features/admin/composables/useAdmin'

beforeEach(() => {
  resetTanstack()
  stubNuxtGlobals()
})
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('adminKeys', () => {
  it('génère la clé des audit logs paginés', () => {
    expect(adminKeys.auditLogs(3)).toEqual(['admin', 'audit-logs', 3])
  })
})

describe('useAuditLogs', () => {
  it('câble la clé paginée et la queryFn appelle l’API', async () => {
    const opts = useAuditLogs(3) as Record<string, any>
    expect(opts.queryKey.value).toEqual(['admin', 'audit-logs', 3])
    await opts.queryFn()
    expect(fetchMock).toHaveBeenCalledOnce()
  })
})
