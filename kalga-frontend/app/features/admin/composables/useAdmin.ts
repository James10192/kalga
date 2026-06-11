/**
 * Composables TanStack Query — feature `admin`.
 */

import { useQuery } from '@tanstack/vue-query'
import type { MaybeRef } from 'vue'

import { CACHE_STALE_TIME_DEFAULT } from '@/utils/constants'
import { adminApi } from '../api'

export const adminKeys = {
  dashboard: () => ['admin', 'dashboard'] as const,
  auditLogs: (page: number) => ['admin', 'audit-logs', page] as const,
}

/** Statistiques globales de la plateforme (overview admin). */
export function useAdminDashboard() {
  return useQuery({
    queryKey: adminKeys.dashboard(),
    queryFn: () => adminApi.getDashboard(),
    staleTime: CACHE_STALE_TIME_DEFAULT,
  })
}

export function useAuditLogs(page: MaybeRef<number>) {
  return useQuery({
    queryKey: computed(() => adminKeys.auditLogs(unref(page))),
    queryFn: () => adminApi.listAuditLogs(unref(page)),
    staleTime: CACHE_STALE_TIME_DEFAULT,
  })
}
