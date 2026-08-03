import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import { App } from '@/App'
import '@/styles.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // A failed read should surface, not be retried into a long silence: the
      // API is same-origin behind the Vite proxy, so a failure here is a real
      // fault rather than a flaky network.
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
})

const container = document.getElementById('root')
if (!container) throw new Error('#root is missing from index.html')

createRoot(container).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
