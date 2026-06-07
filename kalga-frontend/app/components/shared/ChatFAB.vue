<!--
  Chat flottant (FAB) — bouton d'aide rond, fixe en bas à droite.
  Référence : prompt design KALGA (section 6).

  Couleur : token de marque `--gold` (pas de hex en dur). Le branchement réel
  (ouverture d'un widget de chat) viendra avec l'intégration support.
-->

<script setup lang="ts">
import { MessageCircle } from 'lucide-vue-next'

const { t } = useI18n()
</script>

<template>
  <button
    type="button"
    class="fixed bottom-6 right-6 z-50 inline-flex h-14 w-14 items-center justify-center rounded-full bg-gold text-gold-foreground shadow-lg transition duration-300 hover:scale-105 hover:shadow-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    :aria-label="t('landing.chatLabel')"
    :title="t('landing.chatLabel')"
  >
    <MessageCircle class="h-6 w-6" aria-hidden="true" />
  </button>
</template>
