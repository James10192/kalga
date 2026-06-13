import fs from "node:fs"
import path from "node:path"

/**
 * Detection d'un etat d'authentification reutilisable pour les E2E gated.
 *
 * Les routes `/app/*` sont protegees (plan 010 §C) : `beforeLoad` redirige vers
 * `/login` sans session. Pour exercer l'ecran « Connecter WhatsApp » et le
 * dashboard responsive en E2E, il faut une session reelle, qui n'existe qu'avec
 * un backend Convex + Better Auth lance et une porte de test.
 *
 * Convention : si un `storageState` authentifie est fourni, les specs gated le
 * consomment et tournent ; sinon elles `test.skip` proprement (jamais rouge).
 *
 * Fournir l'etat de deux facons :
 *  - variable d'env `KALGA_E2E_STORAGE_STATE` = chemin absolu d'un fichier
 *    storageState Playwright ;
 *  - OU le fichier par defaut `playwright/.auth/user.json` (genere par un
 *    `auth.setup.ts` une fois la porte TEST_MODE en place).
 */

export const DEFAULT_AUTH_FILE = path.join(
  process.cwd(),
  "playwright",
  ".auth",
  "user.json",
)

/** Chemin du storageState authentifie, ou `null` si indisponible. */
export function resolveAuthStorageState(): string | null {
  const fromEnv = process.env.KALGA_E2E_STORAGE_STATE
  if (fromEnv && fs.existsSync(fromEnv)) return fromEnv
  if (fs.existsSync(DEFAULT_AUTH_FILE)) return DEFAULT_AUTH_FILE
  return null
}

/** Vrai si une session authentifiee est disponible pour les specs gated. */
export function hasAuthSession(): boolean {
  return resolveAuthStorageState() !== null
}
