<!--
  Badge de statut d'une conversation.
  Référence : utils/constants.ts:CONVERSATION_STATUS

  Couleur sémantique par statut, conserve la palette KALGA (forest/gold).
-->

<script setup lang="ts">
import { CONVERSATION_STATUS } from '@/utils/constants'
import type { ConversationStatusValue } from '@/utils/constants'

interface Props {
  status: ConversationStatusValue
}

const props = defineProps<Props>()

const STATUS_CLASSES: Record<ConversationStatusValue, string> = {
  [CONVERSATION_STATUS.ACTIVE]:
    'bg-primary/10 text-primary border border-primary/20',
  [CONVERSATION_STATUS.NEGOTIATING]:
    'bg-warning/20 text-primary border border-warning/40',
  [CONVERSATION_STATUS.AGREED]:
    'bg-emerald-500/10 text-emerald-700 dark:text-emerald-200 border border-emerald-500/20',
  [CONVERSATION_STATUS.PENDING_DELIVERY]:
    'bg-blue-500/10 text-blue-700 dark:text-blue-200 border border-blue-500/20',
  [CONVERSATION_STATUS.PENDING_PICKUP]:
    'bg-blue-500/10 text-blue-700 dark:text-blue-200 border border-blue-500/20',
  [CONVERSATION_STATUS.COMPLETED]:
    'bg-emerald-500/10 text-emerald-700 dark:text-emerald-200 border border-emerald-500/20',
  [CONVERSATION_STATUS.ABANDONED]: 'bg-muted text-muted-foreground border border-border',
  [CONVERSATION_STATUS.ENDED]: 'bg-muted text-muted-foreground border border-border',
  [CONVERSATION_STATUS.EXPIRED]: 'bg-muted text-muted-foreground border border-border',
}

const i18nKey = computed(() => `conversations.status.${props.status}`)
</script>

<template>
  <span
    :class="[
      'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
      STATUS_CLASSES[status],
    ]"
  >
    <span aria-hidden="true" class="h-1.5 w-1.5 rounded-full bg-current" />
    {{ $t(i18nKey) }}
  </span>
</template>
