<!--
  Hero de vitrine marchand — bannière en fond (visible) + logo + nom + slogan.
  Référence : storefront/static/storefront.js (renderHero) + style.css (.store-hero).
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
    class="relative overflow-hidden bg-foreground text-warning"
    :aria-label="merchant.business_name ?? ''"
  >
    <!-- Bannière en fond (au-dessus du fond, visible) + voile pour la lisibilité -->
    <template v-if="merchant.banner_url">
      <img
        :src="merchant.banner_url"
        alt=""
        aria-hidden="true"
        class="absolute inset-0 h-full w-full object-cover"
        loading="eager"
      >
      <div
        class="absolute inset-0 bg-gradient-to-b from-foreground/45 via-foreground/40 to-foreground/80"
        aria-hidden="true"
      />
    </template>

    <div
      class="relative mx-auto flex max-w-7xl flex-col items-center gap-4 px-4 py-16 text-center sm:px-6"
    >
      <div
        v-if="merchant.logo_url"
        class="h-20 w-20 overflow-hidden rounded-full border-2 border-warning/60 bg-muted shadow-lg"
      >
        <img
          :src="merchant.logo_url"
          :alt="merchant.business_name ?? ''"
          class="h-full w-full object-cover"
        >
      </div>
      <div
        v-else
        class="inline-flex h-20 w-20 items-center justify-center rounded-full border-2 border-warning/60 bg-primary text-warning"
      >
        <Store class="h-8 w-8" aria-hidden="true" />
      </div>

      <h1 class="font-display text-3xl font-bold drop-shadow sm:text-4xl">
        {{ merchant.business_name ?? $t('storefront.unnamedShop') }}
      </h1>

      <p v-if="merchant.tagline" class="max-w-2xl text-sm text-warning/90 drop-shadow sm:text-base">
        {{ merchant.tagline }}
      </p>
    </div>
  </section>
</template>
