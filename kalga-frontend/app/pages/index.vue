<!--
  Page d'accueil publique — landing storefront.
  Référence : ARCHITECTURE_FRONTEND.md sections 3 + 7.5

  Style: tokens depuis dashboard/static/style.css
-->

<script setup lang="ts">
import { ArrowRight, MessageCircle } from 'lucide-vue-next'
import { ROUTES } from '@/utils/routes'

useHead({
  title: 'KALGA',
  meta: [{ name: 'description', content: 'KALGA — Commerce WhatsApp automatisé' }],
})
</script>

<template>
  <div>
    <!-- Hero -->
    <section
      class="relative overflow-hidden border-b border-border bg-primary text-warning/90"
    >
      <div
        class="mx-auto grid max-w-7xl gap-10 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:items-center lg:py-28"
      >
        <div class="space-y-6">
          <span
            class="inline-flex rounded-full bg-warning px-4 py-1 text-xs font-semibold uppercase tracking-wider text-primary"
          >
            {{ $t('landing.heroTag') }}
          </span>

          <h1 class="font-display text-4xl font-bold leading-tight text-warning sm:text-5xl lg:text-6xl">
            {{ $t('landing.heroTitle') }}
          </h1>

          <p class="max-w-lg text-base text-warning/80 sm:text-lg">
            {{ $t('landing.heroSubtitle') }}
          </p>

          <div class="flex flex-col gap-3 pt-2 sm:flex-row">
            <NuxtLink
              :to="ROUTES.login"
              class="inline-flex items-center justify-center gap-2 rounded-md bg-warning px-5 py-3 text-sm font-semibold text-primary transition hover:bg-warning/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-warning focus-visible:ring-offset-2 focus-visible:ring-offset-primary"
            >
              {{ $t('landing.merchantCTA') }}
              <ArrowRight class="h-4 w-4" aria-hidden="true" />
            </NuxtLink>

            <a
              href="#features"
              class="inline-flex items-center justify-center gap-2 rounded-md border border-warning/40 px-5 py-3 text-sm font-medium text-warning transition hover:bg-warning/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-warning focus-visible:ring-offset-2 focus-visible:ring-offset-primary"
            >
              <MessageCircle class="h-4 w-4" aria-hidden="true" />
              {{ $t('landing.learnMore') }}
            </a>
          </div>
        </div>

        <div class="hidden lg:block">
          <div
            class="aspect-square rounded-lg bg-gradient-to-br from-warning/20 via-transparent to-warning/10 p-1"
          >
            <div
              class="flex h-full w-full items-center justify-center rounded-lg border border-warning/30 backdrop-blur-sm"
            >
              <KalgaLogo size="lg" :with-wordmark="false" />
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Section "Comment ça marche" -->
    <section id="features" class="mx-auto max-w-7xl px-4 py-20 sm:px-6">
      <div class="mb-12 max-w-2xl">
        <h2 class="font-display text-3xl font-bold text-primary sm:text-4xl">
          {{ $t('landing.featuresTitle') }}
        </h2>
        <p class="mt-3 text-base text-muted-foreground">
          {{ $t('landing.featuresSubtitle') }}
        </p>
      </div>

      <div class="grid gap-6 md:grid-cols-3">
        <article
          v-for="i in 3"
          :key="i"
          class="rounded-lg border border-border bg-card p-6 transition hover:shadow-sm"
        >
          <div
            class="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-md bg-primary text-warning"
          >
            <span class="font-display text-lg font-bold">{{ i }}</span>
          </div>
          <h3 class="font-display text-lg font-semibold text-primary">
            {{ $t(`landing.feature${i}Title`) }}
          </h3>
          <p class="mt-2 text-sm text-muted-foreground">
            {{ $t(`landing.feature${i}Body`) }}
          </p>
        </article>
      </div>
    </section>
  </div>
</template>
