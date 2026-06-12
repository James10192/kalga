# KALGA — Stratégie de tests E2E + unit + intégration (fichier de référence)

> Fichier de référence pour agents exécuteurs SANS contexte. Tout est concret et copiable.
> Versions confirmées (juin 2026) : `@playwright/test` **1.58.x**, `vitest` **3.x**, `convex-test` **0.0.38+**, `convex` **1.27+**.
> Stack KALGA cible E2E : app Vite / TanStack Start (frontend), FastAPI (kalga-api, port 8001), Node Baileys bridge (kalga-whatsapp, port 3001).
> Si un backend Convex est introduit, sections 4 et 5 s'appliquent. Sinon, l'auth OTP est exercée via l'API FastAPI (section 3, variante REST).

---

## 0. Vue d'ensemble — pyramide de tests

| Niveau | Outil | Quoi | Vitesse | CI |
|--------|-------|------|---------|-----|
| Unit (FE) | Vitest | composants, hooks, utils pures | ms | toujours |
| Unit/integration (backend Convex) | Vitest + convex-test | mutations, queries, actions, scheduler | ms | toujours |
| Unit (backend FastAPI) | pytest | détecteurs AI, repos, calculs | ms | toujours |
| E2E | Playwright | flows réels navigateur (SSR, formulaires, auth OTP) | s | toujours (sur CI Linux headless) |

Règle : beaucoup d'unit, quelques convex-test/integration, peu d'E2E (les flows critiques seulement : signup OTP, dashboard charge produits, storefront public).

---

## 1. Playwright dans une app Vite / TanStack Start

### 1.1 Install (pnpm — jamais npm)

```bash
# Depuis la racine de l'app frontend (celle qui a le package.json + vite.config.ts)
pnpm add -D @playwright/test
pnpm exec playwright install chromium          # binaire navigateur (obligatoire)
# CI Linux : installer aussi les deps système
pnpm exec playwright install --with-deps chromium
```

