<!--
  Placeholder pour l'étape post-login marchand (QR scan + onboarding).
  Référence : ARCHITECTURE_FRONTEND.md sections 3 + 7.1

  Cette page est intentionnellement minimale pour PR #2. Le port complet
  du QR + payment + activation + location vit dans la PR onboarding dédiée
  (cf. plan de portage HTML→Vue documenté avec le user).
-->

<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

definePageMeta({
  layout: false,
  middleware: [],
})

const { t } = useI18n()
const route = useRoute()

const phone = computed(() => {
  const raw = route.query.phone
  return Array.isArray(raw) ? (raw[0] ?? '') : (raw ?? '')
})

useHead({ title: t('auth.merchant.connectingTitle') })
</script>

<template>
  <main class="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#0a0a0a] px-6 py-12 text-center text-[hsl(120_18%_92%)]">
    <Loader2 class="h-10 w-10 animate-spin text-primary" aria-hidden="true" />
    <h1 class="font-display text-2xl font-semibold">
      {{ $t('auth.merchant.connectingTitle') }}
    </h1>
    <p class="max-w-md text-sm text-white/50">
      {{ $t('auth.merchant.connectingSubtitle', { phone }) }}
    </p>
    <p class="mt-4 max-w-md text-xs text-white/30">
      {{ $t('auth.merchant.connectingPlaceholder') }}
    </p>
  </main>
</template>
