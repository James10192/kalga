<!--
  Vitrine d'un marchand — /boutique/:phone.
  Référence : ARCHITECTURE_FRONTEND.md sections 3 (zone publique)
-->

<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

import StorefrontHero from '@/features/storefront/components/StorefrontHero.vue'
import StorefrontProductGrid from '@/features/storefront/components/StorefrontProductGrid.vue'
import { useStorefrontMerchant } from '@/features/storefront/composables/useStorefront'

const { t } = useI18n()
const route = useRoute()

const phone = computed(() => {
  const raw = route.params.phone
  return Array.isArray(raw) ? (raw[0] ?? '') : (raw ?? '')
})

// Le endpoint renvoie { merchant, products }.
const { data: storefront, isLoading, isError } = useStorefrontMerchant(phone)

useHead({
  title: () => storefront.value?.merchant.business_name ?? t('storefront.shopFallback'),
})
</script>

<template>
  <div>
    <!-- Loading -->
    <div
      v-if="isLoading"
      class="flex min-h-[60vh] items-center justify-center"
    >
      <Loader2 class="h-8 w-8 animate-spin text-muted-foreground" aria-hidden="true" />
    </div>

    <!-- Erreur -->
    <div
      v-else-if="isError || !storefront"
      role="alert"
      class="mx-auto max-w-2xl px-4 py-20 text-center sm:px-6"
    >
      <h1 class="font-display text-2xl font-semibold text-primary">
        {{ $t('storefront.shopNotFound') }}
      </h1>
      <p class="mt-2 text-sm text-muted-foreground">
        {{ $t('storefront.shopNotFoundMessage') }}
      </p>
    </div>

    <template v-else>
      <StorefrontHero :merchant="storefront.merchant" />

      <main class="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <h2 class="mb-6 font-display text-2xl font-semibold text-primary">
          {{ $t('storefront.ourProducts') }}
        </h2>

        <div
          v-if="storefront.products.length === 0"
          class="rounded-lg border border-dashed border-border bg-card py-12 text-center text-sm text-muted-foreground"
        >
          {{ $t('storefront.noProductsYet') }}
        </div>

        <StorefrontProductGrid v-else :products="storefront.products" />
      </main>
    </template>
  </div>
</template>
