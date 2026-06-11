<!--
  Gestion du Stock — porté fidèlement depuis dashboard/index.html (#section-stock)
  + dashboard/static/app.js (loadStockSection / renderStockTable).

  Tableau : Produit · Statut · Stock · Mode rupture · En attente · Réappro.
  Filtres : Tous / Épuisés / Stock bas / Normal.
-->

<script setup lang="ts">
import { Loader2, Plus, Users } from 'lucide-vue-next'

import { useRestock, useStockOverview, useUpdateStockMode } from '@/features/stock/composables/useStock'
import { STOCK_MODE_VALUES } from '@/features/stock/schemas'
import type { StockMode, StockOverviewItem, StockOverviewStatus } from '@/features/stock/types'

definePageMeta({ layout: 'dashboard' })

const { t } = useI18n()
const { user } = useAuth()
const { push } = useToast()

const merchantId = computed(() => user.value?.merchant_id ?? 0)
const storeName = computed(() => user.value?.business_name ?? '')

const { data, isLoading, isError, refetch } = useStockOverview(merchantId)
const { mutateAsync: updateMode } = useUpdateStockMode()
const { mutateAsync: restock, isPending: restocking } = useRestock()

type Filter = 'all' | StockOverviewStatus
const FILTERS = [
  { key: 'all', label: 'stock.filterAll' },
  { key: 'out_of_stock', label: 'stock.filterOut' },
  { key: 'low_stock', label: 'stock.filterLow' },
  { key: 'ok', label: 'stock.filterOk' },
] as const
const filter = ref<Filter>('all')

const filtered = computed<StockOverviewItem[]>(() => {
  const items = data.value ?? []
  if (filter.value === 'all') return items
  if (filter.value === 'ok') {
    return items.filter((p) => p.stock_status === 'ok' || p.stock_status === 'unlimited')
  }
  return items.filter((p) => p.stock_status === filter.value)
})

/** Quantité à ajouter, saisie par code produit. */
const restockQty = reactive<Record<string, number | null>>({})

const STATUS_STYLE: Record<StockOverviewStatus, string> = {
  out_of_stock: 'bg-destructive/10 text-destructive',
  low_stock: 'bg-warning/15 text-warning',
  ok: 'bg-success/15 text-success',
  unlimited: 'bg-primary-lo text-primary',
}

function stockDisplay(item: StockOverviewItem): string {
  return item.stock_quantity === -1 ? '∞' : String(item.stock_quantity)
}

async function onModeChange(item: StockOverviewItem, mode: StockMode): Promise<void> {
  try {
    await updateMode({ code: item.code, mode, merchantId: merchantId.value })
    push.success(t('stock.modeUpdated'))
  } catch (error) {
    push.error(extractApiErrorMessage(error, t('stock.modeError')))
  }
}

async function onRestock(item: StockOverviewItem): Promise<void> {
  const qty = restockQty[item.code]
  if (!qty || qty < 1) {
    push.error(t('stock.invalidQty'))
    return
  }
  try {
    const result = await restock({
      code: item.code,
      data: {
        quantity_to_add: qty,
        merchant_id: merchantId.value,
        broadcast_waitlist: true,
        store_name: storeName.value,
      },
    })
    restockQty[item.code] = null
    const notified = result.waitlist_notified ?? 0
    push.success(notified > 0 ? t('stock.restockedNotified', { n: notified }) : t('stock.restocked'))
  } catch (error) {
    push.error(extractApiErrorMessage(error, t('stock.restockError')))
  }
}

useHead({ title: t('stock.title') })
</script>

<template>
  <div class="space-y-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">{{ $t('stock.title') }}</h1>
        <p class="text-sm text-muted-foreground">{{ $t('stock.subtitle') }}</p>
      </div>

      <div class="flex flex-wrap gap-1" role="tablist" :aria-label="$t('stock.title')">
        <button
          v-for="f in FILTERS"
          :key="f.key"
          type="button"
          role="tab"
          :aria-selected="filter === f.key"
          :class="[
            'rounded-md px-3 py-1.5 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            filter === f.key ? 'bg-primary text-primary-foreground' : 'text-foreground hover:bg-muted',
          ]"
          @click="filter = f.key"
        >
          {{ $t(f.label) }}
        </button>
      </div>
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
      v-else-if="isError"
      role="alert"
      class="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center"
    >
      <p class="text-sm text-destructive">{{ $t('stock.loadError') }}</p>
      <button
        type="button"
        class="mt-3 inline-flex items-center justify-center rounded-md border border-destructive/40 bg-card px-4 py-2 text-xs font-medium text-destructive transition hover:bg-destructive/10"
        @click="refetch()"
      >
        {{ $t('common.retry') }}
      </button>
    </div>

    <!-- Table -->
    <div v-else class="overflow-x-auto rounded-lg border border-border bg-card">
      <table class="w-full min-w-[760px] text-sm">
        <thead>
          <tr class="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
            <th class="px-4 py-3 font-medium">{{ $t('stock.colProduct') }}</th>
            <th class="px-4 py-3 font-medium">{{ $t('stock.colStatus') }}</th>
            <th class="px-4 py-3 font-medium">{{ $t('stock.colStock') }}</th>
            <th class="px-4 py-3 font-medium">{{ $t('stock.colMode') }}</th>
            <th class="px-4 py-3 font-medium">{{ $t('stock.colWaitlist') }}</th>
            <th class="px-4 py-3 font-medium">{{ $t('stock.colRestock') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="filtered.length === 0">
            <td colspan="6" class="px-4 py-12 text-center text-muted-foreground">
              {{ $t('stock.empty') }}
            </td>
          </tr>
          <tr
            v-for="item in filtered"
            :key="item.id"
            class="border-b border-border last:border-0 hover:bg-muted/30"
          >
            <!-- Produit -->
            <td class="px-4 py-3">
              <div class="font-medium text-foreground">{{ item.name }}</div>
              <div class="text-xs text-muted-foreground">{{ item.code }}</div>
            </td>
            <!-- Statut -->
            <td class="px-4 py-3">
              <span
                :class="[
                  'inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium',
                  STATUS_STYLE[item.stock_status],
                ]"
              >
                {{ $t(`stock.status_${item.stock_status}`) }}
              </span>
            </td>
            <!-- Stock -->
            <td class="px-4 py-3 font-semibold text-foreground">{{ stockDisplay(item) }}</td>
            <!-- Mode rupture -->
            <td class="px-4 py-3">
              <select
                :aria-label="$t('stock.colMode')"
                class="rounded-md border border-border bg-background px-2 py-1 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                @change="onModeChange(item, ($event.target as HTMLSelectElement).value as StockMode)"
              >
                <option v-for="mode in STOCK_MODE_VALUES" :key="mode" :value="mode">
                  {{ $t(`stock.mode_${mode}`) }}
                </option>
              </select>
            </td>
            <!-- En attente -->
            <td class="px-4 py-3">
              <span
                v-if="item.waitlist_count > 0"
                class="inline-flex items-center gap-1 text-xs font-medium text-primary"
              >
                <Users class="h-3.5 w-3.5" aria-hidden="true" />
                {{ item.waitlist_count }}
              </span>
              <span v-else class="text-muted-foreground">—</span>
            </td>
            <!-- Réappro -->
            <td class="px-4 py-3">
              <div class="flex items-center gap-1">
                <input
                  v-model.number="restockQty[item.code]"
                  type="number"
                  min="1"
                  :placeholder="$t('stock.qtyPlaceholder')"
                  :aria-label="$t('stock.colRestock')"
                  class="w-20 rounded-md border border-border bg-background px-2 py-1 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                <button
                  type="button"
                  :disabled="restocking"
                  class="inline-flex items-center justify-center rounded-md bg-primary p-1.5 text-primary-foreground transition hover:bg-primary-hi disabled:opacity-60"
                  :aria-label="$t('stock.colRestock')"
                  @click="onRestock(item)"
                >
                  <Plus class="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
