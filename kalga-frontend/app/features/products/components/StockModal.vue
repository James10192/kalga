<!--
  Modal de gestion du stock d'un produit.
  Référence : dashboard/static/app.js (showStockModal / saveStock).

  Sémantique backend : quantity = -1 → illimité (∞), 0 → épuisé, N → quantité.
  PUT /api/products/{code}/stock { quantity, low_stock_threshold }.
  Les valeurs initiales viennent du produit (déjà chargé dans la liste).
-->

<script setup lang="ts">
import { Infinity as InfinityIcon, Loader2, X } from 'lucide-vue-next'

import { useUpdateStock } from '../composables/useProducts'
import type { Product } from '../types'

interface Props {
  product: Product
}

const props = defineProps<Props>()
const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()
const { push } = useToast()
const { mutateAsync, isPending } = useUpdateStock()

const quantity = ref<number>(props.product.stock_quantity ?? -1)
const threshold = ref<number>(props.product.low_stock_threshold ?? 5)
const isUnlimited = computed(() => quantity.value === -1)

function setUnlimited(): void {
  quantity.value = -1
}

async function save(): Promise<void> {
  if (Number.isNaN(quantity.value) || quantity.value < -1) {
    push.error(t('products.stockInvalid'))
    return
  }
  try {
    await mutateAsync({
      code: props.product.code,
      data: { quantity: quantity.value, low_stock_threshold: threshold.value },
    })
    push.success(t('products.stockUpdated'))
    emit('close')
  } catch (error) {
    push.error(extractApiErrorMessage(error, t('products.stockUpdateError')))
  }
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-4"
    role="dialog"
    aria-modal="true"
    :aria-label="t('products.stockTitle')"
  >
    <div class="absolute inset-0 bg-black/50" @click="emit('close')" />

    <div class="relative w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-xl">
      <div class="mb-1 flex items-center justify-between">
        <h2 class="font-display text-lg font-semibold text-primary">
          {{ $t('products.stockTitle') }}
        </h2>
        <button
          type="button"
          class="rounded-md p-1 text-muted-foreground transition hover:bg-muted"
          :aria-label="$t('common.close')"
          @click="emit('close')"
        >
          <X class="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      <p class="mb-5 text-sm text-muted-foreground">
        {{ product.name }} · <strong>{{ product.code }}</strong>
      </p>

      <div class="space-y-4">
        <div>
          <label for="stock-qty" class="block text-sm font-medium text-foreground">
            {{ $t('products.stockQuantity') }}
          </label>
          <div class="mt-1 flex items-center gap-2">
            <input
              id="stock-qty"
              v-model.number="quantity"
              type="number"
              min="-1"
              class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
            <button
              type="button"
              :class="[
                'inline-flex shrink-0 items-center gap-1 rounded-md border px-3 py-2 text-xs font-medium transition',
                isUnlimited
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border bg-card text-foreground hover:bg-muted',
              ]"
              @click="setUnlimited"
            >
              <InfinityIcon class="h-3.5 w-3.5" aria-hidden="true" />
              {{ $t('products.unlimited') }}
            </button>
          </div>
          <p class="mt-1 text-xs text-muted-foreground">{{ $t('products.stockQuantityHint') }}</p>
        </div>

        <div>
          <label for="stock-threshold" class="block text-sm font-medium text-foreground">
            {{ $t('products.lowStockThreshold') }}
          </label>
          <input
            id="stock-threshold"
            v-model.number="threshold"
            type="number"
            min="0"
            class="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
        </div>
      </div>

      <div class="mt-6 flex justify-end gap-2">
        <button
          type="button"
          class="rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground transition hover:bg-muted"
          @click="emit('close')"
        >
          {{ $t('common.cancel') }}
        </button>
        <button
          type="button"
          :disabled="isPending"
          class="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary-hi disabled:cursor-not-allowed disabled:opacity-60"
          @click="save"
        >
          <Loader2 v-if="isPending" class="h-4 w-4 animate-spin" aria-hidden="true" />
          {{ $t('common.save') }}
        </button>
      </div>
    </div>
  </div>
</template>
