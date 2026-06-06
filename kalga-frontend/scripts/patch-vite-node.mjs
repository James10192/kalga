/**
 * Patch @nuxt/vite-builder pour contourner un bug Node.js Windows.
 *
 * ============================================================================
 * DETTE TRACÉE — À RETIRER QUAND :
 * - Node.js fixe la résolution des subpath imports (`package.json#imports`)
 *   pour les chemins Windows contenant des caractères Unicode + espaces ; OU
 * - Le projet est déplacé vers un chemin ASCII pur sans espaces (ex:
 *   `C:\dev\KALGA`), auquel cas ce script devient inutile.
 *
 * Le bug : dans `@nuxt/vite-builder/dist/vite-node-{entry,runner,index}.mjs`,
 * des imports en `#vite-node`, `#vite-node-runner`, `#vite-node-entry` sont
 * résolus par Node via `package.json#imports`. Sur Windows + Node 22-24 +
 * chemin contenant `à` (ou autre caractère non-ASCII) + espaces, Node renvoie
 * `Package import specifier "#vite-node" is not defined`.
 *
 * Fix : remplacer ces imports symboliques par leurs chemins relatifs réels.
 * Les 3 fichiers cibles existent dans le même `dist/`, donc les chemins
 * relatifs sont triviaux.
 *
 * Ce script est lancé en `postinstall` (cf. package.json#scripts.postinstall)
 * pour que les patches soient ré-appliqués automatiquement après chaque
 * `pnpm install`. Sans ça, pnpm ré-écrase node_modules et le patch disparaît.
 *
 * Référence : https://github.com/nodejs/node (subpath imports + Unicode paths)
 * ============================================================================
 */

import { readdir, readFile, writeFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { join, resolve } from 'node:path'

/**
 * Mapping des spécificateurs `#xxx` vers leur chemin relatif réel.
 * IMPORTANT : ordre du plus long au plus court pour éviter qu'un sed
 * remplace partiellement (ex: `#vite-node-runner` matcherait `#vite-node`).
 */
const REPLACEMENTS = [
  ['"#vite-node-runner"', '"./vite-node-runner.mjs"'],
  ['"#vite-node-entry"', '"./vite-node-entry.mjs"'],
  ['"#vite-node"', '"./vite-node.mjs"'],
]

const ROOT = resolve(import.meta.dirname, '..')
const PNPM_DIR = join(ROOT, 'node_modules', '.pnpm')
const PACKAGE_PREFIX = '@nuxt+vite-builder@'

async function findViteBuilderDists() {
  if (!existsSync(PNPM_DIR)) {
    console.log('[patch-vite-node] node_modules/.pnpm not found, skipping')
    return []
  }
  const entries = await readdir(PNPM_DIR)
  const matches = entries.filter((e) => e.startsWith(PACKAGE_PREFIX))
  return matches.map((dir) =>
    join(PNPM_DIR, dir, 'node_modules', '@nuxt', 'vite-builder', 'dist'),
  )
}

async function patchFile(filePath) {
  const original = await readFile(filePath, 'utf8')
  let patched = original
  for (const [from, to] of REPLACEMENTS) {
    patched = patched.replaceAll(from, to)
  }
  if (patched === original) return false
  await writeFile(filePath, patched, 'utf8')
  return true
}

async function patchDist(distDir) {
  if (!existsSync(distDir)) return { distDir, patched: 0 }
  const files = await readdir(distDir)
  const mjsFiles = files.filter((f) => f.endsWith('.mjs'))
  let patched = 0
  for (const file of mjsFiles) {
    const filePath = join(distDir, file)
    if (await patchFile(filePath)) {
      patched++
    }
  }
  return { distDir, patched }
}

async function main() {
  const dists = await findViteBuilderDists()
  if (dists.length === 0) {
    console.log('[patch-vite-node] no @nuxt/vite-builder dist found, nothing to patch')
    return
  }
  let totalPatched = 0
  for (const dist of dists) {
    const { patched } = await patchDist(dist)
    totalPatched += patched
  }
  if (totalPatched > 0) {
    console.log(
      `[patch-vite-node] patched ${totalPatched} file(s) across ${dists.length} @nuxt/vite-builder dist(s)`,
    )
  } else {
    console.log('[patch-vite-node] already patched (or nothing to patch)')
  }
}

main().catch((err) => {
  console.error('[patch-vite-node] failed:', err)
  process.exit(1)
})
