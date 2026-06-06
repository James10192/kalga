<!--
  État vide pour la liste de produits — CTA création.
  Référence : ARCHITECTURE_FRONTEND.md section 7.5
-->

<script setup lang="ts">
import { Package, Plus } from 'lucide-vue-next'

import { ROUTES } from '@/utils/routes'
</script>

<template>
  <div
    class="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card px-6 py-16 text-center"
  >
    <div
      class="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary"
    >
      <Package class="h-7 w-7" aria-hidden="true" />
    </div>

    <h2 class="font-display text-xl font-semibold text-primary">
      {{ $t('products.emptyTitle') }}
    </h2>
    <p class="mt-1 max-w-sm text-sm text-muted-foreground">
      {{ $t('products.emptyMessage') }}
    </p>

    <NuxtLink
      :to="ROUTES.dashboard.productNew"
      class="mt-6 inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-warning transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Plus class="h-4 w-4" aria-hidden="true" />
      {{ $t('products.createNew') }}
    </NuxtLink>
  </div>
</template>
