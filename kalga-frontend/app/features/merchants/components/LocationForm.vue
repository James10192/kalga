<!--
  Form de localisation marchand : adresse texte + GPS (détection auto possible).
-->

<script setup lang="ts">
import { Loader2, MapPin } from 'lucide-vue-next'

import { extractApiErrorMessage } from '@/composables/useApiError'
import { merchantLocationUpdateSchema } from '@/features/merchants/schemas'
import type { Merchant, MerchantLocationUpdate } from '@/features/merchants/types'
import { useUpdateMerchantLocation } from '../composables/useMerchants'

interface Props {
  merchant: Merchant
}

const props = defineProps<Props>()
const { t } = useI18n()
const { push } = useToast()
const { mutateAsync, isPending } = useUpdateMerchantLocation()

const form = reactive<MerchantLocationUpdate>({
  address: props.merchant.address,
  city: props.merchant.city,
  commune: props.merchant.commune,
  quarter: props.merchant.quarter,
  latitude: props.merchant.latitude,
  longitude: props.merchant.longitude,
})
const fieldError = ref<string | null>(null)
const detecting = ref(false)

const inputClass =
  'w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60'

function detectGps(): void {
  if (typeof navigator === 'undefined' || !navigator.geolocation) {
    push.error(t('settings.geolocationUnsupported'))
    return
  }
  detecting.value = true
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      form.latitude = Number(pos.coords.latitude.toFixed(6))
      form.longitude = Number(pos.coords.longitude.toFixed(6))
      detecting.value = false
      push.success(t('settings.gpsDetected'))
    },
    (err) => {
      detecting.value = false
      push.error(`${t('settings.gpsError')} (${err.code})`)
    },
    { enableHighAccuracy: true, timeout: 10_000 },
  )
}

async function handleSubmit(event: Event): Promise<void> {
  event.preventDefault()
  fieldError.value = null

  const parsed = merchantLocationUpdateSchema.safeParse(form)
  if (!parsed.success) {
    fieldError.value = parsed.error.issues[0]?.message ?? t('common.error')
    return
  }

  try {
    await mutateAsync({ id: props.merchant.id, data: parsed.data })
    push.success(t('settings.locationSaved'))
  } catch (err) {
    push.error(extractApiErrorMessage(err, t('settings.saveError')))
  }
}
</script>

<template>
  <form class="space-y-4" novalidate @submit="handleSubmit">
    <div>
      <label for="address" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('settings.address') }}
      </label>
      <input
        id="address"
        :value="form.address ?? ''"
        type="text"
        :disabled="isPending"
        :class="inputClass"
        @input="form.address = ($event.target as HTMLInputElement).value || null"
      >
    </div>

    <div class="grid gap-4 sm:grid-cols-3">
      <div>
        <label for="city" class="mb-1 block text-sm font-medium text-foreground">
          {{ $t('settings.city') }}
        </label>
        <input
          id="city"
          :value="form.city ?? ''"
          type="text"
          :disabled="isPending"
          :class="inputClass"
          @input="form.city = ($event.target as HTMLInputElement).value || null"
        >
      </div>
      <div>
        <label for="commune" class="mb-1 block text-sm font-medium text-foreground">
          {{ $t('settings.commune') }}
        </label>
        <input
          id="commune"
          :value="form.commune ?? ''"
          type="text"
          :disabled="isPending"
          :class="inputClass"
          @input="form.commune = ($event.target as HTMLInputElement).value || null"
        >
      </div>
      <div>
        <label for="quarter" class="mb-1 block text-sm font-medium text-foreground">
          {{ $t('settings.quarter') }}
        </label>
        <input
          id="quarter"
          :value="form.quarter ?? ''"
          type="text"
          :disabled="isPending"
          :class="inputClass"
          @input="form.quarter = ($event.target as HTMLInputElement).value || null"
        >
      </div>
    </div>

    <fieldset class="rounded-md border border-border p-4">
      <legend class="px-2 text-sm font-medium text-foreground">
        {{ $t('settings.gpsCoordinates') }}
      </legend>

      <div class="grid gap-4 sm:grid-cols-2">
        <div>
          <label for="latitude" class="mb-1 block text-xs text-muted-foreground">
            {{ $t('settings.latitude') }}
          </label>
          <input
            id="latitude"
            :value="form.latitude ?? ''"
            type="number"
            step="0.000001"
            :disabled="isPending"
            :class="inputClass"
            @input="
              form.latitude = ($event.target as HTMLInputElement).value === ''
                ? null
                : Number(($event.target as HTMLInputElement).value)
            "
          >
        </div>
        <div>
          <label for="longitude" class="mb-1 block text-xs text-muted-foreground">
            {{ $t('settings.longitude') }}
          </label>
          <input
            id="longitude"
            :value="form.longitude ?? ''"
            type="number"
            step="0.000001"
            :disabled="isPending"
            :class="inputClass"
            @input="
              form.longitude = ($event.target as HTMLInputElement).value === ''
                ? null
                : Number(($event.target as HTMLInputElement).value)
            "
          >
        </div>
      </div>

      <button
        type="button"
        :disabled="detecting || isPending"
        class="mt-3 inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-xs text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
        @click="detectGps"
      >
        <Loader2 v-if="detecting" class="h-3 w-3 animate-spin" aria-hidden="true" />
        <MapPin v-else class="h-3 w-3" aria-hidden="true" />
        {{ detecting ? $t('settings.gpsDetecting') : $t('settings.gpsDetect') }}
      </button>
    </fieldset>

    <p v-if="fieldError" role="alert" class="text-xs text-destructive">{{ fieldError }}</p>

    <div class="pt-1">
      <button
        type="submit"
        :disabled="isPending"
        class="inline-flex items-center gap-2 rounded-md bg-brand-forest px-4 py-2 text-sm font-medium text-brand-gold transition hover:bg-brand-forest/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Loader2 v-if="isPending" class="h-4 w-4 animate-spin" aria-hidden="true" />
        {{ isPending ? $t('common.loading') : $t('common.save') }}
      </button>
    </div>
  </form>
</template>
