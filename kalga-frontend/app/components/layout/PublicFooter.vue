<!--
  Footer de la zone publique (storefront).
  Référence : ARCHITECTURE_FRONTEND.md section 7.5

  Design minimaliste forest sur le fond crème pour contraste fort.
-->

<script setup lang="ts">
const currentYear = new Date().getFullYear()
</script>

<template>
  <footer class="mt-auto border-t border-border bg-foreground text-warning/90">
    <div class="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <div class="flex flex-col items-center gap-4 sm:flex-row sm:justify-between">
        <KalgaLogo size="sm" />

        <p class="text-xs">
          &copy; {{ currentYear }} KALGA — {{ $t('storefront.allRightsReserved') }}
        </p>
      </div>
    </div>
  </footer>
</template>
