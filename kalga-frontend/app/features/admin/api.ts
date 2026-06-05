/**
 * Client API — feature `admin` (audit logs).
 * Référence : ARCHITECTURE_FRONTEND.md sections 7.2 + 9.4
 *
 * Backend correspondant : kalga-api/app/routers/admin.py
 */

import type { Paginated } from '@/types/api'
import type { AuditLogEntry } from '@/types/domain'

function proxyUrl(path: string): string {
  const config = useRuntimeConfig()
  const base = config.public.apiUrl.endsWith('/')
    ? config.public.apiUrl.slice(0, -1)
    : config.public.apiUrl
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

export const adminApi = {
  /** Journal d'audit paginé (action admin / changements sensibles). */
  listAuditLogs: (page = 1): Promise<Paginated<AuditLogEntry>> =>
    $fetch<Paginated<AuditLogEntry>>(proxyUrl('/admin/audit-logs'), { query: { page } }),
}
