<!--
  Carte produit — affichage dans la liste.
  Référence : ARCHITECTURE_FRONTEND.md sections 7.5 + features/products
-->

<script setup lang="ts">
import { ImageOff } from 'lucide-vue-next'

import { formatPriceFCFA, truncate } from '@/utils/format'
import { ROUTES } from '@/utils/routes'
import type { Product } from '../types'

interface Props {
  product: Product
}

const props = defineProps<Props>()

const detailHref = computed(() => ROUTES.dashboard.productDetail(props.product.id))

const imageSrc = computed<string | null>(() => {
  const path = props.product.image_path
  if (!path) return null
  // `image_path` = nom de fichier nu côté dashboard. Les images sont servies par
  // le backend sous /uploads/ et relayées par server/routes/uploads/[...path].ts.
  return path.startsWith('/uploads/') ? path : `/uploads/${path}`
})
</script>

<template>
  <article
    class="group flex flex-col overflow-hidden rounded-lg border border-border bg-card transition hover:border-primary/40 hover:shadow-sm"
  >
    <NuxtLink
      :to="detailHref"
      class="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div class="relative aspect-square w-full overflow-hidden bg-muted">
        <img
          v-if="imageSrc"
          :src="imageSrc"
          :alt="product.name"
          class="h-full w-full object-cover transition group-hover:scale-105"
          loading="lazy"
        >
        <div
          v-else
          class="flex h-full w-full items-center justify-center text-muted-foreground"
          :aria-label="$t('products.noImage')"
        >
          <ImageOff class="h-10 w-10" aria-hidden="true" />
        </div>

        <span
          class="absolute left-2 top-2 rounded-md bg-primary px-2 py-0.5 text-xs font-semibold text-warning"
        >
          {{ product.code }}
        </span>
      </div>

      <div class="space-y-2 p-4">
        <h3 class="line-clamp-1 font-medium text-foreground">{{ product.name }}</h3>

        <p v-if="product.description" class="line-clamp-2 text-xs text-muted-foreground">
          {{ truncate(product.description, 100) }}
        </p>

        <div class="flex items-center justify-between pt-1">
          <span class="font-semibold text-primary">
            {{ formatPriceFCFA(product.price) }}
          </span>

          <StockBadge
            :quantity="product.stock_quantity"
            :low-threshold="product.low_stock_threshold"
          />
        </div>
      </div>
    </NuxtLink>
  </article>
</template>
