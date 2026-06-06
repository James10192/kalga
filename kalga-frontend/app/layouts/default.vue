<!--
  Layout par défaut — zone publique (storefront acheteur).
  Référence : ARCHITECTURE_FRONTEND.md sections 3 (zones) + 7.5 (design)

  Caractéristiques :
  - Fond crème (), typographie serif sur titres
  - Header avec logo + nav + lang + cart
  - Footer forest deep avec copyright
-->

<script setup lang="ts">
// Pas de logique métier ici — orchestration pure
</script>

<template>
  <div class="flex min-h-screen flex-col bg-background text-foreground">
    <PublicHeader />

    <main class="flex-1">
      <slot />
    </main>

    <PublicFooter />
  </div>
</template>
