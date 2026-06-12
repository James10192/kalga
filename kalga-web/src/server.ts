import {
  createStartHandler,
  defaultStreamHandler,
} from '@tanstack/react-start/server'
import type { Register } from '@tanstack/react-router'
import type { RequestHandler } from '@tanstack/react-start/server'

// Explicit server entry. Like src/client.tsx, this exists because the plugin's
// default `virtual:tanstack-start-server-entry` fails to resolve through the
// pnpm symlinked store (TanStack/router#6588), which makes every document route
// 404 "Cannot GET" in `vite dev`. A local copy fixes the dev SSR mount.
const fetch = createStartHandler(defaultStreamHandler)

export type ServerEntry = { fetch: RequestHandler<Register> }

export function createServerEntry(entry: ServerEntry): ServerEntry {
  return {
    async fetch(...args) {
      return await entry.fetch(...args)
    },
  }
}

export default createServerEntry({ fetch })