> `playwright install` télécharge les binaires navigateurs dans `~/.cache/ms-playwright` (Linux) / `%USERPROFILE%\AppData\Local\ms-playwright` (Windows). Ce n'est PAS fait par `pnpm add`. Oublier cette étape = `Executable doesn't exist` au run.

### 1.2 `playwright.config.ts` (racine app)

```ts
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,          // empêche test.only de passer en CI
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',

  use: {
    baseURL: 'http://localhost:3000',     // permet page.goto('/route') relatif
    trace: 'on-first-retry',              // trace.zip rejouable sur échec
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    // décommenter si besoin multi-browser :
    // { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    // { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],

  // Démarre automatiquement le dev server avant les tests.
  // Pour TanStack Start / Vite, lance le SSR dev server.
  webServer: {
    command: 'pnpm dev',                  // doit servir sur le port ci-dessous
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI, // en local réutilise un serveur déjà lancé
    timeout: 120 * 1000,                  // TanStack Start peut mettre du temps à boot
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
```

**Gotcha TanStack Start / Vite** : `pnpm dev` sert souvent sur le port **3000** (Start) ou **5173** (Vite SPA). Aligner `webServer.url`, `webServer.command` et `use.baseURL` sur le VRAI port. Vérifier dans `package.json` le script `dev` et son `--port`.

**Multi-server** (frontend + backend FastAPI ensemble) : passer un tableau à `webServer` :

```ts
webServer: [
  { command: 'pnpm dev', url: 'http://localhost:3000', reuseExistingServer: !process.env.CI, timeout: 120000 },
  { command: 'cd ../kalga-api && uvicorn app.main:app --port 8001', url: 'http://localhost:8001/docs', reuseExistingServer: !process.env.CI, timeout: 120000 },
],
```

### 1.3 Scripts `package.json`

```jsonc
{
  "scripts": {
    "test:unit": "vitest run",
    "test:unit:watch": "vitest",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",        // mode UI interactif local
    "test:e2e:headed": "playwright test --headed",
    "test:e2e:report": "playwright show-report"
  }
}
```

### 1.4 `.gitignore`

```
/test-results/
/playwright-report/
/blob-report/
/playwright/.cache/
```

---

## 2. Écrire un E2E (navigation SSR, formulaires, attentes)

### 2.1 Principes Playwright (web-first assertions = auto-wait)

- **Toujours** utiliser `await expect(locator).toBeVisible()` etc. — les assertions Playwright RÉESSAIENT automatiquement jusqu'au timeout. Ne JAMAIS faire `waitForTimeout` arbitraire.
- **Locators sémantiques** par priorité : `getByRole` > `getByLabel` > `getByPlaceholder` > `getByText` > `getByTestId`. Éviter les sélecteurs CSS fragiles.
- Pour un `data-testid` : `page.getByTestId('product-card')` (config par défaut lit l'attribut `data-testid`).

### 2.2 Exemple basique — navigation SSR + assertion

```ts
// tests/e2e/smoke.spec.ts
import { test, expect } from '@playwright/test';

test('la home SSR rend le titre', async ({ page }) => {
  await page.goto('/');                                  // relatif grâce à baseURL
  await expect(page).toHaveTitle(/KALGA/);
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
});
```

**SSR-specific** : pour vérifier que le HTML SSR (pas seulement l'hydratation client) contient le contenu, on peut couper le JS :

```ts
test('contenu présent dans le HTML SSR (sans JS)', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto('http://localhost:3000/');
  await expect(page.getByRole('heading', { name: /catalogue/i })).toBeVisible();
  await ctx.close();
});
```

### 2.3 Formulaires + attentes de navigation

```ts
// tests/e2e/login.spec.ts
import { test, expect } from '@playwright/test';

test('login redirige vers le dashboard', async ({ page }) => {
  await page.goto('/login');

  // Remplir via label (accessible) plutôt que sélecteur CSS
  await page.getByLabel('Téléphone').fill('0141540178');
  await page.getByRole('button', { name: /continuer|se connecter/i }).click();

  // Attendre la nav SPA (window.location.href OU router). toHaveURL auto-retry.
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByText(/mes produits/i)).toBeVisible();
});
```

**Patterns d'attente clés** :
- `await expect(page).toHaveURL(/regex/)` — attend changement d'URL (marche aussi sur push router SPA).
- `await expect(locator).toBeVisible()` — attend apparition (auto-retry jusqu'à timeout 5s par défaut).
- `await expect(locator).toHaveText('...')` / `toContainText`.
- `await expect(locator).toHaveCount(4)` — utile pour "le dashboard liste 4 produits".
- `await page.waitForResponse(r => r.url().includes('/api/products') && r.ok())` — attend une réponse réseau précise.
- **Anti-pattern interdit** : `await page.waitForTimeout(3000)`. Source de flakiness. Utiliser les assertions auto-wait.

### 2.4 Fixtures réutilisables (storage state pour rester loggé)

Pour ne pas relogger à chaque test, sauvegarder l'état d'auth une fois (setup project) et le réutiliser :

```ts
// tests/e2e/auth.setup.ts
import { test as setup, expect } from '@playwright/test';
const authFile = 'playwright/.auth/user.json';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Téléphone').fill('0141540178');
  await page.getByRole('button', { name: /continuer/i }).click();
  // (compléter OTP — voir section 3)
  await page.getByLabel(/code/i).fill('123456');
  await page.getByRole('button', { name: /valider/i }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await page.context().storageState({ path: authFile });
});
```

```ts
// dans playwright.config.ts, ajouter aux projects :
projects: [
  { name: 'setup', testMatch: /auth\.setup\.ts/ },
  {
    name: 'chromium',
    use: { ...devices['Desktop Chrome'], storageState: 'playwright/.auth/user.json' },
    dependencies: ['setup'],            // exécute setup d'abord
  },
],
```

---

## 3. Tester un flow AUTH OTP (téléphone + OTP WhatsApp) en E2E

Le problème : l'OTP est envoyé hors-bande (WhatsApp), donc le navigateur ne le connaît pas. Trois stratégies, par ordre de robustesse.

### 3.1 Stratégie A — OTP déterministe en mode test (RECOMMANDÉE)

Le backend accepte un OTP fixe (ex `000000`) OU n'importe quel code quand `NODE_ENV=test` / `KALGA_TEST_MODE=1`. Le plus simple et fiable.

```ts
// tests/e2e/signup-otp.spec.ts
import { test, expect } from '@playwright/test';

