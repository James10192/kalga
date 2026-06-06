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
}, {
  // Exception ciblée aux tests (justifiée — cf. doc §10) :
  // - `no-explicit-any` : on caste les options capturées des mocks TanStack
  //   Query pour inspecter queryKey/queryFn/onSuccess (introspection runtime).
  // - `import/first` : `vi.mock` est hoisté par vitest ; l'idiome canonique le
  //   place en tête de fichier, avant les imports.
  files: ['tests/**/*.{test,spec}.ts'],
  rules: {
    '@typescript-eslint/no-explicit-any': 'off',
    'import/first': 'off',
  },
}, {
  // Les fichiers de config (.mjs/.cjs/.js) ne font pas partie du projet
  // TypeScript (absents de tsconfig), donc pas d'info de type. On désactive
  // les règles type-aware pour eux, sinon `consistent-type-imports` plante au
  // chargement (« rule requires type information ») sur eslint.config.mjs.
  files: ['**/*.{mjs,cjs,js}'],
  rules: {
    '@typescript-eslint/consistent-type-imports': 'off',
  },
}, {
  // Scripts de build/maintenance (postinstall, patches) : le logging de
  // progression sur stdout via console.log est légitime et attendu.
  files: ['scripts/**/*.{mjs,cjs,js,ts}'],
  rules: {
    'no-console': 'off',
  },
})
