<!--
  Grille de produits pour la vitrine.
  Supporte le regroupement par variantes (group_id).
  V1 : affichage simple, sans regroupement (chaque variante = sa carte).
-->

<script setup lang="ts">
import StorefrontProductCard from './StorefrontProductCard.vue'
import type { StorefrontProduct } from '../types'

interface Props {
  products: ReadonlyArray<StorefrontProduct>
}

defineProps<Props>()
</script>

<template>
  <div
    class="grid gap-4 sm:gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
    :aria-label="$t('storefront.productsList')"
  >
    <StorefrontProductCard
      v-for="product in products"
      :key="product.id"
      :product="product"
    />
  </div>
</template>
