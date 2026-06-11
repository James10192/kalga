<!--
  Header applicatif réutilisable pour les zones authentifiées
  (dashboard marchand + admin).
  Référence : ARCHITECTURE_FRONTEND.md section 7.5

  Affiche :
  - Bouton hamburger (mobile uniquement)
  - Logo KALGA cliquable vers home
  - LangSwitcher
  - UserMenu (avatar + dropdown)
-->

<script setup lang="ts">
import { Menu } from 'lucide-vue-next'

interface Props {
  /** État courant du drawer mobile (v-model) */
  mobileNavOpen: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{ 'update:mobileNavOpen': [value: boolean] }>()

function handleToggleMobile(): void {
  emit('update:mobileNavOpen', !props.mobileNavOpen)
}
</script>

<template>
  <header
    class="sticky top-0 z-40 flex h-14 items-center justify-between gap-3 border-b border-border bg-card px-4 sm:px-6"
  >
    <div class="flex items-center gap-3">
      <button
        type="button"
        class="inline-flex items-center justify-center rounded-md p-2 text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring lg:hidden"
        :aria-label="$t('common.openMenu')"
        :aria-expanded="mobileNavOpen"
        @click="handleToggleMobile"
      >
        <Menu class="h-5 w-5" aria-hidden="true" />
      </button>

      <NuxtLink :to="'/'" class="lg:hidden">
        <KalgaLogo size="sm" :with-wordmark="false" />
      </NuxtLink>
    </div>

    <div class="flex items-center gap-2">
      <WhatsAppStatusBadge />
      <LangSwitcher />
      <UserMenu />
    </div>
  </header>
</template>
