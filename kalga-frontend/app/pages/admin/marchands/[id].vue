<!--
  Détail d'un marchand côté admin : informations + statut + lien rapide.
-->

<script setup lang="ts">
import { ArrowLeft, Loader2 } from 'lucide-vue-next'

import MerchantStatusBadge from '@/features/merchants/components/MerchantStatusBadge.vue'
import { useMerchant } from '@/features/merchants/composables/useMerchants'
import { formatDate, formatPhone } from '@/utils/format'
import { ROUTES } from '@/utils/routes'

definePageMeta({ layout: 'admin' })

const { t, locale } = useI18n()
const route = useRoute()

const merchantId = computed(() => {
  const raw = route.params.id
  const id = Number(Array.isArray(raw) ? raw[0] : raw)
  return Number.isFinite(id) && id > 0 ? id : 0
})

const { data: merchant, isLoading, isError } = useMerchant(merchantId)

useHead({ title: () => merchant.value?.name ?? t('common.loading') })

const createdAt = computed(() =>
  merchant.value
    ? formatDate(merchant.value.created_at, locale.value === 'en' ? 'en-US' : 'fr-FR')
    : '',
)

const storefrontHref = computed(() =>
  merchant.value ? ROUTES.storefront.merchant(merchant.value.phone) : '#',
)
</script>

<template>
  <div class="space-y-6">
    <NuxtLink
      :to="ROUTES.admin.merchants"
      class="inline-flex items-center gap-1 text-sm text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <ArrowLeft class="h-4 w-4" aria-hidden="true" />
      {{ $t('admin.backToMerchants') }}
    </NuxtLink>

    <div
      v-if="isLoading"
      class="flex items-center justify-center rounded-lg border border-border bg-card py-16"
    >
      <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
    </div>

    <div
      v-else-if="isError || !merchant"
      role="alert"
      class="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center"
    >
      <p class="text-sm text-destructive">{{ $t('admin.loadError') }}</p>
    </div>

    <template v-else>
      <header class="rounded-lg border border-border bg-card p-6">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 class="font-display text-2xl font-semibold text-primary">
              {{ merchant.business_name ?? merchant.name }}
            </h1>
            <p class="text-sm text-muted-foreground">{{ merchant.name }}</p>
          </div>
          <MerchantStatusBadge :is-active="merchant.is_active" />
        </div>

        <dl class="mt-4 grid gap-3 sm:grid-cols-2">
          <div>
            <dt class="text-xs uppercase tracking-wider text-muted-foreground">
              {{ $t('admin.phone') }}
            </dt>
            <dd class="text-sm text-foreground">{{ formatPhone(merchant.phone) }}</dd>
          </div>
          <div>
            <dt class="text-xs uppercase tracking-wider text-muted-foreground">
              {{ $t('admin.createdAt') }}
            </dt>
            <dd class="text-sm text-foreground">{{ createdAt }}</dd>
          </div>
          <div v-if="merchant.address">
            <dt class="text-xs uppercase tracking-wider text-muted-foreground">
              {{ $t('admin.address') }}
            </dt>
            <dd class="text-sm text-foreground">
              {{ merchant.address }}
              <span v-if="merchant.city"> · {{ merchant.city }}</span>
            </dd>
          </div>
          <div v-if="merchant.payment_methods">
            <dt class="text-xs uppercase tracking-wider text-muted-foreground">
              {{ $t('admin.paymentMethods') }}
            </dt>
            <dd class="text-sm text-foreground">{{ merchant.payment_methods }}</dd>
          </div>
        </dl>
      </header>

      <section class="rounded-lg border border-border bg-card p-6">
        <h2 class="mb-3 font-display text-lg font-semibold text-primary">
          {{ $t('admin.quickActions') }}
        </h2>
        <div class="flex flex-wrap gap-3">
          <NuxtLink
            :to="storefrontHref"
            target="_blank"
            rel="noopener"
            class="inline-flex items-center justify-center rounded-md border border-primary px-4 py-2 text-sm font-medium text-primary transition hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {{ $t('admin.openStorefront') }}
          </NuxtLink>
        </div>
      </section>
    </template>
  </div>
</template>
