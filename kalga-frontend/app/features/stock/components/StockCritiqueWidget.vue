<!--
  Widget « Stock Critique » de l'Aperçu.
  Porté fidèlement depuis dashboard/index.html (#stock-critique-section) +
  app.js (loadStockCritiqueWidget). Affiché uniquement s'il y a une alerte
  (rupture ou stock bas) — la décision d'affichage est faite par le parent.

  Données : GET /stock/merchant/{id}/critique.
-->

<script setup lang="ts">
import { AlertTriangle, ArrowRight } from 'lucide-vue-next'

import type { CriticalStockProduct, StockCritique } from '@/features/stock/types'
import { formatPriceFCFA } from '@/utils/format'
import { ROUTES } from '@/utils/routes'

interface Props {
  critique: StockCritique
}

defineProps<Props>()

const { t } = useI18n()

function statusLabel(product: CriticalStockProduct): string {
  return product.stock_status === 'out_of_stock'
    ? t('stock.status_out_of_stock')
    : t('stock.status_low_stock')
}
</script>

<template>
  <section class="rounded-lg border border-warning/30 bg-warning/5 p-5">
    <div class="mb-4 flex items-center justify-between gap-3">
      <h2 class="flex items-center gap-2 text-sm font-semibold text-foreground">
        <AlertTriangle class="h-4 w-4 text-warning" aria-hidden="true" />
        {{ $t('stock.critiqueTitle') }}
      </h2>
      <NuxtLink
        :to="ROUTES.dashboard.stock"
        class="inline-flex items-center gap-1 text-sm font-medium text-primary transition hover:text-primary-hi focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {{ $t('stock.manage') }}
        <ArrowRight class="h-3.5 w-3.5" aria-hidden="true" />
      </NuxtLink>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div class="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-center">
        <p class="text-2xl font-bold text-destructive">{{ critique.out_of_stock_count }}</p>
        <p class="text-xs text-muted-foreground">{{ $t('stock.kpiOutOfStock') }}</p>
      </div>
      <div class="rounded-md border border-warning/30 bg-warning/10 p-3 text-center">
        <p class="text-2xl font-bold text-warning">{{ critique.low_stock_count }}</p>
        <p class="text-xs text-muted-foreground">{{ $t('stock.kpiLowStock') }}</p>
      </div>
      <div class="rounded-md border border-border bg-card p-3 text-center">
        <p class="text-2xl font-bold text-foreground">{{ critique.total_waitlist }}</p>
        <p class="text-xs text-muted-foreground">{{ $t('stock.kpiWaitlist') }}</p>
      </div>
      <div class="rounded-md border border-border bg-card p-3 text-center">
        <p class="text-lg font-bold text-gold">
          {{ formatPriceFCFA(critique.lost_revenue_estimate) }}
        </p>
        <p class="text-xs text-muted-foreground">{{ $t('stock.kpiLostRevenue') }}</p>
      </div>
    </div>

    <!-- Liste des produits critiques -->
    <ul v-if="critique.critical_products.length > 0" class="mt-4 space-y-2">
      <li
        v-for="product in critique.critical_products"
        :key="product.id"
        class="flex items-center justify-between gap-3 rounded-md border border-border bg-card px-3 py-2"
      >
        <div class="min-w-0">
          <p class="truncate text-sm font-medium text-foreground">{{ product.name }}</p>
          <p class="text-xs text-muted-foreground">
            <span class="font-mono">{{ product.code }}</span>
            ·
            <span
              :class="
                product.stock_status === 'out_of_stock' ? 'text-destructive' : 'text-warning'
              "
            >
              {{ statusLabel(product) }}
            </span>
          </p>
        </div>
        <span
          v-if="product.waitlist_count > 0"
          class="shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
        >
          {{ $t('stock.waitingCount', { count: product.waitlist_count }) }}
        </span>
      </li>
    </ul>
  </section>
</template>
