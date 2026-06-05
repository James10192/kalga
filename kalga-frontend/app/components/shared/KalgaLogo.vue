<!--
  Logo KALGA — composant réutilisable.
  Référence : ARCHITECTURE_FRONTEND.md section 7.5 (design system)

  - Cercle forest avec "K" en gold
  - Optionnellement le mot "KALGA" en serif à droite
  - Taille via prop `size` ('sm' | 'md' | 'lg')
-->

<script setup lang="ts">
type LogoSize = 'sm' | 'md' | 'lg'

interface Props {
  /** Taille du badge logo */
  size?: LogoSize
  /** Affiche le mot "KALGA" à côté du badge */
  withWordmark?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  withWordmark: true,
})

const SIZE_TOKENS: Record<LogoSize, { box: string; text: string; word: string }> = {
  sm: { box: 'h-8 w-8', text: 'text-base', word: 'text-lg' },
  md: { box: 'h-10 w-10', text: 'text-xl', word: 'text-2xl' },
  lg: { box: 'h-14 w-14', text: 'text-3xl', word: 'text-3xl' },
}

const tokens = computed(() => SIZE_TOKENS[props.size])
</script>

<template>
  <div class="inline-flex items-center gap-2.5" aria-label="KALGA">
    <span
      :class="[
        tokens.box,
        'inline-flex items-center justify-center rounded-md bg-brand-forest font-serif font-bold text-brand-gold',
      ]"
    >
      <span :class="tokens.text">K</span>
    </span>

    <span
      v-if="withWordmark"
      :class="[tokens.word, 'font-serif font-semibold tracking-tight text-brand-forest']"
    >
      KALGA
    </span>
  </div>
</template>
