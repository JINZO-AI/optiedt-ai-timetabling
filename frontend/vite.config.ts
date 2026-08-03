import { fileURLToPath, URL } from 'node:url'

import react from '@vitejs/plugin-react'
// `vitest/config` rather than `vite`: it is the same defineConfig plus the
// `test` key below, so the alias and the tests cannot drift apart.
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  resolve: {
    // tsconfig.json declares the same `@/*` -> `src/*` alias, but Vite does
    // NOT read tsconfig paths — it needs its own. Without this the project
    // type-checks cleanly and fails to boot, which is the worst combination:
    // `npm run typecheck` is green and every import resolves to nothing.
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      // The run launch returns immediately with a run id; the client then polls
      // GET /runs/{id}. No request is held open for the duration of a solve.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
