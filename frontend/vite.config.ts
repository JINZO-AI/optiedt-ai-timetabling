import { fileURLToPath, URL } from 'node:url'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

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
})
