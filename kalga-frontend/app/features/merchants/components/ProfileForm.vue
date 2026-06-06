<!--
  Form d'édition du profil marchand (nom, business, paiements).
-->

<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

import { extractApiErrorMessage } from '@/composables/useApiError'
import { merchantProfileUpdateSchema } from '@/features/merchants/schemas'
import type { Merchant, MerchantProfileUpdate } from '@/features/merchants/types'
import { useUpdateMerchantProfile } from '../composables/useMerchants'

interface Props {
  merchant: Merchant
}

const props = defineProps<Props>()
const { t } = useI18n()
const { push } = useToast()
const { mutateAsync, isPending } = useUpdateMerchantProfile()

const form = reactive<MerchantProfileUpdate>({
  name: props.merchant.name,
  business_name: props.merchant.business_name,
  payment_info: props.merchant.payment_info,
  payment_methods: props.merchant.payment_methods,
})
const fieldErrors = reactive<Partial<Record<keyof MerchantProfileUpdate, string>>>({})

const inputClass =
  'w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60'

async function handleSubmit(event: Event): Promise<void> {
  event.preventDefault()
  Object.keys(fieldErrors).forEach((k) => {
    fieldErrors[k as keyof MerchantProfileUpdate] = undefined
  })

  const parsed = merchantProfileUpdateSchema.safeParse(form)
  if (!parsed.success) {
    for (const issue of parsed.error.issues) {
      const key = issue.path[0] as keyof MerchantProfileUpdate | undefined
      if (key) fieldErrors[key] = issue.message
    }
    return
  }

  try {
    await mutateAsync({ id: props.merchant.id, data: parsed.data })
    push.success(t('settings.profileSaved'))
  } catch (err) {
    push.error(extractApiErrorMessage(err, t('settings.saveError')))
  }
}
</script>

<template>
  <form class="space-y-4" novalidate @submit="handleSubmit">
    <div>
      <label for="profile-name" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('settings.merchantName') }} *
      </label>
      <input
        id="profile-name"
        v-model="form.name"
        type="text"
        required
        :disabled="isPending"
        :class="inputClass"
      >
      <p v-if="fieldErrors.name" class="mt-1 text-xs text-destructive">{{ fieldErrors.name }}</p>
    </div>

    <div>
      <label for="business-name" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('settings.businessName') }}
      </label>
      <input
        id="business-name"
        :value="form.business_name ?? ''"
        type="text"
        :disabled="isPending"
        :class="inputClass"
        @input="form.business_name = ($event.target as HTMLInputElement).value || null"
      >
    </div>

    <div>
      <label for="payment-methods" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('settings.paymentMethods') }}
      </label>
      <input
        id="payment-methods"
        :value="form.payment_methods ?? ''"
        type="text"
        :disabled="isPending"
        :placeholder="$t('settings.paymentMethodsPlaceholder')"
        :class="inputClass"
        @input="form.payment_methods = ($event.target as HTMLInputElement).value || null"
      >
    </div>

    <div>
      <label for="payment-info" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('settings.paymentInfo') }}
      </label>
      <textarea
        id="payment-info"
        :value="form.payment_info ?? ''"
        rows="3"
        :disabled="isPending"
        :placeholder="$t('settings.paymentInfoPlaceholder')"
        :class="inputClass"
        @input="form.payment_info = ($event.target as HTMLTextAreaElement).value || null"
      />
    </div>

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
