import type { Page } from "@playwright/test"

/**
 * Stubs du proxy serveur WhatsApp `/api/wa/*` pour les E2E (plan 010 §B + Tests).
 *
 * Aucun bridge Baileys reel (port 3001) n'est requis : on intercepte cote
 * navigateur les routes que `useWhatsappStatus` appelle. Cela permet d'exercer
 * le RENDU et le POLLING de l'ecran « Connecter WhatsApp » de facon
 * deterministe, sans telephone ni session WhatsApp live.
 *
 * Sequence par defaut (chemin nominal) :
 *  - POST /api/wa/connect  -> 200 (socket initialisee).
 *  - GET  /api/wa/pairing  -> 200 { pairingCode } (code 8 caracteres).
 *  - GET  /api/wa/status   -> 200, `ready:false` au debut puis `ready:true`
 *    apres `readyAfter` appels (simule la liaison depuis le telephone).
 *  - GET  /api/wa/qr        -> PNG 1x1 (onglet QR).
 *
 * Toutes les routes doivent etre enregistrees AVANT `page.goto` (sinon la
 * premiere requete part avant le mock).
 */

export interface WaMockOptions {
  /** Code d'appairage renvoye par /api/wa/pairing (8 caracteres). */
  pairingCode?: string
  /** Numero reel remonte par le bridge une fois `ready`. */
  realPhone?: string
  /**
   * Nombre d'appels GET /api/wa/status avant de passer `ready:true`.
   * `Infinity` (defaut) = reste « en attente » (utile pour tester le rendu du
   * code + l'etat de polling sans declencher l'ecran de succes).
   */
  readyAfter?: number
}

/** PNG 1x1 transparent (base64) pour stubber /api/wa/qr. */
const PNG_1X1_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC"

export async function mockWhatsappBridge(
  page: Page,
  opts: WaMockOptions = {},
): Promise<void> {
  const pairingCode = opts.pairingCode ?? "ABCD1234"
  const realPhone = opts.realPhone ?? "2250708090910"
  const readyAfter = opts.readyAfter ?? Number.POSITIVE_INFINITY

  let statusCalls = 0

  await page.route("**/api/wa/connect", (route) =>
    route.fulfill({ status: 200, json: { ok: true } }),
  )

  await page.route("**/api/wa/pairing", (route) =>
    route.fulfill({ status: 200, json: { pairingCode } }),
  )

  await page.route("**/api/wa/status", (route) => {
    statusCalls += 1
    const ready = statusCalls >= readyAfter
    route.fulfill({
      status: 200,
      json: {
        connected: statusCalls > 1,
        ready,
        qrCode: "data:image/png;base64,stub",
        pairingCode,
        realPhone: ready ? realPhone : null,
      },
    })
  })

  await page.route("**/api/wa/qr", (route) =>
    route.fulfill({
      status: 200,
      contentType: "image/png",
      body: Buffer.from(PNG_1X1_BASE64, "base64"),
    }),
  )
}

/** Stub d'un bridge indisponible : /api/wa/status renvoie 503. */
export async function mockWhatsappBridgeDown(page: Page): Promise<void> {
  await page.route("**/api/wa/connect", (route) =>
    route.fulfill({ status: 503, json: { error: "service_down" } }),
  )
  await page.route("**/api/wa/pairing", (route) =>
    route.fulfill({ status: 503, json: { error: "service_down" } }),
  )
  await page.route("**/api/wa/status", (route) =>
    route.fulfill({ status: 503, json: { error: "service_down" } }),
  )
}
