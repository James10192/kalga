<!--
  Filtre de statut pour la liste des conversations.
  Émet `update:status` quand l'utilisateur change la sélection.
-->

<script setup lang="ts">
import { CONVERSATION_STATUS_VALUES } from '@/utils/constants'

interface Props {
  /** Statut sélectionné — undefined = tous */
  modelValue: string | undefined
}

defineProps<Props>()
const emit = defineEmits<{ 'update:modelValue': [value: string | undefined] }>()

function handleChange(event: Event): void {
  const value = (event.target as HTMLSelectElement).value
  emit('update:modelValue', value === '' ? undefined : value)
}
</script>

<template>
  <label class="inline-flex items-center gap-2 text-sm text-muted-foreground">
    {{ $t('conversations.filterByStatus') }}
    <select
      :value="modelValue ?? ''"
      class="rounded-md border border-input bg-card px-3 py-1.5 text-sm text-foreground transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      @change="handleChange"
    >
      <option value="">{{ $t('conversations.allStatuses') }}</option>
      <option v-for="status in CONVERSATION_STATUS_VALUES" :key="status" :value="status">
        {{ $t(`conversations.status.${status}`) }}
      </option>
    </select>
  </label>
</template>
