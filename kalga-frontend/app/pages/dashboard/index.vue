<!--
  Dashboard marchand — vue d'ensemble.
  Référence : ARCHITECTURE_FRONTEND.md section 3 (zone marchand).

  Accueil : salutation (nom du marchand depuis la session) + KPIs réels
  (réutilise useMerchantStats) + dernières conversations (useConversationsList).
  Aucun appel API direct ici : tout passe par les composables des features.
-->

<script setup lang="ts">
import { ArrowRight, MessageSquare } from 'lucide-vue-next'

import { useConversationsList } from '@/features/conversations/composables/useConversations'
import KpiCard from '@/features/stats/components/KpiCard.vue'
import { useMerchantStats } from '@/features/stats/composables/useStats'
import { formatPriceFCFA } from '@/utils/format'
import { ROUTES } from '@/utils/routes'

definePageMeta({ layout: 'dashboard' })

const { user } = useAuth()
const { t } = useI18n()

const merchantId = computed(() => user.value?.merchant_id ?? 0)
const merchantPhone = computed(() => user.value?.merchant_phone ?? '')
const merchantName = computed(
  () => user.value?.business_name || t('dashboard.defaultMerchantName'),
)

const statsDays = ref(30)
const allStatus = ref<string | undefined>(undefined)
const firstPage = ref(1)

const { data: kpis } = useMerchantStats(merchantPhone, merchantId, statsDays)
const { data: conversations } = useConversationsList(merchantPhone, allStatus, firstPage)

const recentConversations = computed(() => conversations.value?.items.slice(0, 4) ?? [])

useHead({ title: t('nav.overview') })
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-semibold text-foreground">
        {{ $t('dashboard.welcomeTitle', { name: merchantName }) }}
      </h1>
      <p class="text-sm text-muted-foreground">{{ $t('dashboard.welcomeSubtitle') }}</p>
    </header>

    <!-- KPIs -->
    <section
      v-if="kpis"
      class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
      :aria-label="$t('stats.kpis')"
    >
      <KpiCard label-i18n-key="stats.products" icon="Package" :value="kpis.products" />
      <KpiCard
        label-i18n-key="stats.conversations"
        icon="MessageSquare"
        :value="kpis.conversations"
      />
      <KpiCard label-i18n-key="stats.sales" icon="ShoppingBag" :value="kpis.sales" />
      <KpiCard
        label-i18n-key="stats.revenue"
        icon="DollarSign"
        :value="formatPriceFCFA(kpis.revenue)"
      />
    </section>

    <!-- Dernières conversations -->
    <section class="rounded-lg border border-border bg-card p-4">
      <div class="mb-2 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-foreground">
          {{ $t('dashboard.recentConversations') }}
        </h2>
        <NuxtLink
          :to="ROUTES.dashboard.conversations"
          class="inline-flex items-center gap-1 text-xs font-medium text-gold transition hover:opacity-80"
        >
          {{ $t('dashboard.viewAll') }}
          <ArrowRight class="h-3.5 w-3.5" aria-hidden="true" />
        </NuxtLink>
      </div>

      <ul v-if="recentConversations.length" class="divide-y divide-border">
        <li v-for="conversation in recentConversations" :key="conversation.id">
          <NuxtLink
            :to="ROUTES.dashboard.conversationDetail(conversation.id)"
            class="flex items-center justify-between gap-3 rounded-md px-2 py-3 text-sm transition hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <span class="flex items-center gap-2 font-medium text-foreground">
              <MessageSquare class="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              {{ conversation.client_phone }}
            </span>
            <span v-if="conversation.current_offer" class="text-xs font-medium text-gold">
              {{ formatPriceFCFA(conversation.current_offer) }}
            </span>
          </NuxtLink>
        </li>
      </ul>
      <p v-else class="py-8 text-center text-sm text-muted-foreground">
        {{ $t('dashboard.noActivity') }}
      </p>
    </section>
  </div>
</template>
