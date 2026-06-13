import { test, expect } from "@playwright/test"
import { mockWhatsappBridge } from "./helpers/wa-mock"
import { resolveAuthStorageState } from "./helpers/auth"

/**
 * E2E plan 010 §F — Dashboard responsive (sidebar desktop vs bottom bar mobile).
 *
 * L'AppShell rend les DEUX layouts en parallele et bascule par media query
 * (`lg:hidden` / `hidden lg:flex`). `toBeVisible()` respecte la visibilite CSS :
 *  - >= lg (>=1024px) : la DesktopSidebar est visible, la bottom bar masquee.
 *  - < lg  (mobile)   : la bottom bar « liquid glass » est visible, sidebar masquee.
 *
 * Gate auth : ces ecrans vivent sous `/app` (session requise). On reutilise un
 * `storageState` authentifie s'il existe, sinon `test.skip` propre.
 * Le bridge WhatsApp est stubbe (l'AppShell lit `currentMerchant`/statut WA).
 *
 * Distinction des deux nav (memes `aria-label`) :
 *  - sidebar desktop : contient la marque « KALGA » + lien « Reglages ».
 *  - bottom bar mobile : contient le FAB central « Accueil » (lien aria-label).
 */

const storageState = resolveAuthStorageState()

const LG = { width: 1280, height: 900 }
const MOBILE = { width: 390, height: 844 }

test.describe("Dashboard responsive", () => {
  test.skip(
    storageState === null,
    "Aucune session E2E (KALGA_E2E_STORAGE_STATE / playwright/.auth/user.json). Voir MANUAL-onboarding.md.",
  )

  if (storageState) test.use({ storageState })

  test("au format desktop (>= lg) : sidebar visible, pas de bottom bar", async ({
    page,
  }) => {
    await mockWhatsappBridge(page)
    await page.setViewportSize(LG)
    await page.goto("/app")

    // Sidebar desktop : marque KALGA + items.
    const sidebar = page.getByRole("complementary").or(page.locator("aside"))
    await expect(sidebar.first()).toBeVisible()
    await expect(
      page.getByRole("link", { name: /^reglages$/i }),
    ).toBeVisible()

    // FAB Accueil (bottom bar) masque au format desktop.
    await expect(
      page.getByRole("link", { name: /^accueil$/i }),
    ).toBeHidden()
  })

  test("au format mobile (< lg) : bottom bar visible, pas de sidebar", async ({
    page,
  }) => {
    await mockWhatsappBridge(page)
    await page.setViewportSize(MOBILE)
    await page.goto("/app")

    // FAB central « Accueil » de la liquid-glass bottom bar.
    await expect(
      page.getByRole("link", { name: /^accueil$/i }),
    ).toBeVisible()

    // La sidebar desktop est masquee en mobile.
    await expect(page.locator("aside").first()).toBeHidden()
  })

  test("la chip statut WhatsApp (top bar desktop) mene a /app/connexion", async ({
    page,
  }) => {
    await mockWhatsappBridge(page)
    await page.setViewportSize(LG)
    await page.goto("/app")

    // La puce statut (Connecte / Non connecte) est un lien vers connexion.
    const chip = page.getByRole("link", { name: /whatsapp/i }).first()
    await expect(chip).toBeVisible()
    await expect(chip).toHaveAttribute("href", /\/app\/connexion/)
  })
})
