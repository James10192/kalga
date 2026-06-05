<!--
  Badge d'état de stock d'un produit.
  Référence : ARCHITECTURE_FRONTEND.md sections 7.5 + features/products
-->

<script setup lang="ts">
interface Props {
  /** Quantité en stock (null = non géré) */
  quantity: number | null
  /** Seuil pour considérer stock bas (null = pas de seuil) */
  lowThreshold: number | null
}

const props = defineProps<Props>()

const status = computed<'normal' | 'low' | 'out' | 'unmanaged'>(() => {
  if (props.quantity === null) return 'unmanaged'
  if (props.quantity <= 0) return 'out'
  if (props.lowThreshold !== null && props.quantity <= props.lowThreshold) return 'low'
  return 'normal'
})

const STATUS_CLASSES: Record<typeof status.value, string> = {
  normal: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-200 border border-emerald-500/20',
  low: 'bg-brand-gold/20 text-brand-forest border border-brand-gold/40',
  out: 'bg-destructive/10 text-destructive border border-destructive/20',
  unmanaged: 'bg-muted text-muted-foreground border border-border',
}

const I18N_KEY: Record<typeof status.value, string> = {
  normal: 'products.stockNormal',
  low: 'products.stockLow',
  out: 'products.stockOut',
  unmanaged: 'products.stockUnmanaged',
}
</script>

<template>
  <span
    :class="[
      'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
      STATUS_CLASSES[status],
    ]"
  >
    <span aria-hidden="true" class="h-1.5 w-1.5 rounded-full bg-current" />
    {{ $t(I18N_KEY[status]) }}
    <span v-if="quantity !== null" class="font-semibold">· {{ quantity }}</span>
  </span>
</template>
