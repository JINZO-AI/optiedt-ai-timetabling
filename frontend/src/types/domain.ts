/**
 * Types shared with the API.
 *
 * Kept in step with backend/src/optiedt/domain/ and the Pydantic schemas in
 * optiedt/api/. When the API stabilises these should be generated from the
 * OpenAPI document rather than maintained by hand.
 *
 * See docs/domain-model.md.
 */

/** Lecture (whole promotion) · tutorial (one group) · lab (one subgroup). */
export type SessionType = 'CM' | 'TD' | 'TP'

export type RoomType =
  | 'LECTURE_THEATRE'
  | 'CLASSROOM'
  | 'COMPUTER_LABORATORY'
  | 'SCIENCE_LABORATORY'

export type AvailabilityState = 'AVAILABLE' | 'UNAVAILABLE' | 'PREFERRED'

export type UserRole = 'PERSON_IN_CHARGE' | 'TEACHER' | 'STUDENT' | 'ADMINISTRATOR'

/**
 * Lifecycle of a run. The diagnosis branch is entered ONLY when the
 * optimisation run concludes that no timetable exists.
 */
export type RunState =
  | 'PENDING'
  | 'PREANALYSIS'
  | 'SOLVING'
  | 'SCORING'
  | 'COMPLETED'
  | 'INFEASIBLE'
  | 'DIAGNOSING'
  | 'DIAGNOSED'
  | 'FAILED'

/** slot = day_index * periods_per_day + period_index */
export interface Slot {
  index: number
  dayIndex: number
  periodIndex: number
  startHour: string
  endHour: string
  /** Driven by the calendar configuration, never by the model. */
  isOpen: boolean
}

export interface Placement {
  session: string
  slot: number
  room: string
}

export interface SubScore {
  criterion: string
  rawValue: number
  /** In [0, 1], 1 = best. Against instance-derived bounds (ADR-009). */
  normalised: number
}

/** Immutable once recorded. A regenerated timetable is a NEW candidate. */
export interface Candidate {
  id: string
  run: string
  profileName: string
  cost: number
  /** Out of 100. */
  score: number
  placements: Placement[]
  subScores: SubScore[]
}

/**
 * One criterion's part of the difference between two scores.
 *
 *   contribution = 100 * weight * (normalisedA - normalisedB)
 *
 * The sum of the contributions equals the score difference exactly. What the
 * comparison screen displays IS the score calculation read term by term — so
 * the figures must be shown, not summarised.
 */
export interface Contribution {
  criterion: string
  weight: number
  normalisedA: number
  normalisedB: number
  value: number
}

export interface Decomposition {
  candidateA: string
  candidateB: string
  scoreDifference: number
  contributions: Contribution[]
}

/**
 * Surfaced when the TOP-ranked candidate is dominated, because that reveals the
 * weights are concealing a compromise rather than expressing one.
 */
export interface DominanceVerdict {
  candidate: string
  dominatedBy: string | null
}

/**
 * The closed catalogue. Three actions, no more (ADR-007).
 *
 * A suggestion from the assistant that matches none of these is displayed as a
 * remark and MUST NOT carry a control to act on it.
 */
export type RecommendationAction =
  | { kind: 'weight_delta'; criterion: string; newWeight: number }
  | { kind: 'lock_session'; session: string }
  | { kind: 'exclude_slot'; session: string; slot?: number; room?: string }

export type RecommendationStatus = 'PROPOSED' | 'ACCEPTED' | 'REJECTED'

export interface Recommendation {
  id: string
  candidate: string
  action: RecommendationAction
  status: RecommendationStatus
  resultingCandidate: string | null
  /** The rule that produced it, shown to the user verbatim. */
  rationale: string
}

/**
 * A structural risk found before solving. Names the resource and the quantity
 * missing — never a bare boolean, which is what FR-12 requires.
 */
export interface CheckResult {
  name: string
  passed: boolean
  resource: string | null
  missingQuantity: number | null
  detail: string
}

/**
 * Rules SUFFICIENT to explain an infeasibility — not the smallest such set.
 * The interface must say so: the subset is heuristically reduced and is not
 * guaranteed minimal.
 */
export interface DiagnosisResult {
  conflictingCodes: string[]
  isMinimal: boolean
}

export interface Run {
  id: string
  createdAt: string
  seed: number
  /** Deterministic time, NOT wall-clock seconds (ADR-011). */
  deterministicBudget: number
  state: RunState
  modelVersion: string
  candidates: Candidate[]
  preAnalysis: CheckResult[]
  diagnosis: DiagnosisResult | null
}
