// Config i18n — KALGA Frontend
// Référence : ARCHITECTURE_FRONTEND.md section 7.7
//
// Langues :
// - FR (défaut) — Côte d'Ivoire
// - EN — expansion régionale anglophone

export default defineI18nConfig(() => ({
  legacy: false,
  defaultLocale: 'fr',
  fallbackLocale: 'fr',
  missingWarn: false,
  fallbackWarn: false,
}))