test('signup OTP — happy path', async ({ page }) => {
  const phone = `01${Date.now().toString().slice(-8)}`;   // numéro unique par run

  await page.goto('/signup');
  await page.getByLabel('Téléphone').fill(phone);
  await page.getByRole('button', { name: /recevoir le code/i }).click();

  // L'écran OTP doit s'afficher
  await expect(page.getByText(/code de vérification/i)).toBeVisible();

  // OTP de test déterministe (backend en KALGA_TEST_MODE)
  await page.getByLabel(/code/i).fill('000000');
  await page.getByRole('button', { name: /valider/i }).click();

  await expect(page).toHaveURL(/\/dashboard|\/onboarding/);
});
```

Backend (côté FastAPI ou Convex) à prévoir : `if settings.TEST_MODE and code == "000000": valid = True`. Documenter cette porte dans l'env de test SEULEMENT, jamais en prod.

### 3.2 Stratégie B — Récupérer l'OTP via une API de test interne

Le backend expose un endpoint test-only `GET /test/last-otp?phone=...` qui renvoie le dernier code généré (gardé en mémoire/DB). Plus réaliste (exerce la vraie génération) mais nécessite un endpoint protégé par flag test.

```ts
test('signup OTP via endpoint test', async ({ page, request }) => {
  const phone = `01${Date.now().toString().slice(-8)}`;
  await page.goto('/signup');
  await page.getByLabel('Téléphone').fill(phone);
  await page.getByRole('button', { name: /recevoir le code/i }).click();
  await expect(page.getByText(/code de vérification/i)).toBeVisible();

  // Lire l'OTP réellement généré côté backend (endpoint test-only)
  const res = await request.get(`http://localhost:8001/test/last-otp?phone=225${phone.replace(/^0/, '')}`);
  const { code } = await res.json();

  await page.getByLabel(/code/i).fill(code);
  await page.getByRole('button', { name: /valider/i }).click();
  await expect(page).toHaveURL(/\/dashboard|\/onboarding/);
});
```

> Le numéro KALGA est normalisé : on strip le `0` initial et on préfixe `225` (Côte d'Ivoire). Ex `0141540178` → `225141540178`. Voir `dashboard/static/app.js` (login flow). Aligner le param de l'endpoint test sur la forme normalisée.

### 3.3 Stratégie C — Mock du verify côté réseau (UI only)

Quand on teste seulement l'UI (pas le backend), intercepter l'appel de vérification et le fulfill :

```ts
test('OTP UI — verify mocké', async ({ page }) => {
  // intercepter AVANT navigation
  await page.route('**/auth/verify-otp', async route => {
    await route.fulfill({
      status: 200,
      json: { token: 'fake.jwt.token', merchant: { id: 10, phone: '225141540178' } },
    });
  });
  await page.route('**/auth/send-otp', async route => {
    await route.fulfill({ status: 200, json: { sent: true } });
  });

  await page.goto('/signup');
  await page.getByLabel('Téléphone').fill('0141540178');
  await page.getByRole('button', { name: /recevoir le code/i }).click();
  await page.getByLabel(/code/i).fill('123456');     // n'importe quel code, c'est mocké
  await page.getByRole('button', { name: /valider/i }).click();
  await expect(page).toHaveURL(/\/dashboard/);
});
```

> `page.route(url, handler)` doit être enregistré AVANT que la requête parte. Patterns glob (`**/auth/verify-otp`) ou regex acceptés. `route.fulfill({ json })` sérialise automatiquement.

### 3.4 Cas d'échec à couvrir

```ts
test('OTP invalide affiche une erreur', async ({ page }) => {
  await page.goto('/signup');
  await page.getByLabel('Téléphone').fill('0141540178');
  await page.getByRole('button', { name: /recevoir le code/i }).click();
  await page.getByLabel(/code/i).fill('999999');
  await page.getByRole('button', { name: /valider/i }).click();
  await expect(page.getByText(/code incorrect|invalide/i)).toBeVisible();
  await expect(page).not.toHaveURL(/\/dashboard/);
});
```

**Recommandation KALGA** : Stratégie A (OTP déterministe en `TEST_MODE`) pour les E2E de bout en bout, + Stratégie C (mock réseau) pour les tests UI purs rapides.

---

## 4. Tester Convex côté backend (convex-test + internalMutation)

> S'applique SI KALGA utilise/migre vers Convex. `convex-test` est un mock in-memory du backend Convex, exécuté dans Vitest. Pas de serveur Convex requis.

### 4.1 Install + config Vitest (edge-runtime obligatoire)

```bash
pnpm add -D convex-test vitest @edge-runtime/vm
```

```ts
// vitest.config.ts (à la racine du projet Convex)
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'edge-runtime',                  // OBLIGATOIRE pour convex-test
    server: { deps: { inline: ['convex-test'] } }, // résolution module correcte
    include: ['convex/**/*.test.ts'],
  },
});
```

> **Gotcha** : `environment: 'edge-runtime'` est requis (convex-test simule le runtime Convex). Sans `@edge-runtime/vm`, Vitest crashe. Le `server.deps.inline` évite les erreurs de résolution ESM.

### 4.2 Test d'une mutation + query

```ts
// convex/products.test.ts
import { convexTest } from 'convex-test';
import { expect, test } from 'vitest';
import { api, internal } from './_generated/api';
import schema from './schema';

