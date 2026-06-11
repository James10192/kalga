<!--
  Carte produit pour la vitrine publique — affiche un GROUPE de variantes.
  IMPORTANT : pas de min_price exposé (uniquement le prix de vente).

  Les variantes (group_id) sont regroupées en une seule carte (comme le
  dashboard) ; le client clique pour ouvrir le détail et voir chaque variante.
-->

<script setup lang="ts">
import { ImageOff, Layers } from 'lucide-vue-next'

import type { ProductGroup } from '@/features/products/utils/groupVariants'
import { formatPriceFCFA } from '@/utils/format'
import { ROUTES } from '@/utils/routes'
import type { StorefrontProduct } from '../types'

interface Props {
  group: ProductGroup<StorefrontProduct>
}

const props = defineProps<Props>()

const main = computed(() => props.group.main)
const variantCount = computed(() => props.group.variants.length)
const anyInStock = computed(() => props.group.variants.some((variant) => variant.in_stock))
const detailHref = computed(() => ROUTES.storefront.product(main.value.code))
</script>

<template>
  <article
    class="group flex flex-col overflow-hidden rounded-lg border border-border bg-card transition hover:border-primary/40 hover:shadow-md"
  >
    <NuxtLink
      :to="detailHref"
      class="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div class="relative aspect-square w-full overflow-hidden bg-muted">
        <img
          v-if="main.image_url"
          :src="main.image_url"
          :alt="group.displayName"
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
          v-if="variantCount > 1"
          class="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full bg-primary/90 px-2 py-0.5 text-xs font-semibold text-primary-foreground"
        >
          <Layers class="h-3 w-3" aria-hidden="true" />
          {{ $t('storefront.variantCount', { count: variantCount }) }}
        </span>

        <span
          v-if="!anyInStock"
          class="absolute right-3 top-3 rounded-full bg-destructive/90 px-2 py-0.5 text-xs font-semibold text-destructive-foreground"
        >
          {{ $t('storefront.outOfStock') }}
        </span>
      </div>

      <div class="space-y-1 p-4">
        <h3 class="line-clamp-1 font-display text-lg font-medium text-primary">
          {{ group.displayName }}
        </h3>
        <p class="pt-1 font-semibold text-foreground">
          {{ formatPriceFCFA(main.price) }}
        </p>
      </div>
    </NuxtLink>
  </article>
</template>
