import { test, expect } from "@playwright/test";

/**
 * SCAFFOLD E2E — Le dashboard charge les produits live (plan testing-e2e.md 6.2).
 *
 * KALGA cible : conversations + produits LIVE via Convex `useQuery` (decision D3).
 * Cote produits, la liste s'hydrate depuis Convex (reactif), pas un fetch REST.
 * La spec attend l'apparition des cartes produit (auto-wait) plutot qu'une
 * reponse reseau precise — le transport Convex est WebSocket, pas un GET /products.
 *
 * Marque `test.fixme` : le dashboard reel (route `/dashboard/produits`, cartes
 * `data-testid="product-card"`, etat vide) arrive avec le plan 006, et suppose
 * une session authentifiee (storageState, cf. testing-e2e.md 2.4) qui depend de
 * `/signup` + TEST_MODE. Lever le `.fixme` une fois 006 livre.
 */
test.describe("Dashboard produits", () => {
  test.fixme("liste les produits du marchand (live Convex)", async ({
    page,
  }) => {
    await page.goto("/dashboard/produits");

    // les produits s'affichent en cartes (hydratation reactive Convex)
    const cards = page.getByTestId("product-card");
    await expect(cards.first()).toBeVisible();
    // au moins une carte
    expect(await cards.count()).toBeGreaterThan(0);
  });

  test.fixme("etat vide si aucun produit", async ({ page }) => {
    await page.goto("/dashboard/produits");
    await expect(
      page.getByText(/aucun produit|commencez par/i),
    ).toBeVisible();
  });
});
