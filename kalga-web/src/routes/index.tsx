import { createFileRoute, redirect } from '@tanstack/react-router'

/**
 * Racine `/` — redirige vers l'accueil du dashboard marchand (/app).
 * Le storefront public ({slug}.kalga.app) et la landing seront gérés
 * par hostname / routes dédiées en 007.
 */
export const Route = createFileRoute('/')({
  beforeLoad: () => {
    throw redirect({ to: '/app' })
  },
})
