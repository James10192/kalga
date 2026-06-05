<!--
  Paramètres marchand — page unique avec navigation par onglets accessibles.

  Sections :
  - Profil (nom, business, paiement)
  - Localisation (adresse + GPS)
  - Persona IA (ton, style, catchphrase)
  - Mode absence (toggle + message)
-->

<script setup lang="ts">
import { Bot, ClockAlert, Loader2, MapPin, User } from 'lucide-vue-next'
import type { Component } from 'vue'

import AwayModeForm from '@/features/merchants/components/AwayModeForm.vue'
import BotPersonaForm from '@/features/merchants/components/BotPersonaForm.vue'
import LocationForm from '@/features/merchants/components/LocationForm.vue'
import ProfileForm from '@/features/merchants/components/ProfileForm.vue'
import { useMerchant } from '@/features/merchants/composables/useMerchants'

definePageMeta({ layout: 'dashboard' })

type TabKey = 'profile' | 'location' | 'persona' | 'away'

interface Tab {
  readonly key: TabKey
  readonly i18nKey: string
  readonly icon: Component
}

const TABS: ReadonlyArray<Tab> = [
  { key: 'profile', i18nKey: 'settings.tabProfile', icon: User },
  { key: 'location', i18nKey: 'settings.tabLocation', icon: MapPin },
  { key: 'persona', i18nKey: 'settings.tabPersona', icon: Bot },
  { key: 'away', i18nKey: 'settings.tabAway', icon: ClockAlert },
] as const

const { t } = useI18n()
const { user } = useAuth()

const merchantId = computed(() => user.value?.merchant_id ?? 0)
const { data: merchant, isLoading, isError } = useMerchant(merchantId)

const activeTab = ref<TabKey>('profile')

useHead({ title: t('nav.settings') })

function panelId(key: TabKey): string {
  return `settings-panel-${key}`
}

function tabId(key: TabKey): string {
  return `settings-tab-${key}`
}
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-semibold text-foreground">{{ $t('settings.title') }}</h1>
      <p class="text-sm text-muted-foreground">{{ $t('settings.subtitle') }}</p>
    </header>

    <!-- Loading -->
    <div
      v-if="isLoading"
      class="flex items-center justify-center rounded-lg border border-border bg-card py-16"
    >
      <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
    </div>

    <!-- Erreur ou pas de marchand -->
    <div
      v-else-if="isError || !merchant"
      role="alert"
      class="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center"
    >
      <p class="text-sm text-destructive">{{ $t('settings.loadError') }}</p>
    </div>

    <!-- Tabs + Panels -->
    <div v-else class="rounded-lg border border-border bg-card">
      <!-- Tablist -->
      <div
        role="tablist"
        :aria-label="$t('settings.tabsLabel')"
        class="flex flex-wrap gap-1 border-b border-border p-2"
      >
        <button
          v-for="tab in TABS"
          :key="tab.key"
          :id="tabId(tab.key)"
          type="button"
          role="tab"
          :aria-selected="activeTab === tab.key"
          :aria-controls="panelId(tab.key)"
          :tabindex="activeTab === tab.key ? 0 : -1"
          :class="[
            'inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            activeTab === tab.key
              ? 'bg-brand-forest text-brand-gold'
              : 'text-foreground hover:bg-muted',
          ]"
          @click="activeTab = tab.key"
        >
          <component :is="tab.icon" class="h-4 w-4" aria-hidden="true" />
          {{ $t(tab.i18nKey) }}
        </button>
      </div>

      <!-- Panel : profil -->
      <section
        v-show="activeTab === 'profile'"
        :id="panelId('profile')"
        role="tabpanel"
        :aria-labelledby="tabId('profile')"
        class="p-6"
      >
        <ProfileForm :merchant="merchant" />
      </section>

      <!-- Panel : localisation -->
      <section
        v-show="activeTab === 'location'"
        :id="panelId('location')"
        role="tabpanel"
        :aria-labelledby="tabId('location')"
        class="p-6"
      >
        <LocationForm :merchant="merchant" />
      </section>

      <!-- Panel : persona IA -->
      <section
        v-show="activeTab === 'persona'"
        :id="panelId('persona')"
        role="tabpanel"
        :aria-labelledby="tabId('persona')"
        class="p-6"
      >
        <BotPersonaForm :merchant="merchant" />
      </section>

      <!-- Panel : mode absence -->
      <section
        v-show="activeTab === 'away'"
        :id="panelId('away')"
        role="tabpanel"
        :aria-labelledby="tabId('away')"
        class="p-6"
      >
        <AwayModeForm :merchant="merchant" />
      </section>
    </div>
  </div>
</template>
