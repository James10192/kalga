// Configuration Nuxt 4 — KALGA Frontend
// Référence : ARCHITECTURE_FRONTEND.md sections 2, 3, 7
//
// Choix clés :
// - Tailwind v4 via plugin Vite officiel (PAS @nuxtjs/tailwindcss qui ne supporte que v3)
// - shadcn-nuxt = module Nuxt officiel d'intégration shadcn-vue
// - i18n strategy 'prefix_except_default' = FR sur "/", EN sur "/en", AR sur "/ar"
// - SSG pour zones publiques (CDN-cacheables), SSR pour dashboards (auth requise)

import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  // -------------------------------------------------------------------------
  // Méta
  // -------------------------------------------------------------------------
  compatibilityDate: '2026-06-01',
  future: { compatibilityVersion: 4 },
  devtools: { enabled: true },

  // -------------------------------------------------------------------------
  // Modules (section 2 du doc)
  // -------------------------------------------------------------------------
  modules: [
    '@nuxtjs/i18n',
    '@pinia/nuxt',
    '@vueuse/nuxt',
    '@vite-pwa/nuxt',
    '@nuxt/eslint',
    'nuxt-auth-utils',
    'shadcn-nuxt',
    '@sentry/nuxt/module',
  ],

  // -------------------------------------------------------------------------
  // CSS — point d'entrée Tailwind v4 + tokens shadcn
  // -------------------------------------------------------------------------
  css: ['~/assets/css/tailwind.css'],

  // -------------------------------------------------------------------------
  // Vite — plugin Tailwind v4 (remplace @nuxtjs/tailwindcss en v4)
  // -------------------------------------------------------------------------
  vite: {
    plugins: [tailwindcss()],
  },

  // -------------------------------------------------------------------------
  // TypeScript strict (section 5.7 du doc — non-négociable)
  // -------------------------------------------------------------------------
  typescript: {
    strict: true,
    typeCheck: true,
  },

  // -------------------------------------------------------------------------
  // Auto-imports (section 5.5 du doc — convention over configuration)
  // Les features sont imbriquées : on doit déclarer les dossiers explicitement
  // -------------------------------------------------------------------------
  imports: {
    dirs: [
      'composables/**',
      'stores/**',
      'utils/**',
      'features/*/composables/**',
      'features/*/stores/**',
    ],
  },
  components: [
    { path: '~/components/ui', prefix: '' },
    { path: '~/components/layout', prefix: '' },
    { path: '~/components/shared', prefix: '' },
    { path: '~/features', pathPrefix: false },
  ],

  // -------------------------------------------------------------------------
  // Runtime config (section 5.4 du doc — SSOT pour URLs/secrets)
  // Les valeurs proviennent de .env via le préfixe NUXT_
  // -------------------------------------------------------------------------
  runtimeConfig: {
    // Côté serveur uniquement (jamais exposé au browser)
    // Tous les fallbacks sont vides : la valeur DOIT venir de .env / variables prod.
    // Sans ça, on évite qu'un déploiement prod pointe accidentellement vers localhost.
    proxyInternalApiKey: '', // NUXT_PROXY_INTERNAL_API_KEY (obligatoire)
    sessionPassword: '', // NUXT_SESSION_PASSWORD (obligatoire — cookies HttpOnly, min 32 chars)
    apiBackendUrl: '', // NUXT_API_BACKEND_URL (obligatoire — pas de fallback localhost)

    // Exposé au client
    public: {
      apiUrl: '/api/proxy', // proxy interne — jamais l'URL FastAPI directement
      sentryDsn: '', // NUXT_PUBLIC_SENTRY_DSN
      environment: 'development', // NUXT_PUBLIC_ENVIRONMENT (override en prod)
    },
  },

  // -------------------------------------------------------------------------
  // Route rules (section 3 + 7.1 du doc)
  // Storefront = SSG (CDN), Dashboards = SSR + middleware d'auth
  // -------------------------------------------------------------------------
  routeRules: {
    // Zone publique — SSG, cacheable au CDN
    '/': { prerender: true },
    '/boutique/**': { swr: 3600 }, // revalidation toutes les heures
    '/produit/**': { swr: 3600 },
    '/commander/**': { ssr: true }, // formulaire de commande — pas de cache

    // Zone marchand — SSR + auth
    '/dashboard/**': { ssr: true, appMiddleware: ['merchant'] },

    // Zone admin — SSR + auth + role check
    '/admin/**': { ssr: true, appMiddleware: ['merchant', 'admin'] },

    // Auth pages
    '/login': { ssr: true },
  },

  // -------------------------------------------------------------------------
  // shadcn-nuxt (section 7.5 du doc)
  // -------------------------------------------------------------------------
  shadcn: {
    prefix: '',
    componentDir: './app/components/ui',
  },

  // -------------------------------------------------------------------------
  // i18n (section 7.7 du doc) — FR défaut, EN, AR (RTL natif)
  // -------------------------------------------------------------------------
  i18n: {
    vueI18n: './i18n/i18n.config.ts', // chemin explicite vers la config Vue i18n (légacy false, fallback)
    defaultLocale: 'fr',
    strategy: 'prefix_except_default',
    locales: [
      { code: 'fr', language: 'fr-FR', name: 'Français', file: 'fr.json' },
      { code: 'en', language: 'en-US', name: 'English', file: 'en.json' },
      { code: 'ar', language: 'ar-MA', name: 'العربية', file: 'ar.json', dir: 'rtl' },
    ],
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'kalga_lang',
      redirectOn: 'root',
      fallbackLocale: 'fr',
    },
    bundle: { optimizeTranslationDirective: false },
  },

  // -------------------------------------------------------------------------
  // PWA (section 7.8 du doc)
  // -------------------------------------------------------------------------
  pwa: {
    registerType: 'autoUpdate',
    manifest: {
      name: 'KALGA',
      short_name: 'KALGA',
      description: 'Commerce WhatsApp automatisé pour marchands',
      lang: 'fr',
      theme_color: '#0F4234', // Forest Green (brand primary)
      background_color: '#F5F1E8', // Cream (storefront splash)
      display: 'standalone',
      start_url: '/dashboard',
      orientation: 'portrait',
      icons: [
        { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
        { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
        {
          src: '/icons/icon-512-maskable.png',
          sizes: '512x512',
          type: 'image/png',
          purpose: 'maskable',
        },
      ],
    },
    workbox: {
      navigateFallback: '/',
      // Cache First pour assets statiques, Network First pour API
      runtimeCaching: [
        {
          urlPattern: /^\/api\/proxy\/.*$/,
          handler: 'NetworkFirst',
          options: {
            cacheName: 'kalga-api-cache',
            networkTimeoutSeconds: 5,
            expiration: { maxEntries: 100, maxAgeSeconds: 300 },
          },
        },
      ],
    },
    client: { installPrompt: true },
    devOptions: { enabled: false },
  },

  // -------------------------------------------------------------------------
  // Sentry (section 7.9 du doc) — config minimaliste, étendue dans plugins
  // -------------------------------------------------------------------------
  sourcemap: { client: 'hidden' },

  // -------------------------------------------------------------------------
  // Nitro — server-side
  // -------------------------------------------------------------------------
  nitro: {
    experimental: { openAPI: false },
  },

  // -------------------------------------------------------------------------
  // App head — défauts SEO
  // -------------------------------------------------------------------------
  app: {
    head: {
      htmlAttrs: { lang: 'fr' },
      title: 'KALGA',
      titleTemplate: '%s · KALGA',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' },
        { name: 'description', content: 'Commerce WhatsApp automatisé pour marchands' },
        { name: 'theme-color', content: '#0F4234' }, // Forest brand
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
        // Google Fonts : Inter (UI) + Playfair Display (titres storefront)
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@400;500;600;700;800&display=swap',
        },
      ],
    },
  },
})
