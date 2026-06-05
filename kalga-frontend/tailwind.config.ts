// Tailwind v4 config — KALGA Frontend
// Référence : ARCHITECTURE_FRONTEND.md section 2 (stack) + 7.8 (PWA theme)
//
// NOTE Tailwind v4 : la majorité de la config se fait désormais via le @theme
// directive dans `app/assets/css/tailwind.css`. Ce fichier reste utile pour :
// - le contentement (où Tailwind cherche les classes)
// - les plugins JS (tailwindcss-animate requis par shadcn-vue)
// - le mode dark (class-based)

import type { Config } from 'tailwindcss'
import animate from 'tailwindcss-animate'

export default {
  darkMode: 'class',
  // Tous les fichiers Vue/JS/TS de l'app sont sous `./app/` en Nuxt 4.
  // On limite le scan à cet arbre + le nuxt.config.ts (pour les classes éventuelles).
  content: ['./app/**/*.{vue,js,ts,jsx,tsx}', './nuxt.config.ts'],
  theme: {
    extend: {
      // Les couleurs KALGA sont définies en CSS variables dans tailwind.css
      // pour rester compatibles light/dark via shadcn.
      // Ici on déclare les noms sémantiques mappés sur ces variables.
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        // Marque KALGA — Refined Heritage palette
        // Source unique de vérité = tokens HSL dans `app/assets/css/tailwind.css`.
        // Permet le support light/dark sans duplication.
        brand: {
          forest: 'hsl(var(--primary))',
          gold: 'hsl(var(--secondary))',
          cream: 'hsl(var(--brand-cream))',
          deep: 'hsl(var(--brand-deep))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      fontFamily: {
        // Sans-serif pour UI dense (dashboards, formulaires, tableaux)
        sans: ['Inter', 'system-ui', 'sans-serif'],
        // Serif élégant pour titres storefront (vitrine luxe)
        serif: ['"Playfair Display"', 'Georgia', '"Times New Roman"', 'serif'],
      },
    },
  },
  plugins: [animate],
} satisfies Config
