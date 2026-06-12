import { test, expect } from "@playwright/test";

/**
 * SMOKE E2E — Le dashboard marchand 006 rend ses ecrans cles (plan 006 livre).
 *
 * Les routes /app et /app/products ne sont pas encore protegees (l'auth
 * withOrg + OTP arrivent en 003/004) : elles resolvent le marchand demo via le
 * slug `demo` et s'hydratent depuis Convex (`useQuery`, transport WebSocket).
 *
 * On verifie le chrome qui rend independamment des donnees (en-tetes, barre
 * d'onglets bas), puis on attend les cartes produit via l'auto-wait Playwright
 * (`data-testid="product-card"`) plutot qu'un `waitForTimeout`. Le seed Convex
 * (`npx convex run seed:run`) fournit les produits du slug demo.
 */
test.describe("Dashboard marchand 006", () => {
  test("la home /app rend (conversations + barre d'onglets)", async ({
    page,
  }) => {
    await page.goto("/app");

    // Titre de section "Conversations" (colonne vertebrale, DIRECTION.md).
    await expect(
      page.getByRole("heading", { name: "Conversations" }),
    ).toBeVisible();

    // Barre d'onglets bas : les 4 onglets au pouce sont presents.
    const tabbar = page.getByRole("navigation");
    await expect(
      tabbar.getByText("Conversations", { exact: true }),
    ).toBeVisible();
    await expect(tabbar.getByText("Produits", { exact: true })).toBeVisible();
    await expect(tabbar.getByText("Argent", { exact: true })).toBeVisible();
    await expect(tabbar.getByText("Réglages", { exact: true })).toBeVisible();
  });

  test("la page /app/products rend (en-tete + grille produits live)", async ({
    page,
  }) => {
    await page.goto("/app/products");

    // En-tete "Produits" (rend immediatement, independant des donnees).
    await expect(
      page.getByRole("heading", { name: "Produits" }),
    ).toBeVisible();

    // Les cartes produit s'hydratent depuis Convex (seed demo).
    // Auto-wait sur la premiere carte, pas de waitForTimeout.
    const cards = page.getByTestId("product-card");
    await expect(cards.first()).toBeVisible();
    expect(await cards.count()).toBeGreaterThan(0);
  });
});
