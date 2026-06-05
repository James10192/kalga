<!--
  Liste des activations marchands (en attente + historique).
-->

<script setup lang="ts">
import { ChevronLeft, ChevronRight, KeyRound, Loader2 } from 'lucide-vue-next'

import ActivationCard from '@/features/activations/components/ActivationCard.vue'
import {
  useActivationsList,
  usePendingActivations,
} from '@/features/activations/composables/useActivations'
import { ACTIVATION_STATUS_VALUES } from '@/utils/constants'
import { formatDateTime, formatPhone } from '@/utils/format'

definePageMeta({ layout: 'admin' })

const { t, locale } = useI18n()

const page = ref(1)
const status = ref<string | undefined>(undefined)

const { data: pending, isLoading: pendingLoading } = usePendingActivations()
const { data, isLoading, isError } = useActivationsList(page, status)

useHead({ title: t('nav.activations') })

const totalPages = computed(() =>
  data.value ? Math.max(1, Math.ceil(data.value.total / data.value.per_page)) : 1,
)

watch(status, () => {
  page.value = 1
})

function formatTime(iso: string | null): string {
  return iso ? formatDateTime(iso, locale.value === 'en' ? 'en-US' : 'fr-FR') : '—'
}

const inputClass =
  'rounded-md border border-input bg-card px-3 py-1.5 text-sm text-foreground transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-semibold text-foreground">{{ $t('admin.activations') }}</h1>
      <p class="text-sm text-muted-foreground">{{ $t('admin.activationsSubtitle') }}</p>
    </header>

    <section>
      <h2 class="mb-3 text-sm font-semibold text-muted-foreground">
        {{ $t('admin.pendingActivations') }}
      </h2>

      <div v-if="pendingLoading" class="flex justify-center py-8">
        <Loader2 class="h-5 w-5 animate-spin text-muted-foreground" aria-hidden="true" />
      </div>

      <div
        v-else-if="!pending || pending.length === 0"
        class="rounded-lg border border-dashed border-border bg-card px-6 py-8 text-center text-sm text-muted-foreground"
      >
        {{ $t('admin.noPendingActivations') }}
      </div>

      <div v-else class="grid gap-2 sm:grid-cols-2">
        <ActivationCard v-for="a in pending" :key="a.id" :activation="a" />
      </div>
    </section>

    <section>
      <header class="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 class="text-sm font-semibold text-muted-foreground">
          {{ $t('admin.activationsHistory') }}
        </h2>
        <label class="inline-flex items-center gap-2 text-xs text-muted-foreground">
          {{ $t('admin.filterByStatus') }}
          <select
            :value="status ?? ''"
            :class="inputClass"
            @change="status = ($event.target as HTMLSelectElement).value || undefined"
          >
            <option value="">{{ $t('common.all') }}</option>
            <option v-for="s in ACTIVATION_STATUS_VALUES" :key="s" :value="s">
              {{ $t(`admin.activationStatus.${s}`) }}
            </option>
          </select>
        </label>
      </header>

      <div
        v-if="isLoading"
        class="flex items-center justify-center rounded-lg border border-border bg-card py-12"
      >
        <Loader2 class="h-5 w-5 animate-spin text-muted-foreground" aria-hidden="true" />
      </div>

      <div
        v-else-if="isError"
        role="alert"
        class="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-center text-sm text-destructive"
      >
        {{ $t('admin.loadError') }}
      </div>

      <div
        v-else-if="data && data.total === 0"
        class="rounded-lg border border-dashed border-border bg-card px-6 py-8 text-center text-sm text-muted-foreground"
      >
        {{ $t('admin.noActivations') }}
      </div>

      <template v-else-if="data">
        <div class="overflow-x-auto rounded-lg border border-border bg-card">
          <table class="w-full divide-y divide-border">
            <thead class="bg-muted/50">
              <tr class="text-left text-xs uppercase tracking-wider text-muted-foreground">
                <th class="px-4 py-2 font-semibold">
                  <KeyRound class="inline h-3 w-3" aria-hidden="true" />
                  {{ $t('admin.code') }}
                </th>
                <th class="px-4 py-2 font-semibold">{{ $t('admin.merchant') }}</th>
                <th class="px-4 py-2 font-semibold">{{ $t('admin.statusColumn') }}</th>
                <th class="px-4 py-2 font-semibold">{{ $t('admin.sentAt') }}</th>
                <th class="px-4 py-2 font-semibold">{{ $t('admin.usedAt') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border">
              <tr v-for="a in data.items" :key="a.id" class="text-sm text-foreground">
                <td class="px-4 py-2 font-mono">{{ a.code }}</td>
                <td class="px-4 py-2">
                  <p>{{ a.merchant_name ?? '—' }}</p>
                  <p v-if="a.merchant_phone" class="text-xs text-muted-foreground">
                    {{ formatPhone(a.merchant_phone) }}
                  </p>
                </td>
                <td class="px-4 py-2 text-xs">{{ $t(`admin.activationStatus.${a.status}`) }}</td>
                <td class="px-4 py-2 text-xs text-muted-foreground">{{ formatTime(a.sent_at) }}</td>
                <td class="px-4 py-2 text-xs text-muted-foreground">{{ formatTime(a.used_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <nav
          v-if="totalPages > 1"
          class="mt-4 flex items-center justify-center gap-2"
          :aria-label="$t('common.pagination')"
        >
          <button
            type="button"
            :disabled="page <= 1"
            class="inline-flex items-center gap-1 rounded-md border border-border bg-card px-3 py-1.5 text-sm transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            @click="page = Math.max(1, page - 1)"
          >
            <ChevronLeft class="h-4 w-4" aria-hidden="true" />
            {{ $t('common.previous') }}
          </button>
          <span class="px-3 text-sm text-muted-foreground">
            {{ $t('common.pageOf', { current: page, total: totalPages }) }}
          </span>
          <button
            type="button"
            :disabled="page >= totalPages"
            class="inline-flex items-center gap-1 rounded-md border border-border bg-card px-3 py-1.5 text-sm transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            @click="page = Math.min(totalPages, page + 1)"
          >
            {{ $t('common.next') }}
            <ChevronRight class="h-4 w-4" aria-hidden="true" />
          </button>
        </nav>
      </template>
    </section>
  </div>
</template>
