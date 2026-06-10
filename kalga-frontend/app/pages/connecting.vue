<!--
  Onboarding marchand — scan du QR WhatsApp puis ouverture de session.
  Référence : ARCHITECTURE_FRONTEND.md §3 + §7.1 ; modèle réel KALGA.

  La logique (poll statut bridge → établir la session → rediriger) est dans le
  composable useWhatsappConnection. Cette page ne fait que présenter les états.
  Couleurs via tokens (aucun hex en dur).
-->

<script setup lang="ts">
import QrcodeVue from 'qrcode.vue'
import { CheckCircle2, Loader2, MessageCircle, QrCode } from 'lucide-vue-next'

import { useWhatsappConnection } from '@/features/auth/composables/useWhatsappConnection'
import { ROUTES } from '@/utils/routes'

definePageMeta({ layout: false })

const { t } = useI18n()
const route = useRoute()

const phone = computed(() => {
  const raw = route.query.phone
  return Array.isArray(raw) ? (raw[0] ?? '') : (raw ?? '')
})

const { qrCode, connected, establishing, error } = useWhatsappConnection(phone)

useHead({ title: t('auth.merchant.connectingTitle') })
</script>

<template>
  <main
    class="flex min-h-screen flex-col items-center justify-center gap-6 bg-background px-6 py-12 text-center text-foreground"
  >
    <KalgaLogo size="md" />

    <!-- Numéro manquant -->
    <div v-if="!phone" class="max-w-sm space-y-3" role="alert">
      <p class="text-sm text-muted-foreground">{{ $t('auth.merchant.noPhone') }}</p>
      <NuxtLink
        :to="ROUTES.login"
        class="inline-flex items-center justify-center rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:bg-primary-hi"
      >
        {{ $t('common.back') }}
      </NuxtLink>
    </div>

    <!-- Session en cours d'ouverture (connecté) -->
    <div v-else-if="establishing || connected" class="max-w-sm space-y-3">
      <CheckCircle2 class="mx-auto h-12 w-12 text-success" aria-hidden="true" />
      <h1 class="font-display text-2xl font-semibold text-primary">
        {{ $t('auth.merchant.connectedRedirect') }}
      </h1>
      <Loader2 class="mx-auto h-5 w-5 animate-spin text-muted-foreground" aria-hidden="true" />
    </div>

    <!-- QR à scanner -->
    <div v-else class="max-w-md space-y-5">
      <div class="space-y-1">
        <h1 class="font-display text-2xl font-semibold text-primary">
          {{ $t('auth.merchant.connectingTitle') }}
        </h1>
        <p class="text-sm text-muted-foreground">
          {{ $t('auth.merchant.connectingSubtitle') }}
        </p>
      </div>

      <div
        class="mx-auto flex h-[252px] w-[252px] items-center justify-center rounded-xl border border-border bg-card p-4"
      >
        <ClientOnly>
          <QrcodeVue v-if="qrCode" :value="qrCode" :size="220" level="M" />
          <div v-else class="flex flex-col items-center gap-3 text-muted-foreground">
            <Loader2 class="h-8 w-8 animate-spin" aria-hidden="true" />
            <span class="text-xs">{{ $t('auth.merchant.qrInitializing') }}</span>
          </div>
          <template #fallback>
            <QrCode class="h-10 w-10 text-muted-foreground" aria-hidden="true" />
          </template>
        </ClientOnly>
      </div>

      <p
        class="mx-auto flex max-w-xs items-center justify-center gap-2 text-sm text-muted-foreground"
      >
        <MessageCircle class="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
        {{ $t('auth.merchant.qrScanInstruction') }}
      </p>

      <p v-if="error" role="alert" class="text-sm text-destructive">
        {{ $t('auth.merchant.sessionError') }}
      </p>
    </div>
  </main>
</template>
