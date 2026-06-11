<!--
  Dashboard marchand — Aperçu. Porté fidèlement depuis dashboard/index.html
  (section overview) + dashboard/static/app.js.

  Sections (dans l'ordre de l'existant) :
   1. KPIs : Produits, Conversations, Ventes, Revenus.
   2. Votre Vitrine en ligne : lien public partageable + Copier + Ouvrir.
   3. Ventes en attente : conversations status=pending, Appeler + Fait (accept).
   4. Grille : Conversations Récentes + Produits Populaires (groupés).
-->

<script setup lang="ts">
import { ArrowRight, Bell, Check, Copy, ExternalLink, Phone, Store } from 'lucide-vue-next'

import {
  useAcceptConversation,
  useConversationsList,
} from '@/features/conversations/composables/useConversations'
import { useProductsList } from '@/features/products/composables/useProducts'
import { groupProductsByVariant } from '@/features/products/utils/groupVariants'
import KpiCard from '@/features/stats/components/KpiCard.vue'
import { useMerchantStats } from '@/features/stats/composables/useStats'
import { formatPhone, formatPriceFCFA } from '@/utils/format'
import { ROUTES } from '@/utils/routes'

definePageMeta({ layout: 'dashboard' })

const { user } = useAuth()
const { t } = useI18n()
const { push } = useToast()

const merchantId = computed(() => user.value?.merchant_id ?? 0)
const merchantPhone = computed(() => user.value?.merchant_phone ?? '')
const merchantName = computed(() => user.value?.business_name || t('dashboard.defaultMerchantName'))

// --- KPIs ---
const statsDays = ref(30)
const { data: kpis } = useMerchantStats(merchantPhone, merchantId, statsDays)

// --- Conversations (récentes + ventes en attente) ---
const allStatus = ref<string | undefined>(undefined)
const pendingStatus = ref<string | undefined>('pending')
const firstPage = ref(1)
const { data: conversations } = useConversationsList(merchantPhone, allStatus, firstPage)
const { data: pending } = useConversationsList(merchantPhone, pendingStatus, firstPage)
const { mutateAsync: acceptConversation, isPending: accepting } = useAcceptConversation()

const recentConversations = computed(() => conversations.value?.items.slice(0, 5) ?? [])
const pendingSales = computed(() => pending.value?.items ?? [])

// --- Produits populaires (groupés par variante, top 5) ---
const { data: products } = useProductsList(merchantId, firstPage)
const popularProducts = computed(() =>
  groupProductsByVariant(products.value?.items ?? []).slice(0, 5),
)

// --- Vitrine en ligne (lien public partageable) ---
const storefrontUrl = ref('')
onMounted(() => {
  if (merchantPhone.value) {
    storefrontUrl.value = window.location.origin + ROUTES.storefront.merchant(merchantPhone.value)
  }
})

async function copyStorefrontLink(): Promise<void> {
  try {
    await navigator.clipboard.writeText(storefrontUrl.value)
    push.success(t('dashboard.linkCopied'))
  } catch {
    push.error(t('products.copyError'))
  }
}

