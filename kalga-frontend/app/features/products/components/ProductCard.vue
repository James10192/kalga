<!--
  Carte produit — affichage dans la liste (alignée sur dashboard/static/app.js).

  Affiche un GROUPE de variantes : produit principal + chips de variantes,
  les deux prix (affiché + minimum), le badge stock, et les actions du
  dashboard réel : Stock (émis vers la page), Copier le code, Supprimer (émis).
  Pas de page détail : KALGA ne permet pas l'édition d'un produit (on supprime
  et on recrée via WhatsApp).
-->

<script setup lang="ts">
import { Boxes, Copy, ImageOff, Trash2 } from 'lucide-vue-next'

import { formatPriceFCFA } from '@/utils/format'
import type { Product } from '../types'
import type { ProductGroup } from '../utils/groupVariants'

interface Props {
  group: ProductGroup<Product>
}

const props = defineProps<Props>()
const emit = defineEmits<{
  manageStock: [product: Product]
  delete: [product: Product]
}>()

const { t } = useI18n()
const { push } = useToast()

const main = computed(() => props.group.main)
const hasVariants = computed(() => props.group.variants.length > 1)

const imageSrc = computed<string | null>(() => {
  const path = main.value.image_path
  if (!path) return null
  // `image_path` = nom de fichier nu ; servi par le backend sous /uploads/,
  // relayé par server/routes/uploads/[...path].ts.
  return path.startsWith('/uploads/') ? path : `/uploads/${path}`
})

async function copyCode(): Promise<void> {
  try {
    await navigator.clipboard.writeText(main.value.code)
    push.success(t('products.codeCopied', { code: main.value.code }))
  } catch {
    push.error(t('products.copyError'))
  }
}
</script>

<template>
  <article
    class="flex flex-col overflow-hidden rounded-lg border border-border bg-card transition hover:shadow-sm"
  >
    <div class="relative aspect-square w-full overflow-hidden bg-muted">
      <img
        v-if="imageSrc"
        :src="imageSrc"
        :alt="group.displayName"
        class="h-full w-full object-cover"
        loading="lazy"
      >
      <div
        v-else
        class="flex h-full w-full items-center justify-center text-muted-foreground"
        :aria-label="$t('products.noImage')"
      >
        <ImageOff class="h-10 w-10" aria-hidden="true" />
      </div>

      <span
        class="absolute left-2 top-2 rounded-md bg-primary px-2 py-0.5 text-xs font-semibold text-primary-foreground"
      >
        {{ main.code }}
      </span>
      <StockBadge
        class="absolute right-2 top-2"
        :quantity="main.stock_quantity"
        :low-threshold="main.low_stock_threshold"
      />
    </div>

    <div class="flex flex-1 flex-col gap-3 p-4">
      <div>
        <h3 class="line-clamp-1 font-display text-base font-medium text-foreground">
          {{ group.displayName }}
        </h3>
        <p v-if="main.description" class="mt-1 line-clamp-2 text-xs text-muted-foreground">
          {{ main.description }}
        </p>
      </div>

      <!-- Variantes -->
      <div v-if="hasVariants" class="flex flex-wrap gap-1">
        <span
          v-for="variant in group.variants"
          :key="variant.id"
          :title="variant.code"
          class="rounded-full border border-border bg-muted px-2 py-0.5 text-[0.65rem] text-muted-foreground"
        >
          {{ variant.variant_name || $t('products.mainVariant') }}
        </span>
      </div>

      <!-- Prix : affiché + minimum -->
      <div class="grid grid-cols-2 gap-2 rounded-md bg-muted/40 p-2">
        <div>
          <p class="text-[0.65rem] uppercase tracking-wide text-muted-foreground">
            {{ $t('products.price') }}
          </p>
          <p class="text-sm font-semibold text-foreground">{{ formatPriceFCFA(main.price) }}</p>
        </div>
        <div>
          <p class="text-[0.65rem] uppercase tracking-wide text-muted-foreground">
            {{ $t('products.minPrice') }}
          </p>
          <p class="text-sm font-semibold text-gold">{{ formatPriceFCFA(main.min_price) }}</p>
        </div>
      </div>

      <!-- Actions : Stock · Copier · Supprimer -->
      <div class="mt-auto flex items-center gap-2 pt-1">
        <button
          type="button"
          class="inline-flex flex-1 items-center justify-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          @click="emit('manageStock', main)"
        >
          <Boxes class="h-3.5 w-3.5" aria-hidden="true" />
          {{ $t('products.stock') }}
        </button>
        <button
          type="button"
          class="inline-flex items-center justify-center rounded-md border border-border bg-card p-1.5 text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          :aria-label="$t('products.copyCode')"
          :title="$t('products.copyCode')"
          @click="copyCode"
        >
          <Copy class="h-3.5 w-3.5" aria-hidden="true" />
        </button>
        <button
          type="button"
          class="inline-flex items-center justify-center rounded-md border border-destructive/40 bg-card p-1.5 text-destructive transition hover:bg-destructive/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive"
          :aria-label="$t('common.delete')"
          :title="$t('common.delete')"
          @click="emit('delete', main)"
        >
          <Trash2 class="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </div>
    </div>
  </article>
</template>
