<!--
  Form de configuration de la persona du bot IA.
-->

<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

import { extractApiErrorMessage } from '@/composables/useApiError'
import { merchantBotPersonaUpdateSchema } from '@/features/merchants/schemas'
import type { Merchant, MerchantBotPersonaUpdate } from '@/features/merchants/types'
import { useUpdateBotPersona } from '../composables/useMerchants'

interface Props {
  merchant: Merchant
}

const props = defineProps<Props>()
const { t } = useI18n()
const { push } = useToast()
const { mutateAsync, isPending } = useUpdateBotPersona()

const TONE_VALUES = ['casual', 'formal', 'friendly'] as const
const STYLE_VALUES = ['flexible', 'firm', 'aggressive'] as const

const form = reactive<MerchantBotPersonaUpdate>({
  bot_tone: (props.merchant.bot_tone as (typeof TONE_VALUES)[number] | null) ?? null,
  bot_style: (props.merchant.bot_style as (typeof STYLE_VALUES)[number] | null) ?? null,
  bot_catchphrase: props.merchant.bot_catchphrase,
})
const fieldError = ref<string | null>(null)

const inputClass =
  'w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60'

async function handleSubmit(event: Event): Promise<void> {
  event.preventDefault()
  fieldError.value = null

  const parsed = merchantBotPersonaUpdateSchema.safeParse(form)
  if (!parsed.success) {
    fieldError.value = parsed.error.issues[0]?.message ?? t('common.error')
    return
  }

  try {
    await mutateAsync({ id: props.merchant.id, data: parsed.data })
    push.success(t('settings.personaSaved'))
  } catch (err) {
    push.error(extractApiErrorMessage(err, t('settings.saveError')))
  }
}
</script>

<template>
  <form class="space-y-4" novalidate @submit="handleSubmit">
    <div class="grid gap-4 sm:grid-cols-2">
      <div>
        <label for="bot-tone" class="mb-1 block text-sm font-medium text-foreground">
          {{ $t('settings.botTone') }}
        </label>
        <select
          id="bot-tone"
          v-model="form.bot_tone"
          :disabled="isPending"
          :class="inputClass"
        >
          <option :value="null">{{ $t('settings.botToneDefault') }}</option>
          <option v-for="tone in TONE_VALUES" :key="tone" :value="tone">
            {{ $t(`settings.tone.${tone}`) }}
          </option>
        </select>
        <p class="mt-1 text-xs text-muted-foreground">{{ $t('settings.botToneHint') }}</p>
      </div>

      <div>
        <label for="bot-style" class="mb-1 block text-sm font-medium text-foreground">
          {{ $t('settings.botStyle') }}
        </label>
        <select
          id="bot-style"
          v-model="form.bot_style"
          :disabled="isPending"
          :class="inputClass"
        >
          <option :value="null">{{ $t('settings.botStyleDefault') }}</option>
          <option v-for="style in STYLE_VALUES" :key="style" :value="style">
            {{ $t(`settings.style.${style}`) }}
          </option>
        </select>
        <p class="mt-1 text-xs text-muted-foreground">{{ $t('settings.botStyleHint') }}</p>
      </div>
    </div>

    <div>
      <label for="catchphrase" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('settings.catchphrase') }}
      </label>
      <input
        id="catchphrase"
        :value="form.bot_catchphrase ?? ''"
        type="text"
        :disabled="isPending"
        :placeholder="$t('settings.catchphrasePlaceholder')"
        :class="inputClass"
        @input="form.bot_catchphrase = ($event.target as HTMLInputElement).value || null"
      >
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
