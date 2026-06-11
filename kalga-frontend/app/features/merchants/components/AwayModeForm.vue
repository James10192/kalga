<!--
  Form mode absence : toggle + message personnalisé.
-->

<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

import { extractApiErrorMessage } from '@/composables/useApiError'
import { merchantAwayModeUpdateSchema } from '@/features/merchants/schemas'
import type { Merchant, MerchantAwayModeUpdate } from '@/features/merchants/types'
import { useUpdateAwayMode } from '../composables/useMerchants'

interface Props {
  merchant: Merchant
}

const props = defineProps<Props>()
const { t } = useI18n()
const { push } = useToast()
const { mutateAsync, isPending } = useUpdateAwayMode()

const form = reactive<MerchantAwayModeUpdate>({
  away_mode_enabled: props.merchant.away_mode_enabled,
  away_message: props.merchant.away_message,
})
const fieldError = ref<string | null>(null)

const inputClass =
  'w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60'

async function handleSubmit(event: Event): Promise<void> {
  event.preventDefault()
  fieldError.value = null

  const parsed = merchantAwayModeUpdateSchema.safeParse(form)
  if (!parsed.success) {
    fieldError.value = parsed.error.issues[0]?.message ?? t('common.error')
    return
  }

  try {
    await mutateAsync({ phone: props.merchant.phone, data: parsed.data })
    push.success(t('settings.awayModeSaved'))
  } catch (err) {
    push.error(extractApiErrorMessage(err, t('settings.saveError')))
  }
}
</script>

<template>
  <form class="space-y-4" novalidate @submit="handleSubmit">
    <label class="flex items-center gap-3 rounded-md border border-border bg-card p-3">
      <input
        v-model="form.away_mode_enabled"
        type="checkbox"
        :disabled="isPending"
        class="h-4 w-4 rounded border-input text-primary focus-visible:ring-2 focus-visible:ring-ring"
      >
      <div class="flex-1">
        <p class="text-sm font-medium text-foreground">{{ $t('settings.awayModeToggle') }}</p>
        <p class="text-xs text-muted-foreground">{{ $t('settings.awayModeHint') }}</p>
      </div>
    </label>

    <div>
      <label for="away-message" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('settings.awayMessage') }}
      </label>
      <textarea
        id="away-message"
        :value="form.away_message ?? ''"
        rows="3"
        :disabled="isPending || !form.away_mode_enabled"
        :placeholder="$t('settings.awayMessagePlaceholder')"
        :class="inputClass"
        @input="form.away_message = ($event.target as HTMLTextAreaElement).value || null"
      />
    </div>

    <p v-if="fieldError" role="alert" class="text-xs text-destructive">{{ fieldError }}</p>

    <div class="pt-1">
      <button
        type="submit"
        :disabled="isPending"
        class="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-warning transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Loader2 v-if="isPending" class="h-4 w-4 animate-spin" aria-hidden="true" />
        {{ isPending ? $t('common.loading') : $t('common.save') }}
      </button>
    </div>
  </form>
</template>
