<!--
  Détail d'une conversation (option 2 : reconstruit depuis la LISTE + messages).
  Porté fidèlement depuis dashboard/static/app.js (loadConversationDetail).

  Le backend n'expose PAS « une conversation par id » → on récupère la
  conversation dans la liste du marchand (cache TanStack partagé avec la page
  liste) et on charge ses messages. Reprise humaine : Accepter / Refuser l'offre
  (POST /accept, /reject) + réponse manuelle.
-->

<script setup lang="ts">
import { ArrowLeft, Check, Loader2, RefreshCcw, X } from 'lucide-vue-next'

import MerchantReplyForm from '@/features/conversations/components/MerchantReplyForm.vue'
import MessageBubble from '@/features/conversations/components/MessageBubble.vue'
import StatusBadge from '@/features/conversations/components/StatusBadge.vue'
import {
  useAcceptConversation,
  useConversationMessages,
  useConversationsList,
  useRejectConversation,
} from '@/features/conversations/composables/useConversations'
import { formatPhone, formatPriceFCFA } from '@/utils/format'
import { ROUTES } from '@/utils/routes'

definePageMeta({ layout: 'dashboard' })

const { t } = useI18n()
const route = useRoute()
const { user } = useAuth()
const { push } = useToast()

const conversationId = computed(() => {
  const raw = route.params.id
  const id = Number(Array.isArray(raw) ? raw[0] : raw)
  return Number.isFinite(id) && id > 0 ? id : 0
})

const merchantPhone = computed(() => user.value?.merchant_phone ?? '')
const allStatus = ref<string | undefined>(undefined)
const firstPage = ref(1)

// La conversation vient de la liste (même cache que /dashboard/conversations).
const { data: list, isLoading, isError } = useConversationsList(merchantPhone, allStatus, firstPage)
const conversation = computed(
  () => list.value?.items.find((c) => c.id === conversationId.value) ?? null,
)

const {
  data: messages,
  isLoading: messagesLoading,
  refetch: refetchMessages,
} = useConversationMessages(conversationId)

const { mutateAsync: acceptOffer, isPending: accepting } = useAcceptConversation()
const { mutateAsync: rejectOffer, isPending: rejecting } = useRejectConversation()

useHead({
  title: () =>
    conversation.value
      ? t('conversations.detailTitle', { id: conversation.value.id })
      : t('common.loading'),
})

const lastClientMessage = computed<string>(() => {
  const items = messages.value ?? []
  for (let i = items.length - 1; i >= 0; i--) {
    const message = items[i]
    if (message?.is_from_client) return message.content
  }
  return ''
})

async function onAccept(): Promise<void> {
  try {
    await acceptOffer(conversationId.value)
    push.success(t('conversations.accepted'))
    await refetchMessages()
  } catch (error) {
    push.error(extractApiErrorMessage(error, t('conversations.actionError')))
  }
}

async function onReject(): Promise<void> {
  try {
    await rejectOffer(conversationId.value)
    push.success(t('conversations.rejected'))
    await refetchMessages()
  } catch (error) {
    push.error(extractApiErrorMessage(error, t('conversations.actionError')))
  }
}
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

    <!-- Loading -->
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
      <!-- Header -->
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

        <div
          v-if="conversation.product_code"
          class="mt-4 flex items-center gap-3 rounded-md border border-border bg-muted/30 p-3"
        >
          <div class="rounded-md bg-primary px-2 py-1 text-xs font-semibold text-primary-foreground">
            {{ conversation.product_code }}
          </div>
          <p v-if="conversation.product_name" class="text-sm font-medium text-foreground">
            {{ conversation.product_name }}
          </p>
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

      <!-- Reprise humaine : offre + Accepter/Refuser -->
      <section class="rounded-lg border border-border bg-card p-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <p v-if="conversation.current_offer" class="text-sm text-muted-foreground">
            {{ $t('conversations.currentOffer') }} :
            <span class="font-semibold text-gold">
              {{ formatPriceFCFA(conversation.current_offer) }}
            </span>
          </p>
          <span v-else class="text-sm text-muted-foreground">{{ $t('conversations.noOffer') }}</span>

          <div class="flex gap-2">
            <button
              type="button"
              :disabled="accepting"
              class="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary-hi disabled:opacity-60"
              @click="onAccept"
            >
              <Check class="h-4 w-4" aria-hidden="true" />
              {{ $t('conversations.accept') }}
            </button>
            <button
              type="button"
              :disabled="rejecting"
              class="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground transition hover:bg-muted disabled:opacity-60"
              @click="onReject"
            >
              <X class="h-4 w-4" aria-hidden="true" />
              {{ $t('conversations.reject') }}
            </button>
          </div>
        </div>
      </section>

      <!-- Réponse manuelle -->
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
