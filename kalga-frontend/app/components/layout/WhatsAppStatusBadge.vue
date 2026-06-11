<!--
  Badge de statut WhatsApp dans l'en-tête (zone marchand).
  Porté depuis dashboard/index.html (#wa-status : point + « WhatsApp Connecté »).

  Ne s'affiche que pour un MARCHAND connecté (présence de merchant_phone) — donc
  jamais côté admin, qui partage le même AppHeader. Le statut est rafraîchi
  périodiquement via useWhatsappStatus.
-->

<script setup lang="ts">
import { useWhatsappStatus } from '@/features/auth/composables/useWhatsappStatus'

const { user } = useAuth()
const phone = computed(() => user.value?.merchant_phone ?? '')
const { data } = useWhatsappStatus(phone)
const connected = computed(() => data.value?.connected ?? false)

const label = computed(() =>
  connected.value ? 'dashboard.whatsappConnected' : 'dashboard.whatsappDisconnected',
)
</script>

<template>
  <div
    v-if="phone"
    class="hidden items-center gap-1.5 rounded-full border border-border bg-card px-2.5 py-1 sm:flex"
    :title="$t(label)"
  >
    <span
      class="h-2 w-2 rounded-full"
      :class="connected ? 'bg-success' : 'bg-destructive'"
      aria-hidden="true"
    />
    <span class="text-xs font-medium text-muted-foreground">{{ $t(label) }}</span>
  </div>
</template>
