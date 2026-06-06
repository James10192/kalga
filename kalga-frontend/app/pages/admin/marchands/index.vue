<!--
  Liste paginée + filtrable des marchands (zone admin).
-->

<script setup lang="ts">
import { ChevronLeft, ChevronRight, Loader2, Search, Users } from 'lucide-vue-next'

import MerchantRow from '@/features/merchants/components/MerchantRow.vue'
import { useMerchantsList } from '@/features/merchants/composables/useMerchants'

definePageMeta({ layout: 'admin' })

const { t } = useI18n()

const search = ref('')
const page = ref(1)

const { data, isLoading, isError, refetch } = useMerchantsList(page, search)

useHead({ title: t('nav.merchants') })

const totalPages = computed(() =>
  data.value ? Math.max(1, Math.ceil(data.value.total / data.value.per_page)) : 1,
)

watch(search, () => {
  page.value = 1
})

const inputClass =
  'w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
</script>

<template>
  <div class="space-y-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">{{ $t('admin.merchants') }}</h1>
        <p v-if="data" class="text-sm text-muted-foreground">
          {{ $t('admin.merchantCount', { count: data.total }) }}
        </p>
      </div>

      <label class="relative w-full sm:w-72">
        <span class="sr-only">{{ $t('common.search') }}</span>
        <Search
          class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <input
          v-model="search"
          type="search"
          :placeholder="$t('admin.searchMerchant')"
          :class="[inputClass, 'pl-9']"
        >
      </label>
    </header>

    <div
      v-if="isLoading"
      class="flex items-center justify-center rounded-lg border border-border bg-card py-16"
    >
      <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
    </div>

    <div
      v-else-if="isError"
      role="alert"
      class="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center"
    >
      <p class="text-sm text-destructive">{{ $t('admin.loadError') }}</p>
      <button
        type="button"
        class="mt-3 inline-flex items-center rounded-md border border-destructive/40 bg-card px-4 py-2 text-xs font-medium text-destructive transition hover:bg-destructive/10"
        @click="refetch()"
      >
        {{ $t('common.retry') }}
      </button>
    </div>

    <div
      v-else-if="data && data.total === 0"
      class="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card px-6 py-16 text-center"
    >
      <div
        class="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary"
      >
        <Users class="h-6 w-6" aria-hidden="true" />
      </div>
      <p class="text-sm text-muted-foreground">{{ $t('admin.noMerchants') }}</p>
    </div>

    <template v-else-if="data">
      <div class="space-y-2">
        <MerchantRow v-for="m in data.items" :key="m.id" :merchant="m" />
      </div>

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
