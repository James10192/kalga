import { defineConfig } from "vitest/config";

/**
 * Config Vitest pour les tests backend Convex (convex-test).
 *
 * - `environment: "edge-runtime"` : OBLIGATOIRE, convex-test simule le runtime
 *   Convex (V8 isolate-like). Sans `@edge-runtime/vm`, Vitest crashe.
 * - `server.deps.inline: ["convex-test"]` : resolution module ESM correcte.
 * - `include` : on ne ramasse que les tests Convex (les E2E Playwright vivent
 *   dans `tests/e2e/` et sont lances par `playwright test`, pas par Vitest).
 *
 * Reference : plans/reference/testing-e2e.md (section 4.1).
 */
export default defineConfig({
  test: {
    environment: "edge-runtime",
    server: { deps: { inline: ["convex-test"] } },
    include: ["convex/**/*.test.ts"],
  },
});