// IMPORTANT (Vitest sans bundler) : aide convex-test à trouver les modules
const modules = import.meta.glob('./**/*.*s');

test('createProduct insère et list le retourne', async () => {
  const t = convexTest(schema, modules);

  const id = await t.mutation(api.products.create, {
    name: 'Sac à main',
    price: 15000,
    merchantId: 'm10',
  });

  const list = await t.query(api.products.list, { merchantId: 'm10' });
  expect(list).toHaveLength(1);
  expect(list[0]).toMatchObject({ name: 'Sac à main', price: 15000 });

  // Lecture directe de la DB via t.run (utile pour assertions fines)
  const doc = await t.run(async (ctx) => ctx.db.get(id));
  expect(doc?.name).toBe('Sac à main');
});
```

> Le 2e arg `modules` (`import.meta.glob('./**/*.*s')`) est nécessaire quand on lance Vitest directement (pas via bundler Convex). Sinon convex-test ne trouve pas les fonctions.

### 4.3 Test avec identité (auth)

```ts
import { convexTest } from 'convex-test';
import { expect, test } from 'vitest';
import { api } from './_generated/api';
import schema from './schema';

test('mutation scoped à l\'utilisateur authentifié', async () => {
  const t = convexTest(schema);
  const asMerchant = t.withIdentity({ name: 'Marchand 0178', subject: 'm10' });

  const res = await asMerchant.mutation(api.products.createMine, { name: 'Robe', price: 9000 });
  expect(res).toBeDefined();

  // Vérifier que getUserIdentity() est bien câblé
  const ident = await asMerchant.run((ctx) => ctx.auth.getUserIdentity());
  expect(ident).toMatchObject({ name: 'Marchand 0178' });
});
```

> `withIdentity({...})` génère automatiquement `subject`, `issuer`, `tokenIdentifier` si non fournis. `t.run(ctx => ...)` exécute du code arbitraire dans un contexte (lecture DB, auth, storage).

### 4.4 Tester une `internalMutation` / `internalAction`

Les fonctions internes s'appellent via `internal.*` (pas `api.*`). convex-test permet de les invoquer directement :

```ts
import { internal } from './_generated/api';

test('internalMutation de génération OTP', async () => {
  const t = convexTest(schema);
  // appel direct d'une internalMutation
  const code = await t.mutation(internal.auth.generateOtp, { phone: '225141540178' });
  expect(code).toMatch(/^\d{6}$/);

  // vérifier qu'elle a persisté l'OTP
  const stored = await t.run(async (ctx) =>
    ctx.db.query('otps').filter(q => q.eq(q.field('phone'), '225141540178')).first()
  );
  expect(stored?.code).toBe(code);
});
```

### 4.5 Tester une action avec `fetch` mocké (ex envoi OTP via bridge HTTP)

```ts
import { vi, test, expect } from 'vitest';
import { convexTest } from 'convex-test';
import { api } from './_generated/api';
import schema from './schema';

