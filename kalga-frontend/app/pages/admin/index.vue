<!--
  Dashboard admin — Vue d'ensemble.
  Porté depuis dashboard/admin.html (#section-overview) : stat-cards plateforme
  (marchands, conversations, ventes, messages) + abonnements par plan.
  Données : GET /admin/dashboard.
-->

<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

import { useAdminDashboard } from '@/features/admin/composables/useAdmin'
import KpiCard from '@/features/stats/components/KpiCard.vue'

definePageMeta({ layout: 'admin' })

const { user } = useAuth()
const { t } = useI18n()

const { data: dashboard, isLoading, isError } = useAdminDashboard()

useHead({ title: t('nav.adminOverview') })

const planEntries = computed(() => Object.entries(dashboard.value?.subscriptions.by_plan ?? {}))
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-semibold text-foreground">
        {{ $t('admin.welcomeTitle', { email: user?.email ?? '' }) }}
      </h1>
      <p class="text-sm text-muted-foreground">{{ $t('admin.welcomeSubtitle') }}</p>
    </header>

    <!-- Loading -->
    <div
      v-if="isLoading"
      class="flex items-center justify-center rounded-lg border border-border bg-card py-16"
    >
      <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
    </div>

    <!-- Erreur -->
    <div
      v-else-if="isError || !dashboard"
      role="alert"
      class="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center"
    >
      <p class="text-sm text-destructive">{{ $t('admin.loadError') }}</p>
    </div>

    <template v-else>
      <!-- Stat-cards plateforme -->
      <section class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" :aria-label="$t('admin.statsLabel')">
        <KpiCard
          label-i18n-key="admin.statMerchants"
          icon="Users"
          :value="dashboard.merchants.total"
          :hint="
            t('admin.statMerchantsSub', {
              active: dashboard.merchants.active,
              month: dashboard.merchants.this_month,
            })
          "
        />
        <KpiCard
          label-i18n-key="admin.statConversations"
          icon="MessageSquare"
          :value="dashboard.conversations.total"
          :hint="t('admin.statConvSub', { today: dashboard.conversations.today })"
        />
        <KpiCard
          label-i18n-key="admin.statSales"
          icon="ShoppingBag"
          :value="dashboard.sales.total"
          :hint="t('admin.statSalesSub')"
        />
        <KpiCard
          label-i18n-key="admin.statMessages"
          icon="Mail"
          :value="dashboard.messages.total"
          :hint="t('admin.statMessagesSub')"
        />
      </section>

      <!-- Abonnements -->
      <section class="rounded-lg border border-border bg-card p-4">
        <h2 class="text-sm font-semibold text-foreground">{{ $t('admin.subscriptionsTitle') }}</h2>
        <div class="mt-3 flex flex-wrap gap-2">
          <span
            v-for="[plan, count] in planEntries"
            :key="plan"
            class="inline-flex items-center gap-1 rounded-full border border-border bg-muted/40 px-3 py-1 text-sm text-foreground"
          >
            <span class="font-medium capitalize">{{ plan }}</span>
            <span class="text-muted-foreground">· {{ count }}</span>
          </span>
          <span v-if="planEntries.length === 0" class="text-sm text-muted-foreground">
            {{ $t('admin.noSubscriptions') }}
          </span>
        </div>
        <p class="mt-3 text-sm text-muted-foreground">
          <span class="font-semibold text-warning">{{ dashboard.subscriptions.expiring_soon }}</span>
          {{ $t('admin.expiringSoon') }}
        </p>
      </section>
    </template>
  </div>
</template>
