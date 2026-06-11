/**
 * État partagé — marchand de la vitrine en cours de consultation.
 *
 * Le header de la vitrine (StorefrontHeader) affiche le branding du MARCHAND
 * (logo + nom), pas la nav plateforme. Mais les pages /produit/:code n'ont pas
 * le téléphone du marchand dans l'URL — c'est la page qui connaît le marchand
 * (via l'API). On le partage donc via un `useState` que la page renseigne et
 * que le header lit. Référence : storefront.js (renderNav).
 *
 * Nommé `useStorefrontContext` pour ne PAS entrer en collision avec
 * `useStorefrontMerchant` (useStorefront.ts), qui FETCH la boutique.
 */

import type { StorefrontMerchant } from '../types'

export function useStorefrontContext() {
  return useState<StorefrontMerchant | null>('storefront-merchant', () => null)
}
