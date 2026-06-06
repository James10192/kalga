<!--
  Liste des conversations du marchand.
  Référence : ARCHITECTURE_FRONTEND.md sections 3 + 9.1
-->

<script setup lang="ts">
import { ChevronLeft, ChevronRight, Loader2, MessageSquareOff } from 'lucide-vue-next'

import ConversationFilters from '@/features/conversations/components/ConversationFilters.vue'
import ConversationListItem from '@/features/conversations/components/ConversationListItem.vue'
import { useConversationsList } from '@/features/conversations/composables/useConversations'

definePageMeta({ layout: 'dashboard' })

const { t } = useI18n()
const { user } = useAuth()

const merchantPhone = computed(() => user.value?.merchant_phone ?? '')

const status = ref<string | undefined>(undefined)
const page = ref(1)

const { data, isLoading, isError, refetch } = useConversationsList(merchantPhone, status, page)

useHead({ title: t('nav.conversations') })

const totalPages = computed(() =>
  data.value ? Math.max(1, Math.ceil(data.value.total / data.value.per_page)) : 1,
)

// Reset page quand le filtre change
watch(status, () => {
  page.value = 1
})
</script>

<template>
  <div class="space-y-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">{{ $t('conversations.title') }}</h1>
        <p v-if="data" class="text-sm text-muted-foreground">
          {{ $t('conversations.totalCount', { count: data.total }) }}
        </p>
      </div>

      <ConversationFilters v-model="status" />
    </header>

    <!-- État connexion marchand -->
    <div
      v-if="!merchantPhone"
      role="alert"
      class="rounded-lg border border-warning/30 bg-warning/10 p-4 text-sm text-primary"
    >
      {{ $t('conversations.noMerchantContext') }}
    </div>

    <!-- Loading -->
    <div
      v-else-if="isLoading"
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
      <p class="text-sm text-destructive">{{ $t('conversations.loadError') }}</p>
      <button
        type="button"
        class="mt-3 inline-flex items-center justify-center rounded-md border border-destructive/40 bg-card px-4 py-2 text-xs font-medium text-destructive transition hover:bg-destructive/10"
        @click="refetch()"
      >
        {{ $t('common.retry') }}
      </button>
    </div>

    <!-- Vide -->
    <div
      v-else-if="data && data.total === 0"
      class="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card px-6 py-16 text-center"
    >
      <div
        class="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary"
      >
        <MessageSquareOff class="h-7 w-7" aria-hidden="true" />
      </div>
      <h2 class="font-display text-xl font-semibold text-primary">
        {{ $t('conversations.emptyTitle') }}
      </h2>
      <p class="mt-1 max-w-sm text-sm text-muted-foreground">
        {{ $t('conversations.emptyMessage') }}
      </p>
    </div>

    <!-- Liste -->
    <template v-else-if="data">
      <div class="space-y-2">
        <ConversationListItem
          v-for="conv in data.items"
          :key="conv.id"
          :conversation="conv"
        />
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
