<!--
  Layout VITRINE CLIENT (boutique / produit / commande).
  Header = branding marchand (StorefrontHeader), pas la nav plateforme.
  Footer KALGA conservé (mention « propulsé par »).
-->

<script setup lang="ts">
// Orchestration pure.
</script>

<template>
  <div class="flex min-h-screen flex-col bg-background text-foreground">
    <StorefrontHeader />

    <main class="flex-1">
      <slot />
    </main>

    <PublicFooter />
  </div>
</template>
