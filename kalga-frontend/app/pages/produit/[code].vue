<!--
  Page détail produit publique — /produit/:code.
  Référence : ARCHITECTURE_FRONTEND.md sections 3 (zone publique)
-->

<script setup lang="ts">
import { ArrowRight, ChevronLeft, ChevronRight, ImageOff, Loader2 } from 'lucide-vue-next'

import WhatsAppButton from '@/features/storefront/components/WhatsAppButton.vue'
import { useStorefrontContext } from '@/features/storefront/composables/useStorefrontContext'
import { useStorefrontProduct } from '@/features/storefront/composables/useStorefront'
import { formatPriceFCFA } from '@/utils/format'
import { ROUTES } from '@/utils/routes'

definePageMeta({ layout: 'storefront' })

const { t } = useI18n()
const route = useRoute()

const code = computed(() => {
  const raw = route.params.code
  return Array.isArray(raw) ? (raw[0] ?? '') : (raw ?? '')
})

// Le endpoint renvoie { product, variants, merchant } — on dérive les deux
// vues dont la page a besoin (le marchand porte le téléphone pour WhatsApp).
const { data, isLoading, isError } = useStorefrontProduct(code)
const product = computed(() => data.value?.product)
const merchant = computed(() => data.value?.merchant)
const variants = computed(() => data.value?.variants ?? [])
const hasVariants = computed(() => variants.value.length > 1)

// Renseigne le header (branding marchand) dès que le produit est chargé.
const storefrontContext = useStorefrontContext()
watchEffect(() => {
  if (merchant.value) storefrontContext.value = merchant.value
})

useHead({
  title: () => product.value?.name ?? t('storefront.productFallback'),
})

const orderHref = computed(() =>
  product.value ? ROUTES.storefront.order(product.value.code) : '#',
)

// Navigation circulaire entre variantes (flèches précédent / suivant).
const currentIndex = computed(() =>
  variants.value.findIndex((variant) => variant.code === product.value?.code),
)
const prevVariant = computed(() => {
  if (!hasVariants.value) return null
  const len = variants.value.length
  return variants.value[(currentIndex.value - 1 + len) % len] ?? null
})
const nextVariant = computed(() => {
  if (!hasVariants.value) return null
  const len = variants.value.length
  return variants.value[(currentIndex.value + 1) % len] ?? null
})
</script>

<template>
  <div>
    <!-- Loading -->
    <div v-if="isLoading" class="flex min-h-[60vh] items-center justify-center">
      <Loader2 class="h-8 w-8 animate-spin text-muted-foreground" aria-hidden="true" />
    </div>

    <!-- Erreur -->
    <div
      v-else-if="isError || !product"
      role="alert"
      class="mx-auto max-w-2xl px-4 py-20 text-center sm:px-6"
    >
      <h1 class="font-display text-2xl font-semibold text-primary">
        {{ $t('storefront.productNotFound') }}
      </h1>
      <p class="mt-2 text-sm text-muted-foreground">
        {{ $t('storefront.productNotFoundMessage') }}
      </p>
    </div>

    <main
      v-else
      class="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-2 lg:py-16"
    >
      <!-- Image + navigation entre variantes (flèches) -->
      <div class="relative aspect-square w-full overflow-hidden rounded-lg bg-muted">
        <img
          v-if="product.image_url"
          :src="product.image_url"
          :alt="product.name"
          class="h-full w-full object-cover"
          loading="eager"
        >
        <div
          v-else
          class="flex h-full w-full items-center justify-center text-muted-foreground"
        >
          <ImageOff class="h-16 w-16" aria-hidden="true" />
        </div>

        <template v-if="hasVariants">
          <NuxtLink
            v-if="prevVariant"
            :to="ROUTES.storefront.product(prevVariant.code)"
            class="absolute left-3 top-1/2 inline-flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-card/90 text-foreground shadow-md transition hover:bg-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            :aria-label="$t('storefront.prevVariant')"
          >
            <ChevronLeft class="h-5 w-5" aria-hidden="true" />
          </NuxtLink>
          <NuxtLink
            v-if="nextVariant"
            :to="ROUTES.storefront.product(nextVariant.code)"
            class="absolute right-3 top-1/2 inline-flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-card/90 text-foreground shadow-md transition hover:bg-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            :aria-label="$t('storefront.nextVariant')"
          >
            <ChevronRight class="h-5 w-5" aria-hidden="true" />
          </NuxtLink>

          <!-- Indicateur de position (point par variante) -->
          <div class="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-1.5">
            <span
              v-for="(variant, index) in variants"
              :key="variant.id"
              :class="[
                'h-1.5 rounded-full transition-all',
                index === currentIndex ? 'w-4 bg-primary' : 'w-1.5 bg-card/70',
              ]"
            />
          </div>
        </template>
      </div>

      <!-- Détails -->
      <div class="space-y-6">
        <header class="space-y-2">
          <span
            class="inline-flex items-center rounded-md bg-primary px-2 py-0.5 text-xs font-semibold uppercase tracking-wider text-warning"
          >
            {{ product.code }}
          </span>
          <h1 class="font-display text-3xl font-bold text-primary sm:text-4xl">
            {{ product.name }}
          </h1>
          <p
            v-if="product.variant_name"
            class="text-xs uppercase tracking-wider text-muted-foreground"
          >
            {{ product.variant_name }}
          </p>
        </header>

        <p class="text-2xl font-semibold text-foreground">
          {{ formatPriceFCFA(product.price) }}
        </p>

        <p v-if="product.description" class="text-sm leading-relaxed text-muted-foreground">
          {{ product.description }}
        </p>

        <!-- Sélecteur de variantes -->
        <div v-if="hasVariants" class="space-y-2">
          <p class="text-sm font-medium text-foreground">{{ $t('storefront.chooseVariant') }}</p>
          <div class="flex flex-wrap gap-2">
            <NuxtLink
              v-for="variant in variants"
              :key="variant.id"
              :to="ROUTES.storefront.product(variant.code)"
              :class="[
                'rounded-md border px-3 py-1.5 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                variant.code === product.code
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border bg-card text-foreground hover:bg-muted',
              ]"
            >
              {{ variant.variant_name || variant.name }}
            </NuxtLink>
          </div>
        </div>

        <div
          v-if="!product.in_stock"
          role="alert"
          class="rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-primary"
        >
          {{ $t('storefront.outOfStockNotice') }}
        </div>

        <div class="flex flex-col gap-3 pt-2 sm:flex-row">
          <NuxtLink
            :to="orderHref"
            class="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-5 py-3 text-sm font-semibold text-warning transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {{ $t('storefront.orderNow') }}
            <ArrowRight class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>

          <!-- Contact direct WhatsApp (message pré-rempli) — cf. storefront.js source de vérité -->
          <WhatsAppButton
            v-if="merchant"
            :phone="merchant.phone"
            :product-code="product.code"
            variant="outline"
          />
        </div>
      </div>
    </main>
  </div>
</template>