async function markDone(id: number): Promise<void> {
  try {
    await acceptConversation(id)
    push.success(t('dashboard.saleMarkedDone'))
  } catch (error) {
    push.error(extractApiErrorMessage(error, t('common.error')))
  }
}

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

    <!-- 1. KPIs -->
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

    <!-- 2. Votre Vitrine en ligne -->
    <section class="rounded-lg border border-border bg-card p-4">
      <h2 class="flex items-center gap-2 text-sm font-semibold text-foreground">
        <Store class="h-4 w-4 text-primary" aria-hidden="true" />
        {{ $t('dashboard.storefrontTitle') }}
      </h2>
      <p class="mt-1 text-sm text-muted-foreground">{{ $t('dashboard.storefrontHint') }}</p>
      <div class="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <input
          :value="storefrontUrl"
          readonly
          class="w-full flex-1 cursor-pointer rounded-md border border-primary/40 bg-primary-lo px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          :aria-label="$t('dashboard.storefrontTitle')"
          @click="copyStorefrontLink"
        >
        <div class="flex gap-2">
          <button
            type="button"
            class="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary-hi"
            @click="copyStorefrontLink"
          >
            <Copy class="h-4 w-4" aria-hidden="true" />
            {{ $t('dashboard.copy') }}
          </button>
          <NuxtLink
            :to="ROUTES.storefront.merchant(merchantPhone)"
            target="_blank"
            class="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground transition hover:bg-muted"
          >
            <ExternalLink class="h-4 w-4" aria-hidden="true" />
            {{ $t('dashboard.open') }}
          </NuxtLink>
        </div>
      </div>
    </section>

    <!-- 3. Ventes en attente (prioritaire) -->
    <section
      v-if="pendingSales.length"
      class="rounded-lg border border-destructive/40 bg-destructive/5 p-4"
    >
      <h2 class="flex items-center gap-2 text-sm font-semibold text-destructive">
        <Bell class="h-4 w-4" aria-hidden="true" />
        {{ $t('dashboard.pendingSales') }}
        <span
          class="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive px-1.5 text-xs font-bold text-destructive-foreground"
        >
          {{ pendingSales.length }}
        </span>
      </h2>

      <ul class="mt-3 space-y-2">
        <li
          v-for="sale in pendingSales"
          :key="sale.id"
          class="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-card p-3"
        >
          <div class="min-w-0">
            <p class="text-sm font-medium text-foreground">
              {{ sale.product_name || $t('products.title') }}
              <span v-if="sale.product_code" class="text-muted-foreground">
                ({{ sale.product_code }})
              </span>
            </p>
            <p class="text-xs text-muted-foreground">
              {{ formatPhone(sale.client_phone) }}
              <span v-if="sale.current_offer" class="font-medium text-gold">
                · {{ formatPriceFCFA(sale.current_offer) }}
              </span>
            </p>
          </div>
          <div class="flex shrink-0 gap-2">
            <a
              :href="`tel:${sale.client_phone}`"
              class="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition hover:bg-primary-hi"
            >
              <Phone class="h-3.5 w-3.5" aria-hidden="true" />
              {{ $t('dashboard.call') }}
            </a>
            <button
              type="button"
              :disabled="accepting"
              class="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-muted disabled:opacity-60"
              @click="markDone(sale.id)"
            >
              <Check class="h-3.5 w-3.5" aria-hidden="true" />
              {{ $t('dashboard.markDone') }}
            </button>
          </div>
        </li>
      </ul>
    </section>

    <!-- 4. Conversations récentes + Produits populaires -->
    <div class="grid gap-4 lg:grid-cols-2">
      <!-- Conversations récentes -->
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
              class="flex items-center gap-3 rounded-md px-2 py-2.5 text-sm transition hover:bg-muted/50"
            >
              <span
                class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground"
              >
                {{ conversation.client_phone.slice(-2) }}
              </span>
              <span class="min-w-0 flex-1">
                <span class="block truncate font-medium text-foreground">
                  {{ formatPhone(conversation.client_phone) }}
                </span>
                <span class="block truncate text-xs text-muted-foreground">
                  {{ conversation.product_code }}
                  <template v-if="conversation.product_name"> — {{ conversation.product_name }}</template>
                </span>
              </span>
            </NuxtLink>
          </li>
        </ul>
        <p v-else class="py-8 text-center text-sm text-muted-foreground">
          {{ $t('dashboard.noActivity') }}
        </p>
      </section>

      <!-- Produits populaires -->
      <section class="rounded-lg border border-border bg-card p-4">
        <div class="mb-2 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-foreground">
            {{ $t('dashboard.popularProducts') }}
          </h2>
          <NuxtLink
            :to="ROUTES.dashboard.products"
            class="inline-flex items-center gap-1 text-xs font-medium text-gold transition hover:opacity-80"
          >
            {{ $t('dashboard.viewAll') }}
            <ArrowRight class="h-3.5 w-3.5" aria-hidden="true" />
          </NuxtLink>
        </div>

        <ul v-if="popularProducts.length" class="divide-y divide-border">
          <li
            v-for="(group, index) in popularProducts"
            :key="group.main.id"
            class="flex items-center gap-3 px-2 py-2.5 text-sm"
          >
            <span
              class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gold text-xs font-bold text-gold-foreground"
            >
              {{ index + 1 }}
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate font-medium text-foreground">{{ group.displayName }}</span>
              <span class="block text-xs text-muted-foreground">{{ group.main.code }}</span>
            </span>
            <span class="shrink-0 text-sm font-semibold text-primary">
              {{ formatPriceFCFA(group.main.price) }}
            </span>
          </li>
        </ul>
        <p v-else class="py-8 text-center text-sm text-muted-foreground">
          {{ $t('products.emptyTitle') }}
        </p>
      </section>
    </div>
  </div>
</template>
