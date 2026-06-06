<!--
  Sélecteur de plage temporelle (7j / 30j / 90j).
  Émet `update:modelValue` avec le preset choisi.
-->

<script setup lang="ts">
import { RANGE_PRESET_VALUES, type RangePreset } from '@/features/stats/utils/dateRange'

interface Props {
  modelValue: RangePreset
}

defineProps<Props>()
const emit = defineEmits<{ 'update:modelValue': [value: RangePreset] }>()
</script>

<template>
  <div
    class="inline-flex rounded-md border border-border bg-card p-0.5"
    role="radiogroup"
    :aria-label="$t('stats.rangeLabel')"
  >
    <button
      v-for="preset in RANGE_PRESET_VALUES"
      :key="preset"
      type="button"
      role="radio"
      :aria-checked="modelValue === preset"
      :class="[
        'rounded-sm px-3 py-1 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        modelValue === preset
          ? 'bg-primary text-warning'
          : 'text-foreground hover:bg-muted',
      ]"
      @click="emit('update:modelValue', preset)"
    >
      {{ $t(`stats.preset.${preset}`) }}
    </button>
  </div>
</template>
