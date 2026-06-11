<!--
  Formulaire de commande publique — /commander/:code.
  Référence : ARCHITECTURE_FRONTEND.md sections 3 + 7.4

  Récap produit + form Zod + envoi → toast succès + écran "merci".
-->

<script setup lang="ts">
import { CheckCircle2, Loader2 } from 'lucide-vue-next'

import { extractApiErrorMessage } from '@/composables/useApiError'
import { storefrontOrderInputSchema } from '@/features/storefront/schemas'
import { useStorefrontContext } from '@/features/storefront/composables/useStorefrontContext'
import {
  useStorefrontProduct,
  useSubmitOrder,
} from '@/features/storefront/composables/useStorefront'
import type { StorefrontOrderInput } from '@/features/storefront/types'
import { formatPriceFCFA } from '@/utils/format'
import { ROUTES } from '@/utils/routes'

definePageMeta({ layout: 'storefront' })

const { t } = useI18n()
const route = useRoute()
const { push } = useToast()

const code = computed(() => {
  const raw = route.params.code
  return Array.isArray(raw) ? (raw[0] ?? '') : (raw ?? '')
})

// Le endpoint renvoie { product, variants, merchant } : on a besoin du produit
// (récap + code) ET du téléphone marchand (requis par le backend submit_order).
const { data, isLoading: productLoading } = useStorefrontProduct(code)
const product = computed(() => data.value?.product)
const merchant = computed(() => data.value?.merchant)
const { mutateAsync, isPending } = useSubmitOrder()

// Renseigne le header (branding marchand).
const storefrontContext = useStorefrontContext()
watchEffect(() => {
  if (merchant.value) storefrontContext.value = merchant.value
})

useHead({ title: () => t('storefront.orderTitle') })

const submitted = ref(false)

const form = reactive({
  client_name: '',
  client_phone: '',
  message: '',
})

const fieldErrors = reactive<{
  client_name?: string
  client_phone?: string
  message?: string
}>({})

const inputClass =
  'w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60'

function clearErrors(): void {
  fieldErrors.client_name = undefined
  fieldErrors.client_phone = undefined
  fieldErrors.message = undefined
}

async function handleSubmit(event: Event): Promise<void> {
  event.preventDefault()
  clearErrors()

  if (!product.value) {
    push.error(t('storefront.productNotFound'))
    return
  }

  const cleanedPhone = form.client_phone.replace(/\D/g, '')
  const payload: StorefrontOrderInput = {
    merchant_phone: merchant.value?.phone ?? '', // requis par le backend submit_order
    product_code: product.value.code,
    client_name: form.client_name.trim(),
    client_phone: cleanedPhone,
    message: form.message.trim() || null,
  }

  // Validation Zod (le merchant_phone sera renseigné par le backend ; on valide
  // les autres champs côté client)
  const validateInputSchema = storefrontOrderInputSchema.omit({ merchant_phone: true })
  const parsed = validateInputSchema.safeParse({
    product_code: payload.product_code,
    client_name: payload.client_name,
    client_phone: payload.client_phone,
    message: payload.message,
  })

  if (!parsed.success) {
    for (const issue of parsed.error.issues) {
      const key = issue.path[0] as keyof typeof fieldErrors | undefined
      if (key) fieldErrors[key] = issue.message
    }
    return
  }

  try {
    await mutateAsync(payload)
    submitted.value = true
    push.success(t('storefront.orderSentSuccess'))
  } catch (err) {
    push.error(extractApiErrorMessage(err, t('storefront.orderSentError')))
  }
}
</script>

