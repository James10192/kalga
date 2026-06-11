/**
 * E2E Playwright — page de connexion marchand (/login).
 * Référence : ARCHITECTURE_FRONTEND.md section 7.6 (E2E sur flux critiques).
 *
 * Ces scénarios ne dépendent PAS du bridge WhatsApp : ils couvrent le rendu de
 * la page et la validation côté client (un numéro invalide ne déclenche aucun
 * appel réseau et affiche une erreur inline). Le flux de connexion réussi (QR)
 * sera couvert par une spec dédiée quand l'onboarding sera porté.
 *
 * Sélecteurs choisis pour être non-ambigus :
 *  - `h1`                  : le titre « Bienvenue » (le panneau gauche a un h2).
 *  - `input[type="tel"]`   : le champ numéro de CountryPhoneInput.
 *  - `button[type="submit"]` : le bouton de connexion (le sélecteur pays est
 *    un `button type="button"`).
 */

import { expect, test } from '@playwright/test'

// Le 1er rendu en dev compile les routes Nuxt à la volée (lent) → on triple le
// timeout par défaut pour éviter les faux négatifs liés à la compilation.
test.slow()

test.describe('Page de connexion marchand', () => {
  test('affiche le formulaire WhatsApp', async ({ page }) => {
    await page.goto('/login')

    await expect(page.locator('h1')).toBeVisible()
    await expect(page.locator('input[type="tel"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('un numéro invalide affiche une erreur inline sans appel réseau', async ({ page }) => {
    let connectCalled = false
    await page.route('**/api/whatsapp/connect', (route) => {
      connectCalled = true
      return route.fulfill({ status: 200, body: '{}' })
    })

    await page.goto('/login')
    await page.locator('input[type="tel"]').fill('123') // 225123 → 6 chiffres, invalide
    await page.locator('button[type="submit"]').click()

    // L'alerte de validation apparaît, et le endpoint n'a pas été appelé.
    await expect(page.getByRole('alert')).toBeVisible()
    expect(connectCalled).toBe(false)
  })
})
