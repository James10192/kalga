import { defineConfig, devices } from "@playwright/test";

/**
 * Config Playwright E2E (plan testing-e2e.md, section 1.2).
 *
 * Port : `pnpm dev` = `vite dev` sert sur le port 3000 (vite.config.ts:server.port).
 * `webServer.url`, `webServer.command` et `use.baseURL` sont alignes dessus.
 *
 * OTP : en CI on active l'OTP deterministe via `KALGA_TEST_MODE=1` (section 3.1) ;
 * aucun OTP WhatsApp reel n'est requis. Les specs OTP sont des SCAFFOLDS marques
 * `test.fixme` tant que l'UI signup (plan 006) et la porte TEST_MODE n'existent pas.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI, // empeche un test.only de passer en CI
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI
    ? [["github"], ["html", { open: "never" }]]
    : "list",

  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],

  webServer: {
    command: "pnpm dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000, // TanStack Start / Vite peut mettre du temps a boot
    stdout: "pipe",
    stderr: "pipe",
  },
});
