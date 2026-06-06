<!--
  Ligne d'un marchand dans le tableau admin.
-->

<script setup lang="ts">
import { ChevronRight } from 'lucide-vue-next'

import MerchantStatusBadge from '@/features/merchants/components/MerchantStatusBadge.vue'
import { formatDate, formatPhone, initialsFrom } from '@/utils/format'
import { ROUTES } from '@/utils/routes'
import type { Merchant } from '../types'

interface Props {
  merchant: Merchant
}

const props = defineProps<Props>()
const { locale } = useI18n()

const detailHref = computed(() => ROUTES.admin.merchantDetail(props.merchant.id))
const createdAt = computed(() =>
  formatDate(props.merchant.created_at, locale.value === 'en' ? 'en-US' : 'fr-FR'),
)
const initials = computed(() =>
  initialsFrom(props.merchant.business_name ?? props.merchant.name),
)
</script>

<template>
  <NuxtLink
    :to="detailHref"
    class="group grid grid-cols-[auto_1fr_auto] items-center gap-3 rounded-lg border border-border bg-card p-4 transition hover:border-primary/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
  >
    <div
      class="inline-flex h-10 w-10 items-center justify-center rounded-full bg-primary text-sm font-semibold text-warning"
      aria-hidden="true"
    >
      {{ initials }}
    </div>

    <div class="min-w-0">
      <div class="flex flex-wrap items-center gap-2">
        <p class="truncate font-medium text-foreground">
          {{ merchant.business_name ?? merchant.name }}
        </p>
        <MerchantStatusBadge :is-active="merchant.is_active" />
      </div>

      <p class="mt-0.5 truncate text-xs text-muted-foreground">
        {{ formatPhone(merchant.phone) }}
        <span v-if="merchant.city" class="ml-2">· {{ merchant.city }}</span>
      </p>

      <p class="mt-1 text-xs text-muted-foreground">
        {{ $t('admin.createdAt') }}: {{ createdAt }}
      </p>
    </div>

    <ChevronRight
      class="h-4 w-4 text-muted-foreground transition group-hover:text-primary"
      aria-hidden="true"
    />
  </NuxtLink>
</template>
