<!--
  Item d'une conversation dans la liste.
  Référence : ARCHITECTURE_FRONTEND.md section 7.5
-->

<script setup lang="ts">
import { ChevronRight } from 'lucide-vue-next'

import StatusBadge from '@/features/conversations/components/StatusBadge.vue'
import { formatDateTime, formatPhone, initialsFrom } from '@/utils/format'
import { ROUTES } from '@/utils/routes'
import type { Conversation } from '../types'

interface Props {
  conversation: Conversation
}

const props = defineProps<Props>()
const { locale } = useI18n()

const detailHref = computed(() => ROUTES.dashboard.conversationDetail(props.conversation.id))
const initials = computed(() =>
  initialsFrom(props.conversation.client_name ?? props.conversation.client_phone),
)
const updatedAt = computed(() =>
  formatDateTime(props.conversation.updated_at, locale.value === 'en' ? 'en-US' : 'fr-FR'),
)
</script>

<template>
  <NuxtLink
    :to="detailHref"
    class="group flex items-center gap-3 rounded-lg border border-border bg-card p-4 transition hover:border-brand-forest/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
  >
    <div
      class="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-forest text-sm font-semibold text-brand-gold"
      aria-hidden="true"
    >
      {{ initials }}
    </div>

    <div class="min-w-0 flex-1">
      <div class="flex items-center justify-between gap-2">
        <p class="truncate font-medium text-foreground">
          {{ conversation.client_name ?? formatPhone(conversation.client_phone) }}
        </p>
        <StatusBadge :status="conversation.status" />
      </div>

      <p class="mt-0.5 truncate text-xs text-muted-foreground">
        {{ formatPhone(conversation.client_phone) }}
        <span v-if="conversation.current_offer" class="ml-2 text-brand-forest"
          >· {{ $t('conversations.currentOffer') }}: {{ conversation.current_offer }}</span
        >
      </p>

      <p class="mt-1 text-xs text-muted-foreground">{{ updatedAt }}</p>
    </div>

    <ChevronRight
      class="h-4 w-4 shrink-0 text-muted-foreground transition group-hover:text-brand-forest"
      aria-hidden="true"
    />
  </NuxtLink>
</template>
