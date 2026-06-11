<!--
  Bascule thème clair / sombre.
  Référence : ARCHITECTURE_FRONTEND.md section 7.5 (design system)

  S'appuie sur `useColorMode` (VueUse) qui pose/retire la classe `.dark` sur
  <html> et persiste le choix (localStorage). Les tokens de tailwind.css font
  le reste. `<ClientOnly>` évite tout mismatch d'hydratation sur l'icône.
-->

<script setup lang="ts">
import { Moon, Sun } from 'lucide-vue-next'
import { useColorMode } from '@vueuse/core'

const { t } = useI18n()

// initialValue 'light' : démarrage prévisible (clair) tant que l'utilisateur
// n'a pas choisi. Le choix est ensuite mémorisé.
const mode = useColorMode({ initialValue: 'light' })

function toggle(): void {
  mode.value = mode.value === 'dark' ? 'light' : 'dark'
}
</script>

<template>
  <ClientOnly>
    <button
      type="button"
      class="inline-flex items-center justify-center rounded-md p-2 text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      :aria-label="t('common.toggleTheme')"
      :title="t('common.toggleTheme')"
      @click="toggle"
    >
      <Moon v-if="mode === 'dark'" class="h-4 w-4" aria-hidden="true" />
      <Sun v-else class="h-4 w-4" aria-hidden="true" />
    </button>

    <!-- Réserve l'espace côté serveur pour éviter un saut de layout -->
    <template #fallback>
      <span class="inline-block h-9 w-9" aria-hidden="true" />
    </template>
  </ClientOnly>
</template>
