import { test, expect } from "@playwright/test";

/**
 * SCAFFOLD E2E — Signup OTP telephone (plan testing-e2e.md, section 3.1 + 6.1).
 *
 * Strategie OTP : DETERMINISTE en mode test (`KALGA_TEST_MODE=1`). Le backend
 * accepte un code fixe ("000000") sans appeler le bridge WhatsApp reel. Aucun
 * OTP reel n'est jamais envoye en CI (pas de session WhatsApp `ready` requise).
 *
 * Marque `test.fixme` : l'UI signup reelle (routes `/signup`, ecran OTP) arrive
 * avec le plan 006 (dashboard) ET la porte TEST_MODE cote Convex/Better Auth.
 * Aujourd'hui seul `/login-test` (jetable, plan 003) existe. Lever le `.fixme`
 * une fois `/signup` + `KALGA_TEST_MODE` en place.
 *
 * Rappel anti-flaky : assertions auto-wait uniquement (toBeVisible / toHaveURL),
 * JAMAIS de `waitForTimeout`.
 */
test.describe("Signup OTP", () => {
  test.fixme("happy path -> dashboard (OTP deterministe TEST_MODE)", async ({
    page,
  }) => {
    // numero unique par run (evite la collision d'un user deja cree)
    const phone = `2250${Date.now().toString().slice(-9)}`;

    await page.goto("/signup");
    await page.getByLabel(/telephone|whatsapp/i).fill(phone);
    await page.getByRole("button", { name: /recevoir le code/i }).click();

    // l'ecran de saisie OTP doit apparaitre
    await expect(page.getByText(/code de verification/i)).toBeVisible();

    // OTP deterministe (backend en KALGA_TEST_MODE) — pas de WhatsApp reel
    await page.getByLabel(/code/i).fill("000000");
    await page.getByRole("button", { name: /valider/i }).click();

    // apres provision org + reload JWT, on atterrit sur le dashboard (ou onboarding)
    await expect(page).toHaveURL(/\/dashboard|\/onboarding/);
  });

  test.fixme("code invalide -> erreur, pas de redirection", async ({ page }) => {
    await page.goto("/signup");
    await page.getByLabel(/telephone|whatsapp/i).fill("2250141540178");
    await page.getByRole("button", { name: /recevoir le code/i }).click();

    await page.getByLabel(/code/i).fill("111111");
    await page.getByRole("button", { name: /valider/i }).click();

    await expect(page.getByText(/incorrect|invalide/i)).toBeVisible();
    await expect(page).not.toHaveURL(/\/dashboard/);
  });
});
