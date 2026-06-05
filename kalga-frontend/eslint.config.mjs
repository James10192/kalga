// ESLint flat config — KALGA Frontend
// Référence : ARCHITECTURE_FRONTEND.md section 2 (qualité) + 10 (anti-patterns)
//
// On s'appuie sur @nuxt/eslint qui fournit déjà :
// - Vue 3 recommended
// - TypeScript recommended
// - Nuxt-specific rules (composants auto-imports, etc.)
// On ajoute par-dessus nos règles métier non-négociables.

import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt({
  rules: {
    // Anti-patterns du doc section 10
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'no-debugger': 'error',
    'vue/no-v-html': 'error', // XSS protection — voir doc section 5.7

    // Lisibilité
    'vue/component-name-in-template-casing': ['error', 'PascalCase'],
    'vue/multi-word-component-names': 'off', // Nuxt pages peuvent être mono-mot
    'vue/no-unused-vars': 'error',

    // TypeScript strict (section 5.7)
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/no-unused-vars': [
      'error',
      { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
    ],
    '@typescript-eslint/consistent-type-imports': [
      'error',
      { prefer: 'type-imports', fixStyle: 'inline-type-imports' },
    ],
  },
})
