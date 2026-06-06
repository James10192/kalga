<!--
  Menu utilisateur — dropdown partagé entre dashboard marchand et admin.
  Référence : ARCHITECTURE_FRONTEND.md section 7.5 (design system)

  Affiche l'email + rôle + bouton de déconnexion.
  À remplacer par shadcn-vue DropdownMenu après installation des composants.
-->

<script setup lang="ts">
import { ChevronDown, LogOut } from 'lucide-vue-next'
import { onClickOutside } from '@vueuse/core'

const { user, logout } = useAuth()
const { t } = useI18n()
const open = ref(false)
const root = ref<HTMLElement | null>(null)

// Ferme le menu quand on clique en dehors. `onClickOutside` (composable)
// est SSR-safe contrairement à la directive `v-on-click-outside`
// (qui vit dans `@vueuse/components`, non installé ici).
onClickOutside(root, () => {
  open.value = false
})

function handleToggle(): void {
  open.value = !open.value
}

async function handleLogout(): Promise<void> {
  open.value = false
  await logout()
}

// Évite l'affichage si l'utilisateur n'est pas encore chargé
const initials = computed(() => {
  const email = user.value?.email ?? ''
  return email.charAt(0).toUpperCase() || '?'
})
</script>

<template>
  <div v-if="user" ref="root" class="relative">
    <button
      type="button"
      class="inline-flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      :aria-expanded="open"
      aria-haspopup="menu"
      @click="handleToggle"
    >
      <span
        class="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-forest text-sm font-semibold text-brand-gold"
        aria-hidden="true"
      >
        {{ initials }}
      </span>
      <span class="hidden text-foreground sm:block">{{ user.email }}</span>
      <ChevronDown class="h-4 w-4 text-muted-foreground" aria-hidden="true" />
    </button>

    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        role="menu"
        class="absolute right-0 z-50 mt-2 w-56 origin-top-right rounded-md border border-border bg-card p-1 shadow-lg"
      >
        <div class="border-b border-border px-3 py-2">
          <p class="truncate text-sm font-medium text-foreground">{{ user.email }}</p>
          <p class="text-xs text-muted-foreground capitalize">{{ t(`role.${user.role}`) }}</p>
        </div>

        <button
          type="button"
          role="menuitem"
          class="mt-1 inline-flex w-full items-center gap-2 rounded-sm px-3 py-2 text-sm text-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:bg-muted"
          @click="handleLogout"
        >
          <LogOut class="h-4 w-4" aria-hidden="true" />
          {{ t('auth.logout') }}
        </button>
      </div>
    </Transition>
  </div>
</template>
