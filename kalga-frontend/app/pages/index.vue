<!--
  Page d'accueil publique — landing B2B SaaS pour MARCHANDS.
  Référence : KALGA_one_pager.html (philosophie) + prompt design (esthétique luxe).

  KALGA n'est PAS une marketplace : c'est un assistant IA WhatsApp qui transforme
  le WhatsApp d'un marchand en boutique automatisée. Cette page vend KALGA aux
  marchands (problème → solution → comment ça marche → CTA). Chaque marchand a
  ensuite SA vitrine (/boutique/:phone), distincte de cette landing.

  Couleurs/polices : 100 % via tokens (aucun hex en dur). Header/footer = layout.
-->

<script setup lang="ts">
import {
  ArrowRight,
  BellRing,
  Brain,
  Clock,
  MessageCircle,
  MessagesSquare,
  Package,
  QrCode,
  Sparkles,
  Store,
  TrendingDown,
} from 'lucide-vue-next'

import { ROUTES } from '@/utils/routes'

const { t } = useI18n()

useHead({
  title: 'KALGA — ' + t('landing.heroBadge'),
  meta: [{ name: 'description', content: t('landing.heroSubtitle') }],
})

const problems = [
  { icon: MessagesSquare, key: 'problem1' },
  { icon: Clock, key: 'problem2' },
  { icon: TrendingDown, key: 'problem3' },
  { icon: BellRing, key: 'problem4' },
] as const

const solutions = [
  { icon: Brain, title: 'solution1Title', body: 'solution1Body' },
  { icon: MessageCircle, title: 'solution2Title', body: 'solution2Body' },
  { icon: Store, title: 'solution3Title', body: 'solution3Body' },
  { icon: Package, title: 'solution4Title', body: 'solution4Body' },
] as const

const steps = [
  { icon: QrCode, title: 'step1Title', body: 'step1Body' },
  { icon: Package, title: 'step2Title', body: 'step2Body' },
  { icon: Sparkles, title: 'step3Title', body: 'step3Body' },
] as const

// Vitrine de démonstration (un vrai marchand) — lien « Voir une vitrine ».
const demoStorefront = ROUTES.storefront.merchant('225161407534')
</script>

<template>
  <div>
    <!-- ============ HERO ============ -->
    <section class="relative flex min-h-[88vh] items-center overflow-hidden">
      <img
        src="https://picsum.photos/seed/kalga-merchant/1920/1080"
        alt=""
        aria-hidden="true"
        class="absolute inset-0 h-full w-full object-cover"
        loading="eager"
      >
      <div class="absolute inset-0 bg-gradient-to-br from-primary/85 via-primary/70 to-primary/90" />

      <div class="relative z-10 mx-auto w-full max-w-7xl px-4 py-24 sm:px-6">
        <div class="max-w-2xl space-y-6">
          <span
            class="inline-flex items-center gap-2 rounded-full bg-gold px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-gold-foreground"
          >
            <MessageCircle class="h-3.5 w-3.5" aria-hidden="true" />
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
              :to="ROUTES.login"
              class="inline-flex items-center justify-center gap-2 rounded-lg bg-gold px-8 py-4 text-sm font-semibold text-gold-foreground shadow-md transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary"
            >
              {{ $t('landing.heroPrimary') }}
              <ArrowRight class="h-4 w-4" aria-hidden="true" />
            </NuxtLink>

            <NuxtLink
              :to="demoStorefront"
              class="inline-flex items-center justify-center gap-2 rounded-lg border-2 border-white/80 px-8 py-4 text-sm font-semibold text-white transition hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            >
              <Store class="h-4 w-4" aria-hidden="true" />
              {{ $t('landing.heroSecondary') }}
            </NuxtLink>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ LE PROBLÈME ============ -->
    <section class="bg-surface-2 py-16">
      <div class="mx-auto max-w-7xl px-4 sm:px-6">
        <h2 class="max-w-3xl font-display text-3xl font-bold text-primary sm:text-4xl">
          {{ $t('landing.problemTitle') }}
        </h2>

        <div class="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div
            v-for="problem in problems"
            :key="problem.key"
            class="flex items-start gap-4 rounded-xl border border-border bg-card p-5"
          >
            <span
              class="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-destructive/10 text-destructive"
            >
              <component :is="problem.icon" class="h-5 w-5" aria-hidden="true" />
            </span>
            <p class="text-sm leading-relaxed text-foreground">
              {{ $t(`landing.${problem.key}`) }}
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ LA SOLUTION ============ -->
    <section class="mx-auto max-w-7xl px-4 py-16 sm:px-6">
      <h2 class="max-w-3xl font-display text-3xl font-bold text-primary sm:text-4xl">
        {{ $t('landing.solutionTitle') }}
      </h2>

      <div class="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <article
          v-for="solution in solutions"
          :key="solution.title"
          class="rounded-xl border border-border bg-card p-6 transition duration-300 hover:-translate-y-1 hover:shadow-lg"
        >
          <span
            class="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-primary-lo text-primary"
          >
            <component :is="solution.icon" class="h-6 w-6" aria-hidden="true" />
          </span>
          <h3 class="mt-4 font-display text-lg font-semibold text-foreground">
            {{ $t(`landing.${solution.title}`) }}
          </h3>
          <p class="mt-2 text-sm leading-relaxed text-muted-foreground">
            {{ $t(`landing.${solution.body}`) }}
          </p>
        </article>
      </div>
    </section>

    <!-- ============ COMMENT ÇA MARCHE ============ -->
    <section class="bg-surface-2 py-16">
      <div class="mx-auto max-w-7xl px-4 sm:px-6">
        <h2 class="text-center font-display text-3xl font-bold text-primary sm:text-4xl">
          {{ $t('landing.stepsTitle') }}
        </h2>

        <div class="mt-12 grid grid-cols-1 gap-8 md:grid-cols-3">
          <div
            v-for="(step, index) in steps"
            :key="step.title"
            class="relative text-center"
          >
            <span
              class="mx-auto inline-flex h-16 w-16 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md"
            >
              <component :is="step.icon" class="h-7 w-7" aria-hidden="true" />
            </span>
            <span class="mt-4 block font-display text-sm font-semibold text-gold">
              {{ String(index + 1).padStart(2, '0') }}
            </span>
            <h3 class="mt-1 font-display text-xl font-semibold text-foreground">
              {{ $t(`landing.${step.title}`) }}
            </h3>
            <p class="mx-auto mt-2 max-w-xs text-sm leading-relaxed text-muted-foreground">
              {{ $t(`landing.${step.body}`) }}
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ CTA FINAL ============ -->
    <section class="bg-primary py-20">
      <div class="mx-auto max-w-3xl px-4 text-center sm:px-6">
        <h2 class="font-display text-3xl font-bold text-white sm:text-4xl">
          {{ $t('landing.ctaTitle') }}
        </h2>
        <p class="mx-auto mt-4 max-w-xl text-base text-white/80">
          {{ $t('landing.ctaSubtitle') }}
        </p>
        <NuxtLink
          :to="ROUTES.login"
          class="mt-8 inline-flex items-center justify-center gap-2 rounded-lg bg-gold px-8 py-4 text-sm font-semibold text-gold-foreground shadow-md transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary"
        >
          {{ $t('landing.ctaButton') }}
          <ArrowRight class="h-4 w-4" aria-hidden="true" />
        </NuxtLink>
      </div>
    </section>

    <!-- ============ CHAT FLOTTANT ============ -->
    <ChatFAB />
  </div>
</template>
