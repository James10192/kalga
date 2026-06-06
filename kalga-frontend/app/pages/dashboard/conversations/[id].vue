<!--
  Détail d'une conversation : header + thread messages + human takeover form.
-->

<script setup lang="ts">
import { ArrowLeft, Loader2, RefreshCcw } from 'lucide-vue-next'

import MerchantReplyForm from '@/features/conversations/components/MerchantReplyForm.vue'
import MessageBubble from '@/features/conversations/components/MessageBubble.vue'
import StatusBadge from '@/features/conversations/components/StatusBadge.vue'
import {
  useConversation,
  useConversationMessages,
} from '@/features/conversations/composables/useConversations'
import { useProduct } from '@/features/products/composables/useProducts'
import { formatPhone } from '@/utils/format'
import { ROUTES } from '@/utils/routes'

definePageMeta({ layout: 'dashboard' })

const { t } = useI18n()
const route = useRoute()

const conversationId = computed(() => {
  const raw = route.params.id
  const id = Number(Array.isArray(raw) ? raw[0] : raw)
  return Number.isFinite(id) && id > 0 ? id : 0
})

const { data: conversation, isLoading, isError } = useConversation(conversationId)
const productId = computed(() => conversation.value?.product_id ?? 0)
const { data: product } = useProduct(productId)
const {
  data: messages,
  isLoading: messagesLoading,
  refetch: refetchMessages,
} = useConversationMessages(conversationId)

useHead({
  title: () =>
    conversation.value
      ? t('conversations.detailTitle', { id: conversation.value.id })
      : t('common.loading'),
})

const lastClientMessage = computed<string>(() => {
  const list = messages.value ?? []
  for (let i = list.length - 1; i >= 0; i--) {
    const m = list[i]
    if (m?.is_from_client) return m.content
  }
  return ''
})
</script>

<template>
  <div class="space-y-6">
    <NuxtLink
      :to="ROUTES.dashboard.conversations"
      class="inline-flex items-center gap-1 text-sm text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <ArrowLeft class="h-4 w-4" aria-hidden="true" />
      {{ $t('conversations.backToList') }}
    </NuxtLink>

    <!-- Loading conversation -->
    <div
      v-if="isLoading"
      class="flex items-center justify-center rounded-lg border border-border bg-card py-16"
    >
      <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
    </div>

    <div
      v-else-if="isError || !conversation"
      role="alert"
      class="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center"
    >
      <p class="text-sm text-destructive">{{ $t('conversations.loadError') }}</p>
    </div>

    <template v-else>
      <!-- Header conversation -->
      <header class="rounded-lg border border-border bg-card p-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 class="text-lg font-semibold text-foreground">
              {{ conversation.client_name ?? formatPhone(conversation.client_phone) }}
            </h1>
            <p class="text-sm text-muted-foreground">
              {{ formatPhone(conversation.client_phone) }}
            </p>
          </div>
          <StatusBadge :status="conversation.status" />
        </div>

        <!-- Bloc produit -->
        <div
          v-if="product"
          class="mt-4 flex items-center gap-3 rounded-md border border-border bg-muted/30 p-3"
        >
          <div
            class="rounded-md bg-primary px-2 py-1 text-xs font-semibold text-warning"
          >
            {{ product.code }}
          </div>
          <p class="text-sm font-medium text-foreground">{{ product.name }}</p>
          <NuxtLink
            :to="ROUTES.dashboard.productDetail(product.id)"
            class="ml-auto text-xs text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {{ $t('conversations.openProduct') }}
          </NuxtLink>
        </div>

        <div v-if="conversation.current_offer" class="mt-2 text-xs text-muted-foreground">
          {{ $t('conversations.currentOffer') }}:
          <span class="font-medium text-primary">{{ conversation.current_offer }}</span>
        </div>
      </header>

      <!-- Thread messages -->
      <section class="rounded-lg border border-border bg-card p-4">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-muted-foreground">
            {{ $t('conversations.messages') }}
          </h2>
          <button
            type="button"
            :aria-label="$t('common.retry')"
            class="inline-flex items-center justify-center rounded-md p-1.5 text-muted-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            @click="refetchMessages()"
          >
            <RefreshCcw class="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div v-if="messagesLoading" class="flex justify-center py-8">
          <Loader2 class="h-5 w-5 animate-spin text-muted-foreground" aria-hidden="true" />
        </div>

        <div
          v-else-if="!messages || messages.length === 0"
          class="py-8 text-center text-sm text-muted-foreground"
        >
          {{ $t('conversations.noMessages') }}
        </div>

        <div v-else class="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
          <MessageBubble v-for="msg in messages" :key="msg.id" :message="msg" />
        </div>
      </section>

      <!-- Human takeover form -->
      <section v-if="lastClientMessage">
        <MerchantReplyForm
          :conversation="conversation"
          :last-client-message="lastClientMessage"
          @replied="refetchMessages()"
        />
      </section>
    </template>
  </div>
</template>
