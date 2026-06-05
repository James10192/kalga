/**
 * Plugin TanStack Query (Vue Query).
 * Référence : ARCHITECTURE_FRONTEND.md section 7.2 (Data fetching)
 *
 * Configure le QueryClient global utilisé par tous les `useQuery`/`useMutation`
 * des features.
 */

import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'

import { CACHE_STALE_TIME_DEFAULT } from '@/utils/constants'

export default defineNuxtPlugin((nuxtApp) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        // Considère la donnée fraîche pendant 1 min — évite les refetch inutiles.
        staleTime: CACHE_STALE_TIME_DEFAULT,
        // Pas de refetch automatique sur focus (UX moins agressive pour mobile).
        refetchOnWindowFocus: false,
        // 2 retries avec backoff exponentiel pour les requêtes idempotentes.
        retry: 2,
      },
      mutations: {
        // Pas de retry auto sur les mutations (effet de bord = ne pas répéter).
        retry: 0,
      },
    },
  })

  nuxtApp.vueApp.use(VueQueryPlugin, { queryClient })

  return {
    provide: {
      queryClient,
    },
  }
})
