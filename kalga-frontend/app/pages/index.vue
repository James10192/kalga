<!--
  Page d'accueil publique — vitrine « Luxe africain ».
  Référence : prompt design KALGA + ARCHITECTURE_FRONTEND.md §3 / §5.4 (tokens).

  Sections : Hero (image + overlay) · Recherche · Tendances · Guildes curatées.
  Header + footer fournis par le layout `default`. Le chat flottant (FAB) est
  ajouté ici. Couleurs/polices : 100 % via tokens (aucun hex en dur).

  Données DÉMO (produits/catégories) : placeholders. Le branchement aux vraies
  données (API storefront) se fera dans une PR de câblage dédiée. Images : Picsum
  (rendu garanti) — remplacées par les visuels marchands réels ensuite.
-->

<script setup lang="ts">
import { ArrowRight, Heart, MessageCircle, Search } from 'lucide-vue-next'

import { formatPriceFCFA } from '@/utils/format'
import { ROUTES } from '@/utils/routes'

const { t } = useI18n()

useHead({
  title: 'KALGA — ' + t('landing.heroBadge'),
  meta: [{ name: 'description', content: t('landing.heroSubtitle') }],
})

interface DemoProduct {
  readonly id: number
  readonly name: string
  readonly collection: string
  readonly price: number
  readonly image: string
  readonly limited: boolean
}

interface DemoCategory {
  readonly id: number
  readonly name: string
  readonly image: string
}

// Données de démonstration (placeholders) — voir entête.
const products: ReadonlyArray<DemoProduct> = [
  { id: 1, name: 'Pagne Kente Royal', collection: 'Tissage', price: 125000, image: 'https://picsum.photos/seed/kalga-kente/640/480', limited: true },
  { id: 2, name: 'Collier Touareg', collection: 'Argent', price: 89000, image: 'https://picsum.photos/seed/kalga-touareg/640/480', limited: false },
  { id: 3, name: 'Masque Sénoufo', collection: 'Sculpture', price: 210000, image: 'https://picsum.photos/seed/kalga-masque/640/480', limited: true },
  { id: 4, name: 'Boubou brodé main', collection: 'Couture', price: 156000, image: 'https://picsum.photos/seed/kalga-boubou/640/480', limited: false },
  { id: 5, name: 'Panier Bolga', collection: 'Vannerie', price: 42000, image: 'https://picsum.photos/seed/kalga-bolga/640/480', limited: false },
  { id: 6, name: 'Bracelet en bronze', collection: 'Orfèvrerie', price: 67000, image: 'https://picsum.photos/seed/kalga-bronze/640/480', limited: true },
]

const categories: ReadonlyArray<DemoCategory> = [
  { id: 1, name: 'Textiles', image: 'https://picsum.photos/seed/kalga-cat-textile/600/600' },
  { id: 2, name: 'Bijoux', image: 'https://picsum.photos/seed/kalga-cat-bijoux/600/600' },
  { id: 3, name: 'Sculpture', image: 'https://picsum.photos/seed/kalga-cat-sculpture/600/600' },
  { id: 4, name: 'Maroquinerie', image: 'https://picsum.photos/seed/kalga-cat-cuir/600/600' },
]
</script>

