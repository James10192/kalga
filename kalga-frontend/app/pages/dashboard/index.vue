<!--
  Dashboard marchand — page d'accueil.
  Référence : ARCHITECTURE_FRONTEND.md section 3 (zone marchand)

  Page placeholder qui affiche le bonjour + initiale du marchand.
  À enrichir en Phase 7 avec stats temps réel + actions rapides.
-->

<script setup lang="ts">
definePageMeta({ layout: 'dashboard' })

const { user } = useAuth()
const { t } = useI18n()

useHead({ title: t('nav.overview') })
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-semibold text-foreground">
        {{ $t('dashboard.welcomeTitle', { email: user?.email ?? '' }) }}
      </h1>
      <p class="text-sm text-muted-foreground">{{ $t('dashboard.welcomeSubtitle') }}</p>
    </header>

    <div
      class="rounded-lg border border-dashed border-border bg-muted/30 p-8 text-center text-sm text-muted-foreground"
    >
      {{ $t('dashboard.emptyState') }}
    </div>
  </div>
</template>
