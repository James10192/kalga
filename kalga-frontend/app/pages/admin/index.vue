<!--
  Dashboard admin — page d'accueil.
  Référence : ARCHITECTURE_FRONTEND.md section 3 (zone admin)
-->

<script setup lang="ts">
definePageMeta({ layout: 'admin' })

const { user } = useAuth()
const { t } = useI18n()

useHead({ title: t('nav.adminOverview') })
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-semibold text-foreground">
        {{ $t('admin.welcomeTitle', { email: user?.email ?? '' }) }}
      </h1>
      <p class="text-sm text-muted-foreground">{{ $t('admin.welcomeSubtitle') }}</p>
    </header>

    <div
      class="rounded-lg border border-dashed border-border bg-muted/30 p-8 text-center text-sm text-muted-foreground"
    >
      {{ $t('admin.emptyState') }}
    </div>
  </div>
</template>
