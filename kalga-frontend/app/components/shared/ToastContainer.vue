<!--
  Conteneur de toasts — rendu de toutes les notifications actives.
  Référence : composables/useToast.ts

  À monter UNE SEULE FOIS par layout protégé (dashboard + admin).
  Position : bas droite (desktop), bas centre (mobile).
-->

<script setup lang="ts">
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-vue-next'
import type { Component } from 'vue'

import type { ToastType } from '@/composables/useToast'

const { toasts, dismiss } = useToast()

const ICON_MAP: Record<ToastType, Component> = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
}

const COLOR_CLASSES: Record<ToastType, string> = {
  success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-200',
  error: 'border-destructive/30 bg-destructive/10 text-destructive',
  info: 'border-brand-forest/30 bg-brand-forest/10 text-brand-forest',
}
</script>

<template>
  <div
    aria-live="polite"
    aria-atomic="false"
    class="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4 sm:inset-x-auto sm:right-4 sm:items-end"
  >
    <TransitionGroup
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        role="status"
        :class="[
          'pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-md border bg-card px-4 py-3 shadow-md',
          COLOR_CLASSES[toast.type],
        ]"
      >
        <component
          :is="ICON_MAP[toast.type]"
          class="mt-0.5 h-5 w-5 shrink-0"
          aria-hidden="true"
        />
        <p class="flex-1 text-sm font-medium">{{ toast.message }}</p>
        <button
          type="button"
          class="shrink-0 rounded-sm p-0.5 opacity-70 transition hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          :aria-label="$t('common.close')"
          @click="dismiss(toast.id)"
        >
          <X class="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>
