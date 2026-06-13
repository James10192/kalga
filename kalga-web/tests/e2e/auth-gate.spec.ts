import { test, expect } from "@playwright/test"

/**
 * E2E plan 010 — Gating d'authentification des routes `/app/*`.
 *
 * `app/route.tsx` `beforeLoad` redirige vers `/login` quand il n'y a pas de
 * session (`!context.isAuthenticated`). Le contexte d'auth est resolu cote
 * serveur (token cookie) AVANT toute donnee Convex : la redirection ne depend
 * donc PAS d'un backend live. Ces tests partent d'un navigateur SANS session
 * (contexte neuf, aucun cookie) -> ils sont deterministes et sans backend.
 *
 * Anti-flaky : `toHaveURL` auto-wait, jamais de `waitForTimeout`.
 */
test.describe("Gate auth /app", () => {
  test("visiter /app sans session redirige vers /login", async ({ page }) => {
    await page.goto("/app")
    await expect(page).toHaveURL(/\/login(\?|$)/)
    // L'ecran de connexion s'affiche reellement.
    await expect(
      page.getByRole("heading", { name: /bon retour/i }),
    ).toBeVisible()
  })

  test("visiter /app/connexion sans session redirige vers /login", async ({
    page,
  }) => {
    await page.goto("/app/connexion")
    await expect(page).toHaveURL(/\/login(\?|$)/)
  })

  test("visiter /app/products sans session redirige vers /login", async ({
    page,
  }) => {
    await page.goto("/app/products")
    await expect(page).toHaveURL(/\/login(\?|$)/)
  })

  test("la page /login propose un lien vers /signup", async ({ page }) => {
    await page.goto("/login")
    await expect(
      page.getByRole("link", { name: /creer un compte/i }),
    ).toHaveAttribute("href", /\/signup/)
  })
})
