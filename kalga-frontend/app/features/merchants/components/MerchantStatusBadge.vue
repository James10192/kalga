<!--
  Badge actif/inactif d'un marchand.
-->

<script setup lang="ts">
interface Props {
  isActive: boolean
}

defineProps<Props>()
</script>

<template>
  <span
    :class="[
      'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
      isActive
        ? 'border border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-200'
        : 'border border-border bg-muted text-muted-foreground',
    ]"
  >
    <span aria-hidden="true" class="h-1.5 w-1.5 rounded-full bg-current" />
    {{ isActive ? $t('admin.merchantActive') : $t('admin.merchantInactive') }}
  </span>
</template>
