<!--
  Carte d'activation : affiche un marchand en attente d'envoi de code.
-->

<script setup lang="ts">
import { KeyRound, Loader2, Send } from 'lucide-vue-next'

import { extractApiErrorMessage } from '@/composables/useApiError'
import { formatDateTime, formatPhone } from '@/utils/format'
import { useSendActivationCode } from '../composables/useActivations'
import type { Activation } from '../types'

interface Props {
  activation: Activation
}

const props = defineProps<Props>()
const { t, locale } = useI18n()
const { push } = useToast()
const { mutateAsync, isPending } = useSendActivationCode()

const sentAt = computed(() =>
  props.activation.sent_at
    ? formatDateTime(props.activation.sent_at, locale.value === 'en' ? 'en-US' : 'fr-FR')
    : null,
)

async function handleSend(): Promise<void> {
  try {
    await mutateAsync({ merchant_id: props.activation.merchant_id })
    push.success(t('admin.activationCodeSent'))
  } catch (err) {
    push.error(extractApiErrorMessage(err, t('admin.activationCodeError')))
  }
}
</script>

<template>
  <article class="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
    <div
      class="inline-flex h-10 w-10 items-center justify-center rounded-full bg-brand-gold/20 text-brand-forest"
      aria-hidden="true"
    >
      <KeyRound class="h-4 w-4" aria-hidden="true" />
    </div>

    <div class="min-w-0 flex-1">
      <p class="truncate text-sm font-medium text-foreground">
        {{ activation.merchant_name ?? $t('admin.unknownMerchant') }}
      </p>
      <p v-if="activation.merchant_phone" class="text-xs text-muted-foreground">
        {{ formatPhone(activation.merchant_phone) }}
      </p>
      <p v-if="sentAt" class="mt-1 text-xs text-muted-foreground">
        {{ $t('admin.lastSentAt') }}: {{ sentAt }}
      </p>
    </div>

    <button
      type="button"
      :disabled="isPending"
      class="inline-flex shrink-0 items-center gap-2 rounded-md bg-brand-forest px-3 py-1.5 text-xs font-medium text-brand-gold transition hover:bg-brand-forest/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
      @click="handleSend"
    >
      <Loader2 v-if="isPending" class="h-3 w-3 animate-spin" aria-hidden="true" />
      <Send v-else class="h-3 w-3" aria-hidden="true" />
      {{ isPending ? $t('common.loading') : $t('admin.sendCode') }}
    </button>
  </article>
</template>
