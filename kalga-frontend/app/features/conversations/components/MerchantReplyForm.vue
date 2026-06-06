<!--
  Formulaire de réponse marchand (human takeover).
  Référence : ARCHITECTURE_FRONTEND.md sections 7.4 + 9.4

  Permet au marchand de répondre directement à un client pour un cas où
  l'IA n'a pas su gérer. Optionnellement, sauvegarde la Q/R en KB.
-->

<script setup lang="ts">
import { Loader2, Send } from 'lucide-vue-next'

import { merchantReplyInputSchema } from '@/features/conversations/schemas'
import { extractApiErrorMessage } from '@/composables/useApiError'
import { useSendMerchantReply } from '../composables/useConversations'
import type { Conversation } from '../types'

interface Props {
  conversation: Conversation
  /** Dernier message client à passer comme contexte (client_question) */
  lastClientMessage: string
}

const props = defineProps<Props>()
const emit = defineEmits<{ replied: [] }>()

const { t } = useI18n()
const { user } = useAuth()
const { push } = useToast()
const { mutateAsync, isPending } = useSendMerchantReply()

const answer = ref('')
const saveToKb = ref(true)
const fieldError = ref<string | null>(null)

async function handleSubmit(event: Event): Promise<void> {
  event.preventDefault()
  fieldError.value = null

  const merchantId = user.value?.merchant_id ?? 0
  if (!merchantId) {
    push.error(t('conversations.replyMerchantMissing'))
    return
  }

  const parsed = merchantReplyInputSchema.safeParse({
    merchant_id: merchantId,
    conversation_id: props.conversation.id,
    client_phone: props.conversation.client_phone,
    client_question: props.lastClientMessage,
    merchant_answer: answer.value,
    save_to_kb: saveToKb.value,
  })

  if (!parsed.success) {
    fieldError.value = parsed.error.issues[0]?.message ?? t('common.error')
    return
  }

  try {
    await mutateAsync(parsed.data)
    push.success(t('conversations.replySent'))
    answer.value = ''
    emit('replied')
  } catch (err) {
    push.error(extractApiErrorMessage(err, t('conversations.replyError')))
  }
}
</script>

<template>
  <form
    class="space-y-3 rounded-lg border border-border bg-card p-4"
    novalidate
    @submit="handleSubmit"
  >
    <div>
      <label for="merchant-answer" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('conversations.replyLabel') }}
      </label>
      <textarea
        id="merchant-answer"
        v-model="answer"
        rows="3"
        :disabled="isPending"
        :placeholder="$t('conversations.replyPlaceholder')"
        :aria-invalid="!!fieldError"
        class="w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
      />
      <p v-if="fieldError" class="mt-1 text-xs text-destructive">{{ fieldError }}</p>
    </div>

    <div class="flex items-center justify-between gap-3">
      <label class="inline-flex items-center gap-2 text-sm text-muted-foreground">
        <input
          v-model="saveToKb"
          type="checkbox"
          :disabled="isPending"
          class="h-4 w-4 rounded border-input text-primary focus-visible:ring-2 focus-visible:ring-ring"
        >
        {{ $t('conversations.saveToKb') }}
      </label>

      <button
        type="submit"
        :disabled="isPending || answer.trim().length === 0"
        class="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-warning transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Loader2 v-if="isPending" class="h-4 w-4 animate-spin" aria-hidden="true" />
        <Send v-else class="h-4 w-4" aria-hidden="true" />
        {{ isPending ? $t('common.loading') : $t('conversations.send') }}
      </button>
    </div>
  </form>
</template>
