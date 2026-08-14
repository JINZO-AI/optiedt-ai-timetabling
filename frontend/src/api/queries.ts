/**
 * React Query hooks, one per endpoint.
 *
 * The polling rule lives here rather than in a screen: a run is polled while
 * it is running and left alone once it reaches a terminal state. Solving takes
 * minutes, so the alternative — holding a request open — is not available
 * (docs/architecture.md, "The run lifecycle").
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiGet, apiSend, apiUpload } from '@/api/client'
import type {
  Account,
  AssistantAnswer,
  Availability,
  AvailabilityState,
  CalendarData,
  DatasetImportResult,
  DatasetSummary,
  Decomposition,
  DominanceVerdict,
  ExamRun,
  Holiday,
  InstanceData,
  RecommendedCandidate,
  Run,
  RunState,
  RunSummary,
  ShortenedDay,
  StudentTimetable,
  UserRole,
} from '@/types/domain'
import type { CurrentUser, PublishedTimetable } from '@/types/domain'

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

/**
 * Accept a recommendation — FR-23.
 *
 * ⚠️ This launches a **new run**, exactly like `useCreateRun`, and returns a new
 * run id. It is not an edit and there is no endpoint that edits a timetable
 * (invariant 3). The caller navigates to the new run and watches it the same
 * way it watches any other.
 *
 * The three action shapes are the closed catalogue (ADR-007). A fourth is a
 * type error here, which is the point of the union.
 */
export function useRegenerate(runId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (variables: { candidateId: string; action: RegenerateRequest }) =>
      apiSend<{ runId: string }>(
        'POST',
        `/runs/${runId as string}/candidates/${encodeURIComponent(variables.candidateId)}/regenerate`,
        variables.action,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['runs'] })
    },
  })
}

/**
 * The language service — FR-22, FR-24, FR-25.
 *
 * ⚠️ **These never fail because the service is off.** The API answers 200 with
 * the computed form and `generated: false`; off is the default configuration,
 * not an error. A hook that treated it as one would put an error state on a
 * screen that is working exactly as specified.
 */
export function useExplanation(runId: string | null, candidateId: string | null) {
  return useQuery({
    queryKey: ['assistant', 'explanation', runId, candidateId],
    queryFn: () =>
      apiGet<AssistantAnswer>(
        `/assistant/runs/${runId as string}/candidates/${encodeURIComponent(candidateId as string)}/explanation`,
      ),
    enabled: runId !== null && candidateId !== null,
  })
}

export function useRunReport(runId: string | null) {
  return useQuery({
    queryKey: ['assistant', 'report', runId],
    queryFn: () => apiGet<AssistantAnswer>(`/assistant/runs/${runId as string}/report`),
    enabled: runId !== null,
  })
}

/** FR-24. A mutation rather than a query: asking is an act, and two identical
 * questions are two askings rather than one cached answer. */
export function useAskAssistant(runId: string | null) {
  return useMutation({
    mutationFn: (question: string) =>
      apiSend<AssistantAnswer>('POST', `/assistant/runs/${runId as string}/question`, {
        question,
      }),
  })
}

/**
 * A comparative question about the TWO candidates on screen — "why is this
 * one ranked first", "what trade-offs does it make". `/question` cannot
 * answer these: it is bounded to one run's own figures by design (FR-24) and
 * carries no decomposition. This calls the comparison-grounded route
 * instead, which is handed the same `Decomposition` the ledger itself
 * renders, so the answer is not a guess about "this candidate" in the
 * abstract — it is grounded in the exact two candidates being compared.
 */
export function useAskAboutComparison(runId: string | null) {
  return useMutation({
    mutationFn: ({ candidateId, otherId }: { candidateId: string; otherId: string }) =>
      apiGet<AssistantAnswer>(
        `/assistant/runs/${runId as string}/candidates/${encodeURIComponent(candidateId)}/compare/${encodeURIComponent(otherId)}`,
      ),
  })
}

/** The wire form of the three catalogue actions. Closed — see ADR-007. */
export type RegenerateRequest =
  | { kind: 'weight_delta'; criterion: string; newWeight: number }
  | { kind: 'lock_session'; session: string }
  | { kind: 'exclude_slot'; session: string; slot: number }
  | { kind: 'exclude_slot'; session: string; room: string }

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

/**
 * FR-17 — which candidates another improves on across the board.
 *
 * Added in Phase 6 M1, once **C-14** was resolved. Until then there was no hook
 * here on purpose: the endpoint existed and was tested, but no screen showed a
 * dominance signal, so a hook would have been a code path nothing exercised.
 *
 * ⚠️ The verdicts are portfolio-wide, and that is the point of the resolution.
 * The signal the specification originally asked for — "a dominated **top**
 * candidate" — is arithmetically unreachable, so what is displayed is a
 * dominated candidate *anywhere* in the run.
 */
export function useDominance(runId: string | null) {
  return useQuery({
    queryKey: ['dominance', runId],
    queryFn: () => apiGet<DominanceVerdict[]>(`/runs/${runId as string}/dominance`),
    enabled: runId !== null,
  })
}

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

export function usePublications() {
  return useQuery({
    queryKey: ['publications'],
    queryFn: () => apiGet<PublishedTimetable[]>('/publications'),
    // Only the person in charge may read these; a 403 for anyone else is an
    // answer, not a transient failure.
    retry: false,
  })
}

export function usePublishCandidate(runId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (candidateId: string) =>
      apiSend<PublishedTimetable>(
        'POST',
        `/runs/${runId as string}/candidates/${candidateId}/publish`,
        {},
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['publications'] })
    },
  })
}

