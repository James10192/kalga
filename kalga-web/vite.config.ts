import path from 'node:path'
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import { nitro } from 'nitro/vite'
import viteReact from '@vitejs/plugin-react'

export default defineConfig({
  server: {
    port: 3000,
  },
  ssr: {
    noExternal: ['@convex-dev/better-auth'],
  },
  resolve: {
    tsconfigPaths: true,
    // Single React copy. @gsap/react (useGSAP) otherwise resolves a 2nd React
    // through pnpm symlinks -> "Invalid hook call / more than one copy of React"
    // -> blank page after hydration.
    dedupe: ['react', 'react-dom'],
    alias: {
      '@': path.resolve(__dirname, './src'),
      '~': path.resolve(__dirname, './src'),
    },
  },
  plugins: [
    tailwindcss(),
    tanstackStart(),
    nitro(),
    viteReact(),
  ],
})
