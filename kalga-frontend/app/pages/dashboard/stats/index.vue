<!--
  Dashboard statistiques marchand : KPIs + 2 graphiques temporels.
  Référence : ARCHITECTURE_FRONTEND.md sections 3 + 9.1
-->

<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

import KpiCard from '@/features/stats/components/KpiCard.vue'
import LineChart from '@/features/stats/components/LineChart.vue'
import RangeSelector from '@/features/stats/components/RangeSelector.vue'
import {
  useMerchantStats,
  useStatsTimeseries,
} from '@/features/stats/composables/useStats'
import { rangeFromPreset, type RangePreset } from '@/features/stats/utils/dateRange'
import { formatPriceFCFA } from '@/utils/format'

definePageMeta({ layout: 'dashboard' })

const { t } = useI18n()
const { user } = useAuth()

const merchantId = computed(() => user.value?.merchant_id ?? 0)
const merchantPhone = computed(() => user.value?.merchant_phone ?? '')

const preset = ref<RangePreset>('30d')
const range = computed(() => rangeFromPreset(preset.value))
const fromDate = computed(() => range.value.from)
const toDate = computed(() => range.value.to)
const days = computed(() => Number.parseInt(preset.value, 10) || 30)

const { data: kpis, isLoading: kpisLoading, isError: kpisError } = useMerchantStats(
  merchantPhone,
  merchantId,
  days,
)

const revenueMetric = computed(() => 'revenue' as const)
const salesMetric = computed(() => 'sales' as const)

const { data: revenueSeries } = useStatsTimeseries(merchantPhone, revenueMetric, fromDate, toDate)
const { data: salesSeries } = useStatsTimeseries(merchantPhone, salesMetric, fromDate, toDate)

useHead({ title: t('nav.stats') })

const conversionRateFormatted = computed(() =>
  kpis.value ? `${(kpis.value.conversion_rate * 100).toFixed(1)}%` : '—',
)

const messagesHint = computed(() => {
  if (!kpis.value) return null
  return t('stats.messagesHint', { used: kpis.value.messages_used })
})
</script>

<template>
  <div class="space-y-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">{{ $t('stats.title') }}</h1>
        <p class="text-sm text-muted-foreground">{{ $t('stats.subtitle') }}</p>
      </div>

      <RangeSelector v-model="preset" />
    </header>

    <!-- Pas de marchand -->
    <div
      v-if="!merchantId"
      role="alert"
      class="rounded-lg border border-warning/30 bg-warning/10 p-4 text-sm text-primary"
    >
      {{ $t('conversations.noMerchantContext') }}
    </div>

    <!-- Loading KPIs -->
    <div
      v-else-if="kpisLoading"
      class="flex items-center justify-center rounded-lg border border-border bg-card py-16"
    >
      <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
    </div>

    <!-- Erreur KPIs -->
    <div
      v-else-if="kpisError"
      role="alert"
      class="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center"
    >
      <p class="text-sm text-destructive">{{ $t('stats.loadError') }}</p>
    </div>

    <template v-else-if="kpis">
      <!-- Grid KPIs -->
      <section
        class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6"
        :aria-label="$t('stats.kpis')"
      >
        <KpiCard
          label-i18n-key="stats.revenue"
          icon="DollarSign"
          :value="formatPriceFCFA(kpis.revenue)"
        />
        <KpiCard label-i18n-key="stats.sales" icon="ShoppingBag" :value="kpis.sales" />
        <KpiCard
          label-i18n-key="stats.conversations"
          icon="MessageSquare"
          :value="kpis.conversations"
        />
        <KpiCard
          label-i18n-key="stats.conversionRate"
          icon="TrendingUp"
          :value="conversionRateFormatted"
        />
        <KpiCard label-i18n-key="stats.products" icon="Package" :value="kpis.products" />
        <KpiCard
          label-i18n-key="stats.messages"
          icon="Mail"
          :value="kpis.messages_used"
          :hint="messagesHint"
        />
      </section>

      <!-- Chart : revenu -->
      <section
        class="rounded-lg border border-border bg-card p-4"
        :aria-label="$t('stats.revenueOverTime')"
      >
        <h2 class="mb-3 text-sm font-semibold text-muted-foreground">
          {{ $t('stats.revenueOverTime') }}
        </h2>
        <LineChart :series="revenueSeries" :format-value="formatPriceFCFA" />
      </section>

      <!-- Chart : ventes -->
      <section
        class="rounded-lg border border-border bg-card p-4"
        :aria-label="$t('stats.salesOverTime')"
      >
        <h2 class="mb-3 text-sm font-semibold text-muted-foreground">
          {{ $t('stats.salesOverTime') }}
        </h2>
        <LineChart :series="salesSeries" />
      </section>
    </template>
  </div>
</template>