/**
 * The administrator's calendar — FR-9.
 *
 * ⚠️ Administrator only; a 403 for anyone else is an answer rather than a
 * transient failure, so it is not retried — the same judgement
 * `usePublications` makes.
 */
export function useCalendar(enabled: boolean) {
  return useQuery({
    queryKey: ['calendar'],
    queryFn: () => apiGet<CalendarData>('/calendar'),
    enabled,
    retry: false,
  })
}

/**
 * State the calendar — one statement about a year, sent whole.
 *
 * ⚠️ On success the INSTANCE cache is invalidated too, and that is not
 * housekeeping: `GET /instance` serves the effective calendar, so a closure
 * that did not invalidate it would leave every other screen — the availability
 * grid, every timetable view — drawing a half-day the department has closed.
 * `useInstance` holds it with `staleTime: Infinity`, so nothing else would ever
 * refetch it.
 */
export function useSaveCalendar() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      slots: { slot: number; isOpen: boolean }[]
      holidays?: Holiday[] | null
      shortenedDay?: ShortenedDay | null
    }) => apiSend<CalendarData>('PUT', '/calendar', body),
    onSuccess: (calendar) => {
      queryClient.setQueryData(['calendar'], calendar)
      void queryClient.invalidateQueries({ queryKey: ['instance'] })
    },
  })
}

/** Withdraw every calendar edit; the loaded CSVs govern again. */
export function useResetCalendar() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => apiSend<CalendarData>('DELETE', '/calendar'),
    onSuccess: (calendar) => {
      queryClient.setQueryData(['calendar'], calendar)
      void queryClient.invalidateQueries({ queryKey: ['instance'] })
    },
  })
}

/** Accounts — FR-11, the administrator's other Table 2 surface. */
export function useAccounts(enabled: boolean) {
  return useQuery({
    queryKey: ['accounts'],
    queryFn: () => apiGet<Account[]>('/accounts'),
    enabled,
    retry: false,
  })
}

export function useCreateAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      username: string
      password: string
      role: UserRole
      teacher?: string | null
      group?: string | null
    }) => apiSend<Account>('POST', '/accounts', body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
  })
}

export function useDeleteAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (username: string) =>
      apiSend<void>('DELETE', `/accounts/${encodeURIComponent(username)}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
  })
}

/**
 * The student's own timetable — SRS Table 2.
 *
 * ⚠️ No group is passed, deliberately: the account decides which group this
 * is, exactly as a teacher's grid is decided by the token. A parameter here
 * would be a parameter the API had to refuse.
 */
export function useMyTimetable(enabled: boolean) {
  return useQuery({
    queryKey: ['me', 'timetable'],
    queryFn: () => apiGet<StudentTimetable>('/me/timetable'),
    enabled,
    retry: false,
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

/** The department data in force — FR-1, person in charge only. */
export function useDataset(enabled: boolean) {
  return useQuery({
    queryKey: ['dataset'],
    queryFn: () => apiGet<DatasetSummary>('/dataset'),
    enabled,
    retry: false,
  })
}

/**
 * Supply a department dataset — FR-1.
 *
 * ⚠️ **A refused import is a SUCCESS at this layer.** The endpoint answers 200
 * with `accepted: false` and the report, so `onError` is for a network or
 * authorisation failure only; treating a rejected line as a thrown error would
 * lose the report that is the requirement's whole output.
 *
 * ⚠️ On success the INSTANCE and CALENDAR caches are invalidated, for the reason
 * `useSaveCalendar` gives: `GET /instance` serves whatever dataset is in force
 * and `useInstance` holds it with `staleTime: Infinity`, so an import that did
 * not invalidate it would leave every other screen drawing the previous
 * department's week.
 */
export function useImportDataset() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (files: File[]) => apiUpload<DatasetImportResult>('/dataset', files),
    onSuccess: (result) => {
      queryClient.setQueryData(['dataset'], result.dataset)
      if (result.accepted) {
        void queryClient.invalidateQueries({ queryKey: ['instance'] })
        void queryClient.invalidateQueries({ queryKey: ['calendar'] })
      }
    },
  })
}

/** Withdraw the imported dataset; the reference files govern again — FR-1. */
export function useWithdrawDataset() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => apiSend<DatasetImportResult>('DELETE', '/dataset'),
    onSuccess: (result) => {
      queryClient.setQueryData(['dataset'], result.dataset)
      if (result.accepted) {
        void queryClient.invalidateQueries({ queryKey: ['instance'] })
        void queryClient.invalidateQueries({ queryKey: ['calendar'] })
      }
    },
  })
}

/** FR-20 — the examination session. Same 202-and-poll shape as `useCreateRun`. */
export function useExamRuns() {
  return useQuery({
    queryKey: ['examRuns'],
    queryFn: () => apiGet<ExamRun[]>('/examinations'),
  })
}

export function useExamRun(runId: string | null) {
  return useQuery({
    queryKey: ['examRun', runId],
    queryFn: () => apiGet<ExamRun>(`/examinations/${runId as string}`),
    enabled: runId !== null,
    refetchInterval: (query) => {
      const run = query.state.data
      return run && isTerminal(run.state) ? false : 1000
    },
  })
}

export function useGenerateExamSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { seed?: number; deterministicBudget?: number }) => {
      const params = new URLSearchParams()
      if (body.seed !== undefined) params.set('seed', String(body.seed))
      if (body.deterministicBudget !== undefined) {
        params.set('deterministicBudget', String(body.deterministicBudget))
      }
      return apiSend<ExamRun>('POST', `/examinations?${params.toString()}`, {})
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['examRuns'] })
    },
  })
}
