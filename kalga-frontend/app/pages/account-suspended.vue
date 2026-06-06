<!--
  Page affichée quand un compte est désactivé (user.is_active === false).
  Référence : middleware/merchant.ts (redirect target)
-->

<script setup lang="ts">
import { ShieldAlert } from 'lucide-vue-next'

definePageMeta({ layout: 'empty' })

const { logout } = useAuth()
const { t } = useI18n()

useHead({ title: t('errors.accountSuspendedTitle') })
</script>

<template>
  <div class="w-full max-w-md text-center">
    <div
      class="mx-auto mb-6 inline-flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10 text-destructive"
    >
      <ShieldAlert class="h-8 w-8" aria-hidden="true" />
    </div>

    <h1 class="font-display text-2xl font-semibold text-primary">
      {{ $t('errors.accountSuspendedTitle') }}
    </h1>
    <p class="mt-2 text-sm text-muted-foreground">
      {{ $t('errors.accountSuspendedMessage') }}
    </p>

    <button
      type="button"
      class="mt-6 inline-flex items-center justify-center rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-warning transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      @click="logout"
    >
      {{ $t('auth.logout') }}
    </button>
  </div>
</template>
