<!--
  Carte KPI individuelle pour le dashboard stats.
  Référence : ARCHITECTURE_FRONTEND.md section 7.5
-->

<script setup lang="ts">
import * as LucideIcons from 'lucide-vue-next'
import type { Component } from 'vue'

interface Props {
  /** Clé i18n du libellé */
  labelI18nKey: string
  /** Valeur formatée (déjà localisée) */
  value: string | number
  /** Icône Lucide à afficher */
  icon: string
  /** Détail optionnel (sous-titre / quota) */
  hint?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  hint: null,
})

function iconFor(name: string): Component | null {
  const icons = LucideIcons as unknown as Record<string, Component>
  return icons[name] ?? null
}

const iconComponent = computed(() => iconFor(props.icon))
</script>

<template>
  <div class="rounded-lg border border-border bg-card p-4">
    <div class="flex items-center justify-between">
      <p class="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {{ $t(labelI18nKey) }}
      </p>
      <span
        v-if="iconComponent"
        class="inline-flex h-8 w-8 items-center justify-center rounded-md bg-brand-forest/10 text-brand-forest"
      >
        <component :is="iconComponent" class="h-4 w-4" aria-hidden="true" />
      </span>
    </div>

    <p class="mt-3 text-2xl font-semibold text-foreground">{{ value }}</p>

    <p v-if="hint" class="mt-1 text-xs text-muted-foreground">{{ hint }}</p>
  </div>
</template>