test('sendOtp appelle le bridge WhatsApp', async () => {
  const t = convexTest(schema);
  vi.stubGlobal('fetch', vi.fn(async () => ({
    ok: true,
    json: async () => ({ sent: true }),
    text: async () => 'ok',
  }) as unknown as Response));

  await t.action(api.auth.sendOtp, { phone: '225141540178' });

  expect(fetch).toHaveBeenCalledWith(
    expect.stringContaining('/send'),
    expect.objectContaining({ method: 'POST' }),
  );
  vi.unstubAllGlobals();          // OBLIGATOIRE — sinon fuit sur les autres tests
});
```

### 4.6 Tester des fonctions planifiées (scheduler / followups)

KALGA a un `followup_service` (scheduler). En Convex, on teste avec fake timers :

```ts
import { vi, describe, test, expect, beforeEach, afterEach } from 'vitest';
import { convexTest } from 'convex-test';
import { api, internal } from './_generated/api';
import schema from './schema';

describe('followups', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  test('le followup planifié s\'exécute', async () => {
    const t = convexTest(schema);
    await t.mutation(api.chat.scheduleFollowup, { conversationId: 'c1', delayMs: 60000 });

    // Avance les timers ET attend la complétion de toutes les fonctions planifiées
    await t.finishAllScheduledFunctions(vi.runAllTimers);

    const conv = await t.query(internal.chat.get, { id: 'c1' });
    expect(conv?.followupSent).toBe(true);
  });
});
```

> `finishAllScheduledFunctions(vi.runAllTimers)` boucle jusqu'à ce que TOUTES les fonctions planifiées (y compris celles re-planifiées récursivement) finissent. Toujours `vi.useFakeTimers()` avant. Nettoyer avec `vi.useRealTimers()` en `afterEach`.

### 4.7 Storage (images produits)

```ts
test('store et getUrl d\'une image', async () => {
  const t = convexTest(schema);
  const storageId = await t.run(async (ctx) =>
    ctx.storage.store(new Blob(['fake-bytes'], { type: 'image/jpeg' }))
  );
  const url = await t.run(async (ctx) => ctx.storage.getUrl(storageId));
  expect(url).toContain(storageId);
});
```

---

## 5. Vitest — tests unitaires (frontend + utils)

### 5.1 Install + config (app Vite)

```bash
pnpm add -D vitest @vitest/ui jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom
```

```ts
// vitest.config.ts (app frontend Vite/React)
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',                 // DOM pour composants React
    globals: true,                        // expect/test/describe sans import
    setupFiles: ['./tests/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: { provider: 'v8', reporter: ['text', 'html'] },
  },
});
```

```ts
// tests/setup.ts
import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
afterEach(() => cleanup());
```

### 5.2 Test composant

```tsx
// src/components/ProductCard.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';
import { ProductCard } from './ProductCard';

test('affiche nom + prix formaté et déclenche onAdd', async () => {
  const onAdd = vi.fn();
  render(<ProductCard product={{ id: 'p1', name: 'Sac', price: 15000 }} onAdd={onAdd} />);

  expect(screen.getByText('Sac')).toBeInTheDocument();
  expect(screen.getByText(/15[\s ]?000/)).toBeInTheDocument();   // 15 000 XOF

  await userEvent.click(screen.getByRole('button', { name: /ajouter/i }));
  expect(onAdd).toHaveBeenCalledWith('p1');
});
```

### 5.3 Test fonction pure (ex normalisation téléphone — logique KALGA)

```ts
// src/lib/phone.test.ts
import { expect, test, describe } from 'vitest';
import { normalizePhone } from './phone';

describe('normalizePhone (Côte d\'Ivoire)', () => {
  test('strip 0 initial et préfixe 225', () => {
    expect(normalizePhone('0141540178')).toBe('225141540178');
  });
  test('laisse intact si déjà préfixé', () => {
    expect(normalizePhone('225141540178')).toBe('225141540178');
  });
});
```

### 5.4 Backend FastAPI — pytest (pour mémoire, pas Vitest)

Les détecteurs AI, repos et calculs côté `kalga-api` se testent en **pytest** (Python), pas Vitest :

```bash
cd kalga-api && pip install pytest pytest-asyncio httpx
```

```python
# kalga-api/tests/test_detectors.py
import pytest
from app.services.ai.detectors import detect_product_code

