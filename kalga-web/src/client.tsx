/// <reference types="vite/client" />
import { StrictMode, startTransition } from 'react'
import { hydrateRoot } from 'react-dom/client'
import { StartClient } from '@tanstack/react-start/client'

// Explicit client entry. In pnpm setups the plugin's default
// `virtual:tanstack-start-client-entry` fails to resolve through the symlinked
// store (TanStack/router#6588), which makes every document route 404
// "Cannot GET" in `vite dev`. Providing this local entry fixes it.
startTransition(() => {
  hydrateRoot(
    document,
    <StrictMode>
      <StartClient />
    </StrictMode>,
  )
})
