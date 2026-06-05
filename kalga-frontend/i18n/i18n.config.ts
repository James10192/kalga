// Config i18n — KALGA Frontend
// Référence : ARCHITECTURE_FRONTEND.md section 7.7
//
// Langues V1 :
// - FR (défaut) — Côte d'Ivoire
// - EN — expansion régionale anglophone
// - AR — RTL natif (configuré via `dir: 'rtl'` dans nuxt.config.ts)

export default defineI18nConfig(() => ({
  legacy: false,
  defaultLocale: 'fr',
  fallbackLocale: 'fr',
  missingWarn: false,
  fallbackWarn: false,
}))