def test_detect_product_code():
    assert detect_product_code("je veux le P001") == "P001"
    assert detect_product_code("bonjour") is None
```

```python
# Test endpoint via httpx + ASGITransport (pas de serveur à lancer)
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/")
        assert r.status_code == 200
```

---

## 6. Specs d'exemple demandées

### 6.1 Signup OTP (E2E complet)

```ts
// tests/e2e/signup-otp.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Signup OTP', () => {
  test('happy path → dashboard', async ({ page }) => {
    const phone = `01${Date.now().toString().slice(-8)}`;
    await page.goto('/signup');
    await page.getByLabel('Téléphone').fill(phone);
    await page.getByRole('button', { name: /recevoir le code/i }).click();
    await expect(page.getByText(/code de vérification/i)).toBeVisible();
    await page.getByLabel(/code/i).fill('000000');          // TEST_MODE déterministe
    await page.getByRole('button', { name: /valider/i }).click();
    await expect(page).toHaveURL(/\/dashboard|\/onboarding/);
  });

  test('code invalide → erreur, pas de redirection', async ({ page }) => {
    await page.goto('/signup');
    await page.getByLabel('Téléphone').fill('0141540178');
    await page.getByRole('button', { name: /recevoir le code/i }).click();
    await page.getByLabel(/code/i).fill('111111');
    await page.getByRole('button', { name: /valider/i }).click();
    await expect(page.getByText(/incorrect|invalide/i)).toBeVisible();
    await expect(page).not.toHaveURL(/\/dashboard/);
  });
});
```

### 6.2 Dashboard charge les produits live

```ts
// tests/e2e/dashboard-products.spec.ts
import { test, expect } from '@playwright/test';

// utilise le storageState authentifié (cf. 2.4) → déjà loggé
test.use({ storageState: 'playwright/.auth/user.json' });

test('le dashboard liste les produits du marchand', async ({ page }) => {
  await page.goto('/dashboard/produits');

  // attendre la réponse réseau de l'API produits
  const resp = await page.waitForResponse(r => r.url().includes('/api/products') && r.ok());
  const products = await resp.json();

  // chaque produit rendu en carte
  const cards = page.getByTestId('product-card');
  await expect(cards).toHaveCount(products.length);
  await expect(cards.first()).toBeVisible();

  // au moins le nom du 1er produit présent
  if (products.length > 0) {
    await expect(page.getByText(products[0].name)).toBeVisible();
  }
});

test('état vide si aucun produit', async ({ page }) => {
  await page.route('**/api/products**', r => r.fulfill({ json: [] }));
  await page.goto('/dashboard/produits');
  await expect(page.getByText(/aucun produit|commencez par/i)).toBeVisible();
});
```

### 6.3 Storefront public `/{slug}` rend le catalogue

```ts
// tests/e2e/storefront.spec.ts
import { test, expect } from '@playwright/test';

const SLUG = 'marchand-0178';   // slug public d'un marchand de test

test('la boutique publique rend le catalogue (SSR)', async ({ page }) => {
  await page.goto(`/${SLUG}`);

  // header boutique
  await expect(page.getByRole('heading', { name: /marchand 0178/i })).toBeVisible();

  // au moins une carte produit
  const cards = page.getByTestId('product-card');
  await expect(cards.first()).toBeVisible();

  // prix affiché en XOF
  await expect(page.getByText(/XOF|FCFA/i).first()).toBeVisible();
});

test('slug inexistant → 404', async ({ page }) => {
  const res = await page.goto('/slug-qui-nexiste-pas-xyz');
  expect(res?.status()).toBe(404);
  await expect(page.getByText(/introuvable|404/i)).toBeVisible();
});

