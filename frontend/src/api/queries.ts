/**
 * React Query hooks, one per endpoint.
 *
 * The polling rule lives here rather than in a screen: a run is polled while
 * it is running and left alone once it reaches a terminal state. Solving takes
 * minutes, so the alternative — holding a request open — is not available
 * (docs/architecture.md, "The run lifecycle").
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiGet, apiSend } from '@/api/client'
import type {
  Availability,
  AvailabilityState,
  Decomposition,
  InstanceData,
  RecommendedCandidate,
  Run,
  RunState,
  RunSummary,
} from '@/types/domain'
import type { CurrentUser } from '@/types/domain'

/** States in which nothing further will happen without a new request. */
const TERMINAL: readonly RunState[] = ['COMPLETED', 'INFEASIBLE', 'DIAGNOSED', 'FAILED']

export function isTerminal(state: RunState): boolean {
  return TERMINAL.includes(state)
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ['me'],
    queryFn: () => apiGet<CurrentUser>('/auth/me'),
    // One failure means the token is absent, expired or forged; retrying would
    // just repeat a 401. The shell signs the user out instead.
    retry: false,
    staleTime: Infinity,
  })
}

export function useInstance() {
  return useQuery({
    queryKey: ['instance'],
    queryFn: () => apiGet<InstanceData>('/instance'),
    // The instance does not change while the application runs; re-fetching it
    // on every screen would re-send 218 sessions for nothing.
    staleTime: Infinity,
  })
}

export function useRuns() {
  return useQuery({ queryKey: ['runs'], queryFn: () => apiGet<RunSummary[]>('/runs') })
}

export function useRun(runId: string | null) {
  return useQuery({
    queryKey: ['run', runId],
    queryFn: () => apiGet<Run>(`/runs/${runId as string}`),
    enabled: runId !== null,
    refetchInterval: (query) => {
      const run = query.state.data
      // 1 s while the solve is in flight; stop entirely once it settles.
      return run && isTerminal(run.state) ? false : 1000
    },
  })
}

export function useCreateRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { seed?: number; deterministicBudget?: number }) =>
      apiSend<{ runId: string }>('POST', '/runs', body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['runs'] })
    },
  })
}

export function useComparison(runId: string | null, a: string | null, b: string | null) {
  return useQuery({
    queryKey: ['comparison', runId, a, b],
    queryFn: () =>
      apiGet<Decomposition>(
        `/runs/${runId as string}/comparison?a=${encodeURIComponent(a as string)}&b=${encodeURIComponent(b as string)}`,
      ),
    enabled: runId !== null && a !== null && b !== null && a !== b,
  })
}

// No `useDominance` hook, deliberately. `GET /runs/{id}/dominance` exists and is
// tested, but C-14 is open and Phase 4 ships no dominance signal, so a hook
// here would be a code path nothing exercises. Add it with the screen that
// uses it — see C-14 in docs/open-questions.md.

export function useAvailability(teacherId: string | null) {
  return useQuery({
    queryKey: ['availability', teacherId],
    queryFn: () => apiGet<Availability[]>(`/teachers/${teacherId as string}/availability`),
    enabled: teacherId !== null,
  })
}

export function useDeclareAvailability(teacherId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      semester: number
      cells: { slot: number; state: AvailabilityState }[]
    }) =>
      apiSend<Availability[]>('PUT', `/teachers/${teacherId as string}/availability`, body),
    onSuccess: (rows) => {
      // Seed the cache from the response rather than re-fetching: the PUT
      // already returns the teacher's effective declaration, so a round trip
      // would only add a window in which the grid shows stale cells.
      queryClient.setQueryData(['availability', teacherId], rows)
    },
  })
}

export function useRecommendation(runId: string | null) {
  return useQuery({
    queryKey: ['recommendation', runId],
    queryFn: () =>
      apiGet<RecommendedCandidate | null>(`/runs/${runId as string}/recommendation`),
    enabled: runId !== null,
  })
}
