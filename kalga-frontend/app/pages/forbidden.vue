<!--
  Page 403 — accès refusé.
  Référence : routes.ts:ROUTES.errors.forbidden
-->

<script setup lang="ts">
import { Lock } from 'lucide-vue-next'
import { ROUTES } from '@/utils/routes'

definePageMeta({ layout: 'empty' })

const { t } = useI18n()
useHead({ title: t('errors.forbiddenTitle') })
</script>

<template>
  <div class="w-full max-w-md text-center">
    <div
      class="mx-auto mb-6 inline-flex h-16 w-16 items-center justify-center rounded-full bg-muted text-muted-foreground"
    >
      <Lock class="h-8 w-8" aria-hidden="true" />
    </div>

    <h1 class="font-serif text-2xl font-semibold text-brand-forest">
      {{ $t('errors.forbiddenTitle') }}
    </h1>
    <p class="mt-2 text-sm text-muted-foreground">
      {{ $t('errors.forbiddenMessage') }}
    </p>

    <NuxtLink
      :to="ROUTES.home"
      class="mt-6 inline-flex items-center justify-center rounded-md bg-brand-forest px-5 py-2.5 text-sm font-medium text-brand-gold transition hover:bg-brand-forest/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {{ $t('errors.backHome') }}
    </NuxtLink>
  </div>
</template>
