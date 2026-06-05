<!--
  Header de la zone publique (storefront).
  Référence : ARCHITECTURE_FRONTEND.md section 7.5

  Design : sobre, fond crème, logo + nav + lang + cart.
  Style luxe Refined Heritage (typographie serif sur titres).
-->

<script setup lang="ts">
import { Menu, Search, ShoppingBag, X } from 'lucide-vue-next'
import { PUBLIC_NAV } from '@/utils/nav'
import { ROUTES } from '@/utils/routes'

const mobileOpen = ref(false)
const route = useRoute()

// Ferme le menu mobile à chaque changement de route
watch(() => route.path, () => {
  mobileOpen.value = false
})
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-border bg-card">
    <!-- Bandeau d'annonce -->
    <div class="bg-brand-deep px-4 py-1.5 text-center">
      <p class="text-xs text-brand-gold/90">
        {{ $t('storefront.heritageBanner') }}
      </p>
    </div>

    <!-- Nav principale -->
    <div class="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
      <!-- Gauche : menu mobile + logo -->
      <div class="flex items-center gap-3">
        <button
          type="button"
          class="inline-flex items-center justify-center rounded-md p-2 text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:hidden"
          :aria-label="$t('common.openMenu')"
          :aria-expanded="mobileOpen"
          @click="mobileOpen = !mobileOpen"
        >
          <Menu v-if="!mobileOpen" class="h-5 w-5" aria-hidden="true" />
          <X v-else class="h-5 w-5" aria-hidden="true" />
        </button>

        <NuxtLink :to="ROUTES.home" :aria-label="$t('common.home')">
          <KalgaLogo size="sm" />
        </NuxtLink>
      </div>

      <!-- Centre : nav (desktop) -->
      <nav class="hidden items-center gap-8 md:flex" :aria-label="$t('nav.primary')">
        <NuxtLink
          v-for="item in PUBLIC_NAV"
          :key="item.to"
          :to="item.to"
          class="text-sm font-medium text-foreground transition hover:text-brand-forest focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {{ $t(item.i18nKey) }}
        </NuxtLink>
      </nav>

      <!-- Droite : actions -->
      <div class="flex items-center gap-1">
        <button
          type="button"
          class="inline-flex items-center justify-center rounded-md p-2 text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          :aria-label="$t('storefront.search')"
        >
          <Search class="h-4 w-4" aria-hidden="true" />
        </button>
        <LangSwitcher />
        <button
          type="button"
          class="inline-flex items-center justify-center rounded-md p-2 text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          :aria-label="$t('storefront.cart')"
        >
          <ShoppingBag class="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>

    <!-- Drawer mobile -->
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <nav
        v-if="mobileOpen"
        class="border-t border-border bg-card px-4 py-3 md:hidden"
        :aria-label="$t('nav.mobile')"
      >
        <NuxtLink
          v-for="item in PUBLIC_NAV"
          :key="item.to"
          :to="item.to"
          class="block rounded-md px-3 py-2 text-sm font-medium text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:bg-muted"
        >
          {{ $t(item.i18nKey) }}
        </NuxtLink>
      </nav>
    </Transition>
  </header>
</template>
