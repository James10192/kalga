<!--
  Navigation latérale réutilisable (dashboard marchand + admin).
  Référence : ARCHITECTURE_FRONTEND.md section 7.5

  Props :
  - items : liste typée d'items de navigation (cf. utils/nav.ts)
  - title : titre i18n affiché en haut de la sidebar

  Comportement :
  - Desktop : sidebar fixe (gérée par le layout parent)
  - Mobile  : drawer (slot), géré par le composant parent qui passe `open`
-->

<script setup lang="ts">
import * as LucideIcons from 'lucide-vue-next'
import type { Component } from 'vue'
import type { NavItem } from '@/utils/nav'
import { ROUTES } from '@/utils/routes'

/** Routes "racine" d'une zone — match exact requis pour ne pas matcher tous les sous-paths */
const ZONE_ROOTS: ReadonlyArray<string> = [ROUTES.dashboard.home, ROUTES.admin.home]

interface Props {
  items: ReadonlyArray<NavItem>
  /** Clé i18n pour le titre de la zone (ex: 'nav.merchantPanel') */
  titleI18nKey: string
}

defineProps<Props>()

const route = useRoute()

/**
 * Récupère le composant Lucide correspondant au nom d'icône.
 * Fallback sur null si l'icône n'existe pas (ne devrait pas arriver).
 */
function iconFor(name: string): Component | null {
  const icons = LucideIcons as unknown as Record<string, Component>
  return icons[name] ?? null
}

function isActive(to: string): boolean {
  // Pour la racine d'une zone, on exige un match exact pour ne pas l'activer
  // en permanence quand on est sur un sous-path.
  if (ZONE_ROOTS.includes(to)) {
    return route.path === to
  }
  return route.path.startsWith(to)
}
</script>

<template>
  <nav class="flex h-full flex-col gap-1 p-4" :aria-label="$t(titleI18nKey)">
    <div class="mb-2 px-3">
      <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {{ $t(titleI18nKey) }}
      </p>
    </div>

    <NuxtLink
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      :aria-current="isActive(item.to) ? 'page' : undefined"
      :class="[
        'inline-flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        isActive(item.to)
          ? 'bg-brand-forest text-brand-gold'
          : 'text-foreground hover:bg-muted',
      ]"
    >
      <component
        :is="iconFor(item.icon)"
        v-if="iconFor(item.icon)"
        class="h-4 w-4 shrink-0"
        aria-hidden="true"
      />
      <span>{{ $t(item.i18nKey) }}</span>
    </NuxtLink>
  </nav>
</template>
