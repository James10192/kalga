import { test, expect } from "@playwright/test"
import { mockWhatsappBridge } from "./helpers/wa-mock"
import { resolveAuthStorageState } from "./helpers/auth"

/**
 * E2E plan 010 — Le dashboard marchand rend ses ecrans cles UNE FOIS authentifie.
 *
 * Mise a jour plan 010 : `/app/*` est desormais PROTEGE (`expectAuth: true`,
 * gate `beforeLoad`). L'ancienne hypothese « routes non protegees + slug demo »
 * (plan 006) est obsolete. La redirection sans session est couverte par
 * `auth-gate.spec.ts` ; ici on verifie le rendu du dashboard AVEC session.
 *
 * Gate auth : ces ecrans exigent une session reelle (Convex + Better Auth). On
 * reutilise un `storageState` authentifie s'il existe, sinon `test.skip` propre
 * (voir MANUAL-onboarding.md). Le bridge WhatsApp est stubbe (AppShell lit le
 * statut WA via `currentMerchant`). Aucun bridge live requis.
 *
 * Anti-flaky : auto-wait (toBeVisible / getByTestId), jamais de `waitForTimeout`.
 */

const storageState = resolveAuthStorageState()

test.describe("Dashboard marchand (authentifie)", () => {
  test.skip(
    storageState === null,
    "Aucune session E2E (KALGA_E2E_STORAGE_STATE / playwright/.auth/user.json). Voir MANUAL-onboarding.md.",
  )

  if (storageState) test.use({ storageState })

  test("la home /app rend (fil + navigation)", async ({ page }) => {
    await mockWhatsappBridge(page)
    await page.goto("/app")

    // Une navigation principale est presente (sidebar desktop ou bottom bar).
    await expect(page.getByRole("navigation").first()).toBeVisible()
  })

  test("la page /app/products rend (en-tete + grille produits)", async ({
    page,
  }) => {
    await mockWhatsappBridge(page)
    await page.goto("/app/products")

    await expect(
      page.getByRole("heading", { name: "Produits" }),
    ).toBeVisible()

    // Les cartes produit s'hydratent depuis Convex (seed demo) si presentes.
    const cards = page.getByTestId("product-card")
    await expect(cards.first()).toBeVisible()
  })
})
