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
  // Force a SINGLE React instance through Vite's dev pre-bundling. Without this,
  // react / react-dom / @tanstack/react-router (Await -> React.use) and the
  // better-auth provider could resolve React across two optimize boundaries ->
  // "Invalid hook call / more than one copy of React" (dispatcher null in
  // useAwaited) once expectAuth:true activates the <Await> token path.
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-dom/client',
      'react/jsx-runtime',
      'react/jsx-dev-runtime',
      // Pre-bundle React-rendering deps in the SAME pass so they share the one
      // deduped React. @tanstack/react-router (Await -> React.use) served raw
      // otherwise resolves a 2nd React on a mid-session re-optimize. gsap is
      // listed so discovering it never triggers that disruptive re-optimize.
      '@tanstack/react-router',
      'gsap',
      'qrcode',
    ],
  },
  resolve: {
    tsconfigPaths: true,
    // Single React copy. A 2nd React (via pnpm symlinks / optimize boundary)
    // otherwise triggers "Invalid hook call / more than one copy of React"
    // -> blank page after hydration. Include the jsx runtimes too (React 19
    // `use` reads the shared dispatcher, which must come from one instance).
    dedupe: ['react', 'react-dom', 'react/jsx-runtime', 'react/jsx-dev-runtime'],
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
