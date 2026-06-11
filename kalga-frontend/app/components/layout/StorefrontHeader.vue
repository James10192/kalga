<!--
  Header de la VITRINE CLIENT (boutique / produit / commande).
  Référence : storefront/static/storefront.js (renderNav).

  Affiche le branding du MARCHAND (logo + nom de la boutique) — PAS la nav de la
  plateforme (Accueil/Catalogue/Marchand/Admin), qui n'a pas de sens pour un
  client. Le marchand courant vient de useStorefrontMerchant (renseigné par la
  page). Actions : thème, langue, panier.
-->

<script setup lang="ts">
import { ShoppingBag } from 'lucide-vue-next'

import { useStorefrontContext } from '@/features/storefront/composables/useStorefrontContext'
import { ROUTES } from '@/utils/routes'

const merchant = useStorefrontContext()

const storeName = computed(
  () => merchant.value?.business_name || merchant.value?.name || 'KALGA',
)
const initials = computed(() => storeName.value.slice(0, 2).toUpperCase())
const homeHref = computed(() =>
  merchant.value ? ROUTES.storefront.merchant(merchant.value.phone) : ROUTES.home,
)
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-border bg-card">
    <div class="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
      <!-- Branding marchand -->
      <NuxtLink
        :to="homeHref"
        class="flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <img
          v-if="merchant?.logo_url"
          :src="merchant.logo_url"
          alt=""
          class="h-9 w-9 shrink-0 rounded-full object-cover"
        >
        <span
          v-else
          class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground"
        >
          {{ initials }}
        </span>
        <span class="line-clamp-1 font-display text-lg font-semibold text-primary">
          {{ storeName }}
        </span>
      </NuxtLink>

      <!-- Actions client -->
      <div class="flex items-center gap-1">
        <ThemeToggle />
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
  </header>
</template>
