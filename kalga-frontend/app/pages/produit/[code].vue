<!--
  Page détail produit publique — /produit/:code.
  Référence : ARCHITECTURE_FRONTEND.md sections 3 (zone publique)
-->

<script setup lang="ts">
import { ArrowRight, ImageOff, Loader2 } from 'lucide-vue-next'

import WhatsAppButton from '@/features/storefront/components/WhatsAppButton.vue'
import { useStorefrontProduct } from '@/features/storefront/composables/useStorefront'
import { formatPriceFCFA } from '@/utils/format'
import { ROUTES } from '@/utils/routes'

const { t } = useI18n()
const route = useRoute()

const code = computed(() => {
  const raw = route.params.code
  return Array.isArray(raw) ? (raw[0] ?? '') : (raw ?? '')
})

const { data: product, isLoading, isError } = useStorefrontProduct(code)

useHead({
  title: () => product.value?.name ?? t('storefront.productFallback'),
})

const orderHref = computed(() =>
  product.value ? ROUTES.storefront.order(product.value.code) : '#',
)
</script>

<template>
  <div>
    <!-- Loading -->
    <div v-if="isLoading" class="flex min-h-[60vh] items-center justify-center">
      <Loader2 class="h-8 w-8 animate-spin text-muted-foreground" aria-hidden="true" />
    </div>

    <!-- Erreur -->
    <div
      v-else-if="isError || !product"
      role="alert"
      class="mx-auto max-w-2xl px-4 py-20 text-center sm:px-6"
    >
      <h1 class="font-serif text-2xl font-semibold text-brand-forest">
        {{ $t('storefront.productNotFound') }}
      </h1>
      <p class="mt-2 text-sm text-muted-foreground">
        {{ $t('storefront.productNotFoundMessage') }}
      </p>
    </div>

    <main
      v-else
      class="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-2 lg:py-16"
    >
      <!-- Image -->
      <div class="aspect-square w-full overflow-hidden rounded-lg bg-muted">
        <img
          v-if="product.image_url"
          :src="product.image_url"
          :alt="product.name"
          class="h-full w-full object-cover"
          loading="eager"
        >
        <div
          v-else
          class="flex h-full w-full items-center justify-center text-muted-foreground"
        >
          <ImageOff class="h-16 w-16" aria-hidden="true" />
        </div>
      </div>

      <!-- Détails -->
      <div class="space-y-6">
        <header class="space-y-2">
          <span
            class="inline-flex items-center rounded-md bg-brand-forest px-2 py-0.5 text-xs font-semibold uppercase tracking-wider text-brand-gold"
          >
            {{ product.code }}
          </span>
          <h1 class="font-serif text-3xl font-bold text-brand-forest sm:text-4xl">
            {{ product.name }}
          </h1>
          <p
            v-if="product.variant_name"
            class="text-xs uppercase tracking-wider text-muted-foreground"
          >
            {{ product.variant_name }}
          </p>
        </header>

        <p class="text-2xl font-semibold text-foreground">
          {{ formatPriceFCFA(product.price) }}
        </p>

        <p v-if="product.description" class="text-sm leading-relaxed text-muted-foreground">
          {{ product.description }}
        </p>

        <div
          v-if="!product.in_stock"
          role="alert"
          class="rounded-md border border-brand-gold/40 bg-brand-gold/10 px-3 py-2 text-sm text-brand-forest"
        >
          {{ $t('storefront.outOfStockNotice') }}
        </div>

        <div class="flex flex-col gap-3 pt-2 sm:flex-row">
          <NuxtLink
            :to="orderHref"
            class="inline-flex items-center justify-center gap-2 rounded-md bg-brand-forest px-5 py-3 text-sm font-semibold text-brand-gold transition hover:bg-brand-forest/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {{ $t('storefront.orderNow') }}
            <ArrowRight class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
        </div>
      </div>
    </main>
  </div>
</template>
