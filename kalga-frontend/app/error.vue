<script setup lang="ts">
// Page d'erreur globale — capture tout ce qui n'est pas géré ailleurs.
// Référence : ARCHITECTURE_FRONTEND.md section 7.9 (error handling, niveau 1/3).

import type { NuxtError } from '#app'

interface Props {
  error: NuxtError
}

const props = defineProps<Props>()

const isNotFound = computed(() => props.error.statusCode === 404)

function handleReturnHome(): void {
  clearError({ redirect: '/' })
}
</script>

<template>
  <div class="flex min-h-screen flex-col items-center justify-center bg-background px-6 text-center">
    <div class="max-w-md space-y-6">
      <p class="text-7xl font-bold text-primary">
        {{ error.statusCode }}
      </p>

      <h1 class="text-2xl font-semibold text-foreground">
        {{ isNotFound ? $t('errors.notFoundTitle') : $t('errors.genericTitle') }}
      </h1>

      <p class="text-muted-foreground">
        {{ isNotFound ? $t('errors.notFoundMessage') : $t('errors.genericMessage') }}
      </p>

      <button
        type="button"
        class="inline-flex items-center justify-center rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-white transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        @click="handleReturnHome"
      >
        {{ $t('errors.backHome') }}
      </button>
    </div>
  </div>
</template>
