<!--
  Layout minimaliste — utilisé pour login, QR scan, pages d'auth.
  Référence : ARCHITECTURE_FRONTEND.md section 7.5

  Pas de header ni de sidebar : juste le slot centré sur fond crème.
-->

<template>
  <div
    class="flex min-h-screen items-center justify-center bg-background px-4 py-8 text-foreground"
  >
    <slot />
  </div>
</template>
