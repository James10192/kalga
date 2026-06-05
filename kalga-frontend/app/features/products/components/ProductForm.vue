<!--
  Formulaire produit — utilisé pour création ET édition.
  Référence : ARCHITECTURE_FRONTEND.md sections 7.4 (Validation) + 7.5

  Validation Zod côté client AVANT soumission (UX rapide, économie réseau).
  Émet `submit` avec les données validées une fois la validation passée.
-->

<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

import { productCreateInputSchema } from '@/features/products/schemas'
import type { Product, ProductCreateInput } from '@/features/products/types'

interface Props {
  /** Valeurs initiales (pour édition) — sinon valeurs par défaut */
  initial?: Product | null
  /** État de soumission (désactive les inputs + spinner) */
  loading?: boolean
  /** Label du bouton submit */
  submitLabelI18nKey?: string
}

const props = withDefaults(defineProps<Props>(), {
  initial: null,
  loading: false,
  submitLabelI18nKey: 'common.save',
})

const emit = defineEmits<{ submit: [data: ProductCreateInput] }>()

const { t } = useI18n()

/** État du formulaire — initialisé depuis `props.initial` si édition. */
const form = reactive<ProductCreateInput>({
  name: props.initial?.name ?? '',
  description: props.initial?.description ?? null,
  price: props.initial?.price ?? 0,
  min_price: props.initial?.min_price ?? 0,
  image_path: props.initial?.image_path ?? null,
  group_id: props.initial?.group_id ?? null,
  variant_name: props.initial?.variant_name ?? null,
  stock_quantity: props.initial?.stock_quantity ?? null,
  low_stock_threshold: props.initial?.low_stock_threshold ?? null,
  out_of_stock_mode: props.initial?.out_of_stock_mode ?? 'waitlist',
})

const fieldErrors = reactive<Partial<Record<keyof ProductCreateInput, string>>>({})

function clearErrors(): void {
  for (const key of Object.keys(fieldErrors) as Array<keyof ProductCreateInput>) {
    fieldErrors[key] = undefined
  }
}

function handleSubmit(event: Event): void {
  event.preventDefault()
  clearErrors()

  const parsed = productCreateInputSchema.safeParse(form)
  if (!parsed.success) {
    for (const issue of parsed.error.issues) {
      const key = issue.path[0] as keyof ProductCreateInput | undefined
      if (key) {
        fieldErrors[key] = issue.message
      }
    }
    return
  }

  emit('submit', parsed.data)
}

/** Classes communes pour les inputs */
const inputClass =
  'w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60'
</script>

<template>
  <form class="space-y-5" novalidate @submit="handleSubmit">
    <!-- Nom -->
    <div>
      <label for="name" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('products.name') }} *
      </label>
      <input
        id="name"
        v-model="form.name"
        type="text"
        required
        :disabled="loading"
        :aria-invalid="!!fieldErrors.name"
        :class="inputClass"
      >
      <p v-if="fieldErrors.name" class="mt-1 text-xs text-destructive">
        {{ fieldErrors.name }}
      </p>
    </div>

    <!-- Description -->
    <div>
      <label for="description" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('products.description') }}
      </label>
      <textarea
        id="description"
        :value="form.description ?? ''"
        :disabled="loading"
        rows="3"
        :class="inputClass"
        @input="form.description = ($event.target as HTMLTextAreaElement).value || null"
      />
      <p v-if="fieldErrors.description" class="mt-1 text-xs text-destructive">
        {{ fieldErrors.description }}
      </p>
    </div>

    <!-- Prix + Prix min -->
    <div class="grid gap-4 sm:grid-cols-2">
      <div>
        <label for="price" class="mb-1 block text-sm font-medium text-foreground">
          {{ $t('products.price') }} *
        </label>
        <input
          id="price"
          v-model.number="form.price"
          type="number"
          inputmode="numeric"
          min="0"
          required
          :disabled="loading"
          :aria-invalid="!!fieldErrors.price"
          :class="inputClass"
        >
        <p v-if="fieldErrors.price" class="mt-1 text-xs text-destructive">
          {{ fieldErrors.price }}
        </p>
      </div>

      <div>
        <label for="min_price" class="mb-1 block text-sm font-medium text-foreground">
          {{ $t('products.minPrice') }} *
        </label>
        <input
          id="min_price"
          v-model.number="form.min_price"
          type="number"
          inputmode="numeric"
          min="0"
          required
          :disabled="loading"
          :aria-invalid="!!fieldErrors.min_price"
          :class="inputClass"
        >
        <p v-if="fieldErrors.min_price" class="mt-1 text-xs text-destructive">
          {{ fieldErrors.min_price }}
        </p>
        <p class="mt-1 text-xs text-muted-foreground">
          {{ $t('products.minPriceHint') }}
        </p>
      </div>
    </div>

    <!-- Stock -->
    <div class="grid gap-4 sm:grid-cols-2">
      <div>
        <label for="stock_quantity" class="mb-1 block text-sm font-medium text-foreground">
          {{ $t('products.stockQuantity') }}
        </label>
        <input
          id="stock_quantity"
          :value="form.stock_quantity ?? ''"
          type="number"
          inputmode="numeric"
          min="0"
          :disabled="loading"
          :class="inputClass"
          @input="
            form.stock_quantity = ($event.target as HTMLInputElement).value === ''
              ? null
              : Number(($event.target as HTMLInputElement).value)
          "
        >
        <p class="mt-1 text-xs text-muted-foreground">
          {{ $t('products.stockQuantityHint') }}
        </p>
      </div>

      <div>
        <label for="low_stock_threshold" class="mb-1 block text-sm font-medium text-foreground">
          {{ $t('products.lowStockThreshold') }}
        </label>
        <input
          id="low_stock_threshold"
          :value="form.low_stock_threshold ?? ''"
          type="number"
          inputmode="numeric"
          min="0"
          :disabled="loading"
          :class="inputClass"
          @input="
            form.low_stock_threshold = ($event.target as HTMLInputElement).value === ''
              ? null
              : Number(($event.target as HTMLInputElement).value)
          "
        >
      </div>
    </div>

    <!-- Mode rupture -->
    <div>
      <label for="out_of_stock_mode" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('products.outOfStockMode') }}
      </label>
      <select
        id="out_of_stock_mode"
        v-model="form.out_of_stock_mode"
        :disabled="loading"
        :class="inputClass"
      >
        <option value="waitlist">{{ $t('products.outOfStockWaitlist') }}</option>
        <option value="suspend">{{ $t('products.outOfStockSuspend') }}</option>
      </select>
    </div>

    <!-- Submit -->
    <div class="pt-2">
      <button
        type="submit"
        :disabled="loading"
        class="inline-flex items-center justify-center gap-2 rounded-md bg-brand-forest px-5 py-2.5 text-sm font-medium text-brand-gold transition hover:bg-brand-forest/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Loader2 v-if="loading" class="h-4 w-4 animate-spin" aria-hidden="true" />
        {{ loading ? t('common.loading') : t(submitLabelI18nKey) }}
      </button>
    </div>
  </form>
</template>