<template>
  <div>
    <!-- ============ 1. HERO ============ -->
    <section class="relative flex min-h-[88vh] items-center overflow-hidden">
      <!-- Image de fond + overlay vert -->
      <img
        src="https://picsum.photos/seed/kalga-hero/1920/1080"
        alt=""
        aria-hidden="true"
        class="absolute inset-0 h-full w-full object-cover"
        loading="eager"
      >
      <div class="absolute inset-0 bg-gradient-to-br from-primary/80 via-primary/60 to-primary/80" />

      <div class="relative z-10 mx-auto w-full max-w-7xl px-4 py-24 sm:px-6">
        <div class="max-w-2xl space-y-6">
          <span
            class="inline-flex rounded-full bg-gold px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-gold-foreground"
          >
            {{ $t('landing.heroBadge') }}
          </span>

          <h1 class="font-display text-4xl font-bold leading-tight text-white sm:text-5xl lg:text-6xl">
            {{ $t('landing.heroTitle') }}
          </h1>

          <p class="max-w-xl text-base leading-relaxed text-white/85 sm:text-lg">
            {{ $t('landing.heroSubtitle') }}
          </p>

          <div class="flex flex-col gap-3 pt-2 sm:flex-row">
            <NuxtLink
              :to="'/#trending'"
              class="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-8 py-4 text-sm font-semibold text-primary-foreground shadow-md transition hover:bg-primary-hi focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-primary"
            >
              {{ $t('landing.heroPrimary') }}
              <ArrowRight class="h-4 w-4" aria-hidden="true" />
            </NuxtLink>

            <NuxtLink
              :to="ROUTES.login"
              class="inline-flex items-center justify-center gap-2 rounded-lg border-2 border-white/80 px-8 py-4 text-sm font-semibold text-white transition hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            >
              <MessageCircle class="h-4 w-4" aria-hidden="true" />
              {{ $t('landing.heroSecondary') }}
            </NuxtLink>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ 2. BARRE DE RECHERCHE ============ -->
    <section class="bg-surface-2 py-10">
      <div class="mx-auto max-w-3xl px-4 sm:px-6">
        <form
          class="flex items-center gap-2 rounded-lg border border-border bg-card p-2 shadow-sm"
          @submit.prevent
        >
          <Search class="ml-2 h-5 w-5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <input
            type="search"
            :placeholder="$t('landing.searchPlaceholder')"
            :aria-label="$t('landing.searchPlaceholder')"
            class="min-w-0 flex-1 bg-transparent px-1 py-2 text-sm text-foreground outline-none placeholder:text-muted-foreground"
          >
          <button
            type="submit"
            class="shrink-0 rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:bg-primary-hi focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {{ $t('landing.searchButton') }}
          </button>
        </form>
      </div>
    </section>

    <!-- ============ 3. TENDANCES ============ -->
    <section id="trending" class="mx-auto max-w-7xl px-4 py-16 sm:px-6">
      <div class="mb-10 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 class="font-display text-3xl font-bold text-primary sm:text-4xl">
            {{ $t('landing.trendingTitle') }}
          </h2>
          <p class="mt-2 text-base text-muted-foreground">
            {{ $t('landing.trendingSubtitle') }}
          </p>
        </div>
        <NuxtLink
          :to="'/#trending'"
          class="inline-flex items-center gap-1 text-sm font-semibold text-gold transition hover:opacity-80"
        >
          {{ $t('landing.viewAll') }}
          <ArrowRight class="h-4 w-4" aria-hidden="true" />
        </NuxtLink>
      </div>

      <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="product in products"
          :key="product.id"
          class="group cursor-pointer overflow-hidden rounded-xl border border-border bg-card transition duration-300 hover:-translate-y-1 hover:shadow-lg"
        >
          <div class="relative aspect-[4/3] w-full overflow-hidden">
            <img
              :src="product.image"
              :alt="product.name"
              class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
              loading="lazy"
            >
            <span
              v-if="product.limited"
              class="absolute bottom-3 left-3 rounded-full bg-primary px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-wider text-primary-foreground"
            >
              {{ $t('landing.limitedEdition') }}
            </span>
            <button
              type="button"
              class="absolute right-3 top-3 inline-flex h-9 w-9 items-center justify-center rounded-full bg-card text-foreground shadow-md transition hover:text-gold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              :aria-label="product.name"
            >
              <Heart class="h-4 w-4" aria-hidden="true" />
            </button>
          </div>

          <div class="space-y-1 p-4">
            <p class="text-xs uppercase tracking-wider text-muted-foreground">
              {{ product.collection }}
            </p>
            <h3 class="font-display text-lg font-semibold text-foreground">
              {{ product.name }}
            </h3>
            <p class="pt-1 text-sm font-semibold text-gold">
              {{ formatPriceFCFA(product.price) }}
            </p>
          </div>
        </article>
      </div>
    </section>

    <!-- ============ 4. GUILDES CURATÉES (catégories) ============ -->
    <section class="bg-surface-2 py-16">
      <div class="mx-auto max-w-7xl px-4 sm:px-6">
        <div class="mb-10 text-center">
          <h2 class="font-display text-3xl font-bold text-primary sm:text-4xl">
            {{ $t('landing.categoriesTitle') }}
          </h2>
          <p class="mt-2 text-base text-muted-foreground">
            {{ $t('landing.categoriesSubtitle') }}
          </p>
        </div>

        <div class="grid grid-cols-2 gap-4 sm:gap-6 lg:grid-cols-4">
          <NuxtLink
            v-for="category in categories"
            :key="category.id"
            :to="'/#trending'"
            class="group relative block aspect-square overflow-hidden rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface-2"
          >
            <img
              :src="category.image"
              :alt="category.name"
              class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
              loading="lazy"
            >
            <div class="absolute inset-0 bg-gradient-to-t from-primary/90 via-primary/30 to-transparent transition group-hover:from-primary" />
            <span
              class="absolute inset-x-0 bottom-0 p-4 text-center font-display text-lg font-semibold text-white"
            >
              {{ category.name }}
            </span>
          </NuxtLink>
        </div>
      </div>
    </section>

    <!-- ============ 6. CHAT FLOTTANT ============ -->
    <ChatFAB />
  </div>
</template>
