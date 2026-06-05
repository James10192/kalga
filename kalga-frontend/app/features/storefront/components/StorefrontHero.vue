<!--
  Hero de vitrine marchand — bandeau forest deep avec logo + nom + description.
  Référence : design "Refined Heritage" (Stitch)
-->

<script setup lang="ts">
import { Store } from 'lucide-vue-next'

import type { StorefrontMerchant } from '@/features/storefront/types'

interface Props {
  merchant: StorefrontMerchant
}

defineProps<Props>()
</script>

<template>
  <section
    class="relative overflow-hidden bg-brand-deep text-brand-gold"
    :aria-label="merchant.business_name ?? ''"
  >
    <!-- Banner image en background, fallback gradient -->
    <div
      v-if="merchant.banner_url"
      class="absolute inset-0 -z-10"
      aria-hidden="true"
    >
      <img
        :src="merchant.banner_url"
        :alt="''"
        class="h-full w-full object-cover opacity-30"
        loading="eager"
      >
      <div class="absolute inset-0 bg-gradient-to-b from-brand-deep/70 to-brand-deep" />
    </div>

    <div class="mx-auto flex max-w-7xl flex-col items-center gap-4 px-4 py-16 text-center sm:px-6">
      <div
        v-if="merchant.logo_url"
        class="h-20 w-20 overflow-hidden rounded-full border-2 border-brand-gold/40 bg-brand-cream"
      >
        <img
          :src="merchant.logo_url"
          :alt="merchant.business_name ?? ''"
          class="h-full w-full object-cover"
        >
      </div>
      <div
        v-else
        class="inline-flex h-20 w-20 items-center justify-center rounded-full border-2 border-brand-gold/40 bg-brand-forest text-brand-gold"
      >
        <Store class="h-8 w-8" aria-hidden="true" />
      </div>

      <h1 class="font-serif text-3xl font-bold sm:text-4xl">
        {{ merchant.business_name ?? $t('storefront.unnamedShop') }}
      </h1>

      <p v-if="merchant.description" class="max-w-2xl text-sm text-brand-gold/80 sm:text-base">
        {{ merchant.description }}
      </p>
    </div>
  </section>
</template>