<template>
  <main class="mx-auto max-w-3xl px-4 py-12 sm:px-6">
    <!-- Loading produit -->
    <div v-if="productLoading" class="flex justify-center py-16">
      <Loader2 class="h-8 w-8 animate-spin text-muted-foreground" aria-hidden="true" />
    </div>

    <!-- Produit introuvable -->
    <div
      v-else-if="!product"
      role="alert"
      class="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center"
    >
      <p class="text-sm text-destructive">{{ $t('storefront.productNotFound') }}</p>
    </div>

    <!-- Écran "Merci" -->
    <div
      v-else-if="submitted"
      class="rounded-lg border border-border bg-card p-8 text-center"
    >
      <div
        class="mx-auto mb-4 inline-flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600"
      >
        <CheckCircle2 class="h-8 w-8" aria-hidden="true" />
      </div>
      <h1 class="font-display text-2xl font-semibold text-primary">
        {{ $t('storefront.thanksTitle') }}
      </h1>
      <p class="mt-2 text-sm text-muted-foreground">
        {{ $t('storefront.thanksMessage') }}
      </p>

      <NuxtLink
        :to="ROUTES.home"
        class="mt-6 inline-flex items-center justify-center rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-warning transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {{ $t('errors.backHome') }}
      </NuxtLink>
    </div>

    <!-- Form -->
    <div v-else class="grid gap-6 lg:grid-cols-5">
      <!-- Récap produit -->
      <aside class="lg:col-span-2">
        <div class="rounded-lg border border-border bg-card p-4">
          <div
            v-if="product.image_url"
            class="mb-3 aspect-square overflow-hidden rounded-md bg-muted"
          >
            <img
              :src="product.image_url"
              :alt="product.name"
              class="h-full w-full object-cover"
              loading="eager"
            >
          </div>
          <span
            class="mb-2 inline-block rounded-md bg-primary px-2 py-0.5 text-xs font-semibold text-warning"
          >
            {{ product.code }}
          </span>
          <h2 class="font-display text-lg font-semibold text-primary">
            {{ product.name }}
          </h2>
          <p class="mt-1 text-xl font-semibold text-foreground">
            {{ formatPriceFCFA(product.price) }}
          </p>
        </div>
      </aside>

      <!-- Form -->
      <section class="lg:col-span-3">
        <header class="mb-4">
          <h1 class="font-display text-2xl font-semibold text-primary">
            {{ $t('storefront.orderFormTitle') }}
          </h1>
          <p class="text-sm text-muted-foreground">
            {{ $t('storefront.orderFormSubtitle') }}
          </p>
        </header>

        <form
          class="space-y-4 rounded-lg border border-border bg-card p-6"
          novalidate
          @submit="handleSubmit"
        >
          <div>
            <label for="client-name" class="mb-1 block text-sm font-medium text-foreground">
              {{ $t('storefront.fieldName') }} *
            </label>
            <input
              id="client-name"
              v-model="form.client_name"
              type="text"
              required
              :disabled="isPending"
              :aria-invalid="!!fieldErrors.client_name"
              :class="inputClass"
            >
            <p v-if="fieldErrors.client_name" class="mt-1 text-xs text-destructive">
              {{ fieldErrors.client_name }}
            </p>
          </div>

          <div>
            <label for="client-phone" class="mb-1 block text-sm font-medium text-foreground">
              {{ $t('storefront.fieldPhone') }} *
            </label>
            <input
              id="client-phone"
              v-model="form.client_phone"
              type="tel"
              inputmode="tel"
              autocomplete="tel"
              required
              :disabled="isPending"
              :aria-invalid="!!fieldErrors.client_phone"
              :placeholder="$t('storefront.fieldPhonePlaceholder')"
              :class="inputClass"
            >
            <p v-if="fieldErrors.client_phone" class="mt-1 text-xs text-destructive">
              {{ fieldErrors.client_phone }}
            </p>
            <p v-else class="mt-1 text-xs text-muted-foreground">
              {{ $t('storefront.fieldPhoneHint') }}
            </p>
          </div>

          <div>
            <label for="client-message" class="mb-1 block text-sm font-medium text-foreground">
              {{ $t('storefront.fieldMessage') }}
            </label>
            <textarea
              id="client-message"
              v-model="form.message"
              rows="3"
              :disabled="isPending"
              :placeholder="$t('storefront.fieldMessagePlaceholder')"
              :class="inputClass"
            />
            <p v-if="fieldErrors.message" class="mt-1 text-xs text-destructive">
              {{ fieldErrors.message }}
            </p>
          </div>

          <button
            type="submit"
            :disabled="isPending"
            class="inline-flex w-full items-center justify-center gap-2 rounded-md bg-primary px-5 py-3 text-sm font-semibold text-warning transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Loader2 v-if="isPending" class="h-4 w-4 animate-spin" aria-hidden="true" />
            {{ isPending ? $t('common.loading') : $t('storefront.confirmOrder') }}
          </button>
        </form>
      </section>
    </div>
  </main>
</template>
