<!--
  Liste paginée des produits du marchand.
  Référence : ARCHITECTURE_FRONTEND.md sections 3 + 9.1 (workflow feature)
-->

<script setup lang="ts">
import { ChevronLeft, ChevronRight, Loader2, Plus } from 'lucide-vue-next'

import ProductCard from '@/features/products/components/ProductCard.vue'
import ProductEmptyState from '@/features/products/components/ProductEmptyState.vue'
import { useProductsList } from '@/features/products/composables/useProducts'
import { ROUTES } from '@/utils/routes'

definePageMeta({ layout: 'dashboard' })

const { t } = useI18n()
const { user } = useAuth()

const page = ref(1)
const merchantId = computed(() => user.value?.merchant_id ?? 0)

const { data, isLoading, isError, refetch } = useProductsList(merchantId, page)

useHead({ title: t('nav.products') })

const totalPages = computed(() =>
  data.value ? Math.max(1, Math.ceil(data.value.total / data.value.per_page)) : 1,
)
</script>

<template>
  <div class="space-y-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">{{ $t('products.title') }}</h1>
        <p v-if="data" class="text-sm text-muted-foreground">
          {{ $t('products.totalCount', { count: data.total }) }}
        </p>
      </div>

      <NuxtLink
        :to="ROUTES.dashboard.productNew"
        class="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-warning transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Plus class="h-4 w-4" aria-hidden="true" />
        {{ $t('products.createNew') }}
      </NuxtLink>
    </header>

    <!-- Loading -->
    <div
      v-if="isLoading"
      class="flex items-center justify-center rounded-lg border border-border bg-card py-16"
    >
      <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
      <span class="ml-3 text-sm text-muted-foreground">{{ $t('common.loading') }}</span>
    </div>

    <!-- Erreur -->
    <div
      v-else-if="isError"
      role="alert"
      class="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center"
    >
      <p class="text-sm text-destructive">{{ $t('products.loadError') }}</p>
      <button
        type="button"
        class="mt-3 inline-flex items-center justify-center rounded-md border border-destructive/40 bg-card px-4 py-2 text-xs font-medium text-destructive transition hover:bg-destructive/10"
        @click="refetch()"
      >
        {{ $t('common.retry') }}
      </button>
    </div>

    <!-- Vide -->
    <ProductEmptyState v-else-if="data && data.total === 0" />

    <!-- Liste -->
    <template v-else-if="data && data.items.length > 0">
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <ProductCard v-for="product in data.items" :key="product.id" :product="product" />
      </div>

      <!-- Pagination -->
      <nav
        v-if="totalPages > 1"
        class="flex items-center justify-center gap-2 pt-4"
        :aria-label="$t('common.pagination')"
      >
        <button
          type="button"
          :disabled="page <= 1"
          class="inline-flex items-center gap-1 rounded-md border border-border bg-card px-3 py-1.5 text-sm transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          @click="page = Math.max(1, page - 1)"
        >
          <ChevronLeft class="h-4 w-4" aria-hidden="true" />
          {{ $t('common.previous') }}
        </button>

        <span class="px-3 text-sm text-muted-foreground">
          {{ $t('common.pageOf', { current: page, total: totalPages }) }}
        </span>

        <button
          type="button"
          :disabled="page >= totalPages"
          class="inline-flex items-center gap-1 rounded-md border border-border bg-card px-3 py-1.5 text-sm transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          @click="page = Math.min(totalPages, page + 1)"
        >
          {{ $t('common.next') }}
          <ChevronRight class="h-4 w-4" aria-hidden="true" />
        </button>
      </nav>
    </template>
  </div>
</template>
