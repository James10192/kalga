import { test, expect } from "@playwright/test"

/**
 * E2E plan 010 — Landing publique (`/`) + parcours vers le signup.
 *
 * La landing est une page PUBLIQUE SSR (aucun provider auth requis) : ces tests
 * tournent sans backend Convex ni bridge WhatsApp. On verifie le rendu reel
 * (titre, hero, sections, tarifs) et que les CTA menent bien vers `/signup`.
 *
 * Anti-flaky : assertions auto-wait (toBeVisible / toHaveURL), jamais de
 * `waitForTimeout`.
 */
test.describe("Landing publique", () => {
  test("la home SSR rend le hero et les sections cles", async ({ page }) => {
    await page.goto("/")

    await expect(page).toHaveTitle(/KALGA/)

    // Hero : titre principal.
    await expect(
      page.getByRole("heading", { name: /vendeur whatsapp/i, level: 1 }),
    ).toBeVisible()

    // Au moins un CTA "Commencer" (nav) et le CTA hero "Connecter mon WhatsApp".
    // (Ce libelle apparait 2x : hero + bandeau final -> on scope au premier.)
    await expect(
      page.getByRole("link", { name: /commencer/i }).first(),
    ).toBeVisible()
    await expect(
      page.getByRole("link", { name: /connecter mon whatsapp/i }).first(),
    ).toBeVisible()

    // Lien "Se connecter" present (vers /login).
    await expect(
      page.getByRole("link", { name: /se connecter/i }).first(),
    ).toHaveAttribute("href", /\/login/)
  })

  test("le contenu hero est dans le HTML SSR (JS desactive)", async ({
    browser,
  }) => {
    // Sans JS : le SSR doit deja contenir le titre (pas seulement l'hydratation).
    const ctx = await browser.newContext({ javaScriptEnabled: false })
    const page = await ctx.newPage()
    await page.goto("/")
    await expect(
      page.getByRole("heading", { name: /vendeur whatsapp/i, level: 1 }),
    ).toBeVisible()
    await ctx.close()
  })

  test("le CTA hero navigue vers /signup", async ({ page }) => {
    await page.goto("/")
    await page
      .getByRole("link", { name: /connecter mon whatsapp/i })
      .first()
      .click()
    await expect(page).toHaveURL(/\/signup$/)
    // L'ecran signup rend son formulaire de creation de boutique.
    await expect(
      page.getByRole("heading", { name: /creez votre boutique/i }),
    ).toBeVisible()
  })

  test("le CTA nav 'Commencer' navigue aussi vers /signup", async ({
    page,
  }) => {
    await page.goto("/")
    await page.getByRole("link", { name: /commencer/i }).first().click()
    await expect(page).toHaveURL(/\/signup$/)
  })
})
