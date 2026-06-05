/**
 * Types stricts des variables d'environnement et runtimeConfig.
 * Référence : ARCHITECTURE_FRONTEND.md section 5.4 (SSOT)
 *
 * Toute valeur sensible passe par runtimeConfig.<x> (server-only)
 * et NUXT_ENV via le préfixe.
 */

declare module 'nuxt/schema' {
  /**
   * Configuration serveur — JAMAIS exposée au browser.
   * Source : nuxt.config.ts:runtimeConfig
   * Override : variables d'env avec préfixe NUXT_*
   */
  interface RuntimeConfig {
    /** Clé partagée avec le backend FastAPI (X-Internal-Key) */
    proxyInternalApiKey: string
    /** Secret pour signer les cookies HttpOnly (min 32 chars) */
    sessionPassword: string
    /** URL absolue du backend FastAPI (ex: http://kalga-api:8001) */
    apiBackendUrl: string
  }

  /**
   * Configuration publique — exposée au browser.
   * Source : nuxt.config.ts:runtimeConfig.public
   */
  interface PublicRuntimeConfig {
    /** Chemin du proxy interne (jamais l'URL backend) */
    apiUrl: string
    /** DSN Sentry public (vide en dev) */
    sentryDsn: string
    /** development | staging | production */
    environment: 'development' | 'staging' | 'production'
  }
}

export {}
