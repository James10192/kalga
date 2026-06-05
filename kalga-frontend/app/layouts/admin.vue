<!--
  Layout du dashboard admin.
  Référence : ARCHITECTURE_FRONTEND.md sections 3 + 7.1 (auth) + 7.5

  Structure identique au dashboard marchand mais avec ADMIN_NAV et titre dédié.
-->

<script setup lang="ts">
import { ADMIN_NAV } from '@/utils/nav'

const mobileNavOpen = ref(false)
const route = useRoute()

watch(() => route.path, () => {
  mobileNavOpen.value = false
})
</script>

<template>
  <div class="flex min-h-screen bg-background text-foreground">
    <!-- Sidebar desktop -->
    <aside
      class="hidden w-64 shrink-0 border-r border-border bg-card lg:flex lg:flex-col"
      :aria-label="$t('nav.adminPanel')"
    >
      <div class="flex h-14 items-center border-b border-border px-5">
        <NuxtLink :to="'/'" class="inline-flex items-center" :aria-label="$t('common.home')">
          <KalgaLogo size="sm" />
        </NuxtLink>
      </div>

      <SidebarNav :items="ADMIN_NAV" title-i18n-key="nav.adminPanel" />
    </aside>

    <!-- Drawer mobile -->
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="mobileNavOpen"
        class="fixed inset-0 z-50 bg-foreground/50 lg:hidden"
        @click="mobileNavOpen = false"
      />
    </Transition>

    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="-translate-x-full"
      enter-to-class="translate-x-0"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="translate-x-0"
      leave-to-class="-translate-x-full"
    >
      <aside
        v-if="mobileNavOpen"
        class="fixed inset-y-0 left-0 z-50 w-64 border-r border-border bg-card lg:hidden"
        :aria-label="$t('nav.adminPanel')"
      >
        <div class="flex h-14 items-center border-b border-border px-5">
          <KalgaLogo size="sm" />
        </div>
        <SidebarNav :items="ADMIN_NAV" title-i18n-key="nav.adminPanel" />
      </aside>
    </Transition>

    <!-- Zone principale -->
    <div class="flex min-w-0 flex-1 flex-col">
      <AppHeader v-model:mobile-nav-open="mobileNavOpen" />

      <main class="flex-1 overflow-x-hidden p-4 sm:p-6 lg:p-8">
        <slot />
      </main>
    </div>

    <ToastContainer />
  </div>
</template>
