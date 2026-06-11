<!--
  Grille de produits pour la vitrine — REGROUPÉE par variantes (group_id),
  comme le dashboard. Chaque groupe = une carte cliquable vers le détail.
-->

<script setup lang="ts">
import { groupProductsByVariant } from '@/features/products/utils/groupVariants'
import StorefrontProductCard from './StorefrontProductCard.vue'
import type { StorefrontProduct } from '../types'

interface Props {
  products: ReadonlyArray<StorefrontProduct>
}

const props = defineProps<Props>()

const groups = computed(() => groupProductsByVariant(props.products))
</script>

<template>
  <div
    class="grid gap-4 sm:gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
    :aria-label="$t('storefront.productsList')"
  >
    <StorefrontProductCard v-for="group in groups" :key="group.main.id" :group="group" />
  </div>
</template>
