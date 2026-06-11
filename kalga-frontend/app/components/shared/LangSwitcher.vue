<!--
  Sélecteur de langue — bouton avec dropdown des locales disponibles.
  Référence : ARCHITECTURE_FRONTEND.md section 7.7 (i18n)

  Switch entre français et anglais.
-->

<script setup lang="ts">
import { Globe } from 'lucide-vue-next'
import { onClickOutside } from '@vueuse/core'

const { locale, locales, setLocale } = useI18n()
const open = ref(false)
const root = ref<HTMLElement | null>(null)

// Ferme le menu quand on clique en dehors. `onClickOutside` (composable)
// est SSR-safe contrairement à la directive `v-on-click-outside`
// (qui vit dans `@vueuse/components`, non installé ici).
onClickOutside(root, () => {
  open.value = false
})

interface DisplayedLocale {
  code: string
  name: string
}

const availableLocales = computed<DisplayedLocale[]>(() =>
  (locales.value as DisplayedLocale[]).filter((l) => l.code !== locale.value),
)

const currentLocaleName = computed<string>(() => {
  const all = locales.value as DisplayedLocale[]
  return all.find((l) => l.code === locale.value)?.name ?? locale.value
})

function handleToggle(): void {
  open.value = !open.value
}

async function handleSelect(code: string): Promise<void> {
  open.value = false
  await setLocale(code as 'fr' | 'en')
}
</script>

<template>
  <div ref="root" class="relative">
    <button
      type="button"
      class="inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      :aria-expanded="open"
      :aria-label="$t('common.changeLanguage')"
      @click="handleToggle"
    >
      <Globe class="h-4 w-4" aria-hidden="true" />
      <span class="hidden sm:inline">{{ currentLocaleName }}</span>
    </button>

    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <ul
        v-if="open"
        role="menu"
        class="absolute right-0 z-50 mt-2 w-40 rounded-md border border-border bg-card p-1 shadow-lg"
      >
        <li v-for="l in availableLocales" :key="l.code">
          <button
            type="button"
            role="menuitem"
            class="w-full rounded-sm px-3 py-2 text-left text-sm text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:bg-muted"
            @click="handleSelect(l.code)"
          >
            {{ l.name }}
          </button>
        </li>
      </ul>
    </Transition>
  </div>
</template>
