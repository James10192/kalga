import { test, expect } from "@playwright/test";

/**
 * SCAFFOLD E2E — Storefront public {slug} rend le catalogue (testing-e2e.md 6.3).
 *
 * Le storefront est SSR et multi-tenant par hostname ({slug}.kalga.app, plan 007).
 * En local/CI sans wildcard DNS, la boutique est servie par chemin (`/{slug}`)
 * ou via header Host simule ; cette spec utilise le chemin relatif a `baseURL`.
 *
 * Marque `test.fixme` : la route storefront reelle (catalogue SSR, cartes
 * `data-testid="product-card"`, 404 slug inconnu) arrive avec le plan 007.
 * Aujourd'hui `/` rend seulement le socle. Lever le `.fixme` une fois 007 livre.
 *
 * Le test "HTML SSR sans JS" verifie que le catalogue est rendu cote serveur
 * (pas seulement a l'hydratation) — important pour le SEO storefront.
 */
const SLUG = "marchand-0178"; // slug public d'un marchand de seed

test.describe("Storefront public", () => {
  test.fixme("rend le catalogue (SSR)", async ({ page }) => {
    await page.goto(`/${SLUG}`);

    // en-tete boutique
    await expect(
      page.getByRole("heading", { name: /marchand 0178/i }),
    ).toBeVisible();

    // au moins une carte produit
    await expect(page.getByTestId("product-card").first()).toBeVisible();

    // prix en XOF / FCFA
    await expect(page.getByText(/XOF|FCFA/i).first()).toBeVisible();
  });

  test.fixme("slug inexistant -> 404", async ({ page }) => {
    const res = await page.goto("/slug-qui-nexiste-pas-xyz");
    expect(res?.status()).toBe(404);
    await expect(page.getByText(/introuvable|404/i)).toBeVisible();
  });

  test.fixme("contenu present dans le HTML SSR (JS desactive)", async ({
    browser,
  }) => {
    const ctx = await browser.newContext({ javaScriptEnabled: false });
    const page = await ctx.newPage();
    await page.goto(`http://localhost:3000/${SLUG}`);
    // visible sans hydratation cliente => rendu cote serveur
    await expect(page.getByTestId("product-card").first()).toBeVisible();
    await ctx.close();
  });
});
