import { QueryClient } from '@tanstack/react-query'

// Shared instance so non-component code (axios interceptors, logout) can
// clear the cache — cached data must not leak across sessions.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})