test('contenu présent dans le HTML SSR (JS désactivé)', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto(`http://localhost:3000/${SLUG}`);
  await expect(page.getByTestId('product-card').first()).toBeVisible();  // SSR, pas hydratation
  await ctx.close();
});
```

---

## 7. Intégration en CI (GitHub Actions)

### 7.1 Workflow unique — unit + convex-test + E2E

```yaml
# .github/workflows/test.yml
name: tests
on:
  push: { branches: [develop, main] }
  pull_request: {}

jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: pnpm }
      - run: pnpm install --frozen-lockfile
      - run: pnpm test:unit              # Vitest (FE) + convex-test
        env:
          CI: true

  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: pnpm }
      - run: pnpm install --frozen-lockfile

      # IMPORTANT : installer le binaire navigateur + deps système Linux
      - run: pnpm exec playwright install --with-deps chromium

      # webServer dans playwright.config démarre `pnpm dev` tout seul.
      - run: pnpm test:e2e
        env:
          CI: true
          KALGA_TEST_MODE: '1'           # active l'OTP déterministe (section 3.1)

      - uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7
```

### 7.2 Backend Python (job séparé pytest)

```yaml
  api-tests:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: kalga-api } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt pytest pytest-asyncio httpx
      - run: pytest -q
```

### 7.3 Points de vigilance CI

- **`--with-deps`** est obligatoire sur Linux CI (installe libs système : `libnss3`, `libgbm1`, etc.). Sans ça : `Host system is missing dependencies`.
- **`workers: 1`** + **`retries: 2`** en CI (config section 1.2) réduit la flakiness des E2E.
- **`forbidOnly: !!process.env.CI`** fait échouer le build si un `test.only` traîne.
- **OTP** : exporter `KALGA_TEST_MODE=1` côté backend pour activer l'OTP déterministe (section 3.1), sinon les E2E auth échouent (pas de vrai WhatsApp en CI).
- **Ports** : si `webServer` lance frontend + FastAPI, s'assurer que les deux ports (3000 + 8001) sont libres et que l'`url` de health-check répond (FastAPI `/docs` ou `/health`).
- **Trace sur échec** : `trace: 'on-first-retry'` produit un `trace.zip` rejouable (`pnpm exec playwright show-trace trace.zip`).

---

## 8. Pièges récapitulatifs (à ne pas oublier)

| Piège | Conséquence | Fix |
|-------|-------------|-----|
| Oublier `playwright install` | `Executable doesn't exist` | `pnpm exec playwright install --with-deps chromium` |
| `waitForTimeout(N)` arbitraire | flaky | utiliser `expect(...).toBeVisible()` auto-wait |
| `page.route` enregistré APRÈS la requête | mock ignoré | enregistrer AVANT `page.goto` |
| convex-test sans `environment: 'edge-runtime'` | crash Vitest | config section 4.1 |
| convex-test lancé via Vitest sans `import.meta.glob` modules | fonctions introuvables | passer `modules` en 2e arg de `convexTest` |
| `vi.stubGlobal('fetch', ...)` sans `unstubAllGlobals` | fuite entre tests | `vi.unstubAllGlobals()` en fin de test |
| Scheduler testé sans fake timers | timeout / non-déterministe | `vi.useFakeTimers()` + `finishAllScheduledFunctions(vi.runAllTimers)` |
| port `webServer.url` ≠ port réel `pnpm dev` | webServer timeout | aligner port (3000 Start / 5173 Vite) |
| OTP réel en CI | impossible (pas de WhatsApp) | `KALGA_TEST_MODE` + OTP déterministe |
| Numéro non normalisé dans endpoint test OTP | code introuvable | normaliser `0XXX` → `225XXX` |

---

## 9. Références

- Playwright : `/microsoft/playwright` — config webServer, `page.route`/`fulfill`, web-first assertions.
- convex-test : `/get-convex/convex-test` — `convexTest`, `withIdentity`, `finishAllScheduledFunctions`, `vi.stubGlobal` fetch, storage.
- Vitest 3.x, `@edge-runtime/vm` requis pour convex-test.
- KALGA : normalisation téléphone (`0XXX` → `225XXX`) dans `dashboard/static/app.js` ; scheduler `kalga-api/app/services/followup_service.py` ; routers `/api/products`, `/boutique`, `/auth`.
