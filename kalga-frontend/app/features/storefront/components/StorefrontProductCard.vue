<!--
  Carte produit pour la vitrine publique.
  IMPORTANT : pas de min_price exposé (uniquement le prix de vente).
-->

<script setup lang="ts">
import { ImageOff } from 'lucide-vue-next'

import { formatPriceFCFA } from '@/utils/format'
import { ROUTES } from '@/utils/routes'
import type { StorefrontProduct } from '../types'

interface Props {
  product: StorefrontProduct
}

const props = defineProps<Props>()

const detailHref = computed(() => ROUTES.storefront.product(props.product.code))
</script>

<template>
  <article
    class="group flex flex-col overflow-hidden rounded-lg border border-border bg-card transition hover:border-brand-forest/40 hover:shadow-md"
  >
    <NuxtLink
      :to="detailHref"
      class="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div class="relative aspect-square w-full overflow-hidden bg-muted">
        <img
          v-if="product.image_url"
          :src="product.image_url"
          :alt="product.name"
          class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
          loading="lazy"
        >
        <div
          v-else
          class="flex h-full w-full items-center justify-center text-muted-foreground"
        >
          <ImageOff class="h-10 w-10" aria-hidden="true" />
        </div>

        <span
          v-if="!product.in_stock"
          class="absolute right-3 top-3 rounded-full bg-destructive/90 px-2 py-0.5 text-xs font-semibold text-destructive-foreground"
        >
          {{ $t('storefront.outOfStock') }}
        </span>
      </div>

      <div class="space-y-1 p-4">
        <p
          v-if="product.variant_name"
          class="text-xs uppercase tracking-wider text-muted-foreground"
        >
          {{ product.variant_name }}
        </p>
        <h3 class="line-clamp-1 font-serif text-lg font-medium text-brand-forest">
          {{ product.name }}
        </h3>
        <p class="pt-1 font-semibold text-foreground">
          {{ formatPriceFCFA(product.price) }}
        </p>
      </div>
    </NuxtLink>
  </article>
</template>
