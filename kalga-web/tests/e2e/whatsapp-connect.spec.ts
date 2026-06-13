import { test, expect } from "@playwright/test"
import { mockWhatsappBridge, mockWhatsappBridgeDown } from "./helpers/wa-mock"
import { resolveAuthStorageState } from "./helpers/auth"

/**
 * E2E plan 010 — Ecran « Connecter WhatsApp » (`/app/connexion`).
 *
 * Cet ecran vit sous `/app`, derriere la gate d'auth : il faut donc une session
 * reelle. On reutilise un `storageState` authentifie s'il est disponible
 * (KALGA_E2E_STORAGE_STATE ou playwright/.auth/user.json) ; sinon la suite est
 * `test.skip` proprement (jamais rouge). Voir tests/e2e/MANUAL-onboarding.md.
 *
 * Le BRIDGE WhatsApp (port 3001) est entierement STUBBE cote navigateur via
 * `mockWhatsappBridge` : aucun telephone ni socket Baileys reels. On exerce
 * ainsi le rendu (code d'appairage, toggle Code/QR, etapes) ET le polling de
 * `/api/wa/status` de facon deterministe.
 *
 * Anti-flaky : assertions auto-wait, jamais de `waitForTimeout`.
 */

const storageState = resolveAuthStorageState()

test.describe("Connecter WhatsApp", () => {
  test.skip(
    storageState === null,
    "Aucune session E2E (KALGA_E2E_STORAGE_STATE / playwright/.auth/user.json). Voir MANUAL-onboarding.md.",
  )

  if (storageState) test.use({ storageState })

  test("rend le code d'appairage et les etapes (onglet Code par defaut)", async ({
    page,
  }) => {
    await mockWhatsappBridge(page, { pairingCode: "ABCD1234" })
    await page.goto("/app/connexion")

    // Titre de l'ecran.
    await expect(
      page.getByRole("heading", { name: /connecter whatsapp/i }),
    ).toBeVisible()

    // Toggle segmente Code / QR present.
    await expect(page.getByRole("button", { name: /^code$/i })).toBeVisible()
    await expect(page.getByRole("button", { name: /^qr$/i })).toBeVisible()

    // Code d'appairage rendu cellule par cellule (8 caracteres : ABCD-1234).
    const copyBtn = page.getByRole("button", {
      name: /copier le code d'appairage/i,
    })
    await expect(copyBtn).toBeVisible()
    await expect(copyBtn).toContainText("A")
    await expect(copyBtn).toContainText("4")

    // Les etapes WhatsApp FR (texte exact du flow).
    await expect(
      page.getByText(/ouvrez whatsapp sur ce telephone/i),
    ).toBeVisible()
    await expect(
      page.getByText(/lier avec un numero/i),
    ).toBeVisible()

    // Statut vivant : "En attente de connexion..." tant que pas `ready`.
    await expect(
      page.getByText(/en attente de connexion/i),
    ).toBeVisible()
  })

  test("le toggle bascule vers l'onglet QR", async ({ page }) => {
    await mockWhatsappBridge(page)
    await page.goto("/app/connexion")

    await page.getByRole("button", { name: /^qr$/i }).click()

    // L'image QR (servie par /api/wa/qr, stubbee) doit apparaitre + l'aide.
    await expect(
      page.getByRole("img", { name: /qr code d'appairage whatsapp/i }),
    ).toBeVisible()
    await expect(
      page.getByText(/scannez depuis un autre telephone/i),
    ).toBeVisible()
  })

  test("le polling /api/wa/status mene a l'ecran de succes quand ready", async ({
    page,
  }) => {
    // `ready:true` apres 2 appels de statut : exerce reellement le poll.
    await mockWhatsappBridge(page, { readyAfter: 2 })

    let statusPolls = 0
    page.on("request", (req) => {
      if (req.url().includes("/api/wa/status")) statusPolls += 1
    })

    await page.goto("/app/connexion")

    // L'ecran de succes apparait une fois `ready` (auto-wait couvre le poll ~2.5s).
    await expect(
      page.getByRole("heading", { name: /votre boutique est prete/i }),
    ).toBeVisible({ timeout: 15000 })
    await expect(
      page.getByRole("link", { name: /aller au tableau de bord/i }),
    ).toBeVisible()

    // Au moins un poll a eu lieu (preuve que le hook interroge /api/wa/status).
    expect(statusPolls).toBeGreaterThan(0)
  })

  test("bridge indisponible affiche un message de service", async ({
    page,
  }) => {
    await mockWhatsappBridgeDown(page)
    await page.goto("/app/connexion")
    await expect(
      page.getByText(/service indisponible/i),
    ).toBeVisible()
  })
})
