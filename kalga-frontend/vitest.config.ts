// Vitest config — KALGA Frontend
// Référence : ARCHITECTURE_FRONTEND.md section 7.6 (tests)
//
// Cibles : ≥80% sur composables et utils.
// Environment happy-dom pour les composants Vue (plus rapide que jsdom).

import { defineConfig } from 'vitest/config'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  test: {
    environment: 'happy-dom',
    globals: true,
    include: ['tests/unit/**/*.{test,spec}.ts', 'app/**/*.{test,spec}.ts'],
    exclude: ['node_modules', '.nuxt', '.output', 'tests/e2e/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: ['app/composables/**', 'app/utils/**', 'app/features/**/composables/**'],
      exclude: ['**/*.test.ts', '**/*.spec.ts', '**/types.ts', '**/schemas.ts'],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./app', import.meta.url)),
      '~': fileURLToPath(new URL('./', import.meta.url)),
    },
  },
})
