/**
 * E2E Playwright — page de connexion marchand (/login).
 * Référence : ARCHITECTURE_FRONTEND.md section 7.6 (E2E sur flux critiques).
 *
 * Ces scénarios ne dépendent PAS du bridge WhatsApp : ils couvrent le rendu de
 * la page et la validation côté client (un numéro invalide ne déclenche aucun
 * appel réseau et affiche une erreur inline). Le flux de connexion réussi (QR)
 * sera couvert par une spec dédiée quand l'onboarding sera porté.
 */

import { expect, test } from '@playwright/test'

test.describe('Page de connexion marchand', () => {
  test('affiche le formulaire WhatsApp', async ({ page }) => {
    await page.goto('/login')

    // Titre de bienvenue + champ téléphone + bouton de connexion présents.
    await expect(page.getByRole('heading')).toBeVisible()
    await expect(page.locator('input[type="tel"]')).toBeVisible()
    await expect(page.getByRole('button', { name: /.+/ })).toBeVisible()
  })

  test('un numéro invalide affiche une erreur inline sans appel réseau', async ({ page }) => {
    let connectCalled = false
    await page.route('**/api/whatsapp/connect', (route) => {
      connectCalled = true
      return route.fulfill({ status: 200, body: '{}' })
    })

    await page.goto('/login')
    await page.locator('input[type="tel"]').fill('123') // trop court → invalide
    await page.getByRole('button').last().click()

    // L'alerte de validation apparaît, et le endpoint n'a pas été appelé.
    await expect(page.locator('[role="alert"]')).toBeVisible()
    expect(connectCalled).toBe(false)
  })
})
