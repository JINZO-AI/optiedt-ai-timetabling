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

/**
 * Lecture theatre · classroom · computer lab · science lab.
 *
 * These are the literals in rooms.csv and the values the API sends, kept in
 * French verbatim (CLAUDE.md, "Conventions"). They were English constants
 * until Phase 4 — which matched nothing the API can send, so any room filter
 * written against them would have matched zero rows while looking correct.
 * Pinned on the wire by backend tests/unit/test_api_schemas.py.
 */
export type RoomType = 'Amphi' | 'Salle' | 'Lab_Info' | 'Lab_Sciences'

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

/** Position in the promotion → tutorial group → laboratory subgroup chain. */
export type GroupLevel = 'PROMO' | 'TD' | 'TP'

/** Unaccented, as teachers.csv carries them. Rank fixes the weekly load. */
export type TeacherRank =
  | 'Professeur'
  | 'Maitre de Conferences'
  | 'Maitre Assistant'
  | 'Assistant'

export type ConstraintKind = 'HARD' | 'SOFT'

/** SYNTHETIC marks a generated declaration; it must never pass for a real one. */
export type DeclarationSource = 'TEACHER' | 'SYNTHETIC'

export interface Programme {
  id: string
  code: string
  label: string
  degreeCycle: string
  department: string
}

export interface Promotion {
  id: string
  programme: string
  level: string
  academicYear: string
  studentCount: number
}

export interface Group {
  id: string
  promotion: string
  parentGroup: string | null
  level: GroupLevel
  label: string
  size: number
}

export interface Teacher {
  id: string
  department: string
  rank: TeacherRank
  maxHoursPerWeek: number
}

export interface Course {
  id: string
  code: string
  department: string
  programme: string
  level: string
  semester: number
  credits: number
}

/** The unit CP-SAT places. `durationPeriods` is 1 or 2. */
export interface Session {
  id: string
  course: string
  group: string
  teacher: string
  type: SessionType
  durationPeriods: number
  occurrencesPerWeek: number
  requiredRoomType: RoomType
  locked: boolean
}

export interface Room {
  id: string
  building: string
  code: string
  capacity: number
  type: RoomType
  equipment: string[]
}

export interface Availability {
  teacher: string
  slot: number
  state: AvailabilityState
  semester: number
  source: DeclarationSource
}

export interface ConstraintDefinition {
  code: string
  name: string
  kind: ConstraintKind
  defaultWeight: number
  xhsttReference: string | null
}

/**
 * Everything a screen renders against, fetched once.
 *
 * A `Placement` carries ids only, so turning one into something readable needs
 * this — which is what keeps a candidate exactly what the solver produced.
 */
export interface InstanceData {
  programmes: Programme[]
  promotions: Promotion[]
  groups: Group[]
  teachers: Teacher[]
  courses: Course[]
  sessions: Session[]
  rooms: Room[]
  slots: Slot[]
  constraints: ConstraintDefinition[]
  calendarConfig: Record<string, string>
}

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
 * A candidate another candidate improves on across the board.
 *
 * ⚠️ Do NOT build a "the top candidate is dominated" indicator from this. That
 * state is PROVABLY UNREACHABLE, not merely rare: if B dominates A then
 * n_i(B) > n_i(A) for every criterion, so
 *
 *   score(B) - score(A) = 100 * sum( w_i * ( n_i(B) - n_i(A) ) )
 *
 * is a sum of non-negative terms with at least one positive weight (weights
 * are renormalised to sum to 1). So score(B) > score(A) strictly and A can
 * never rank first. Confirmed over 200,000 random dominated pairs: zero
 * counterexamples. It holds under the Pareto reading too, because
 * TIE_BREAK_ORDER covers all seven criteria.
 *
 * Dominance itself is NOT dead — a dominated RUNNER-UP is ordinary, and the
 * comparison screen can report it. Only the top-candidate case cannot fire,
 * despite both specification documents asking for it.
 *
 * ⚠️ C-14 is OPEN and owned by the technical lead: whether dominance keeps the
 * strict reading (`>` on every criterion, which S10's zero weight makes bite)
 * or moves to the Pareto reading, and how the specification's wording is
 * repaired. Settle it before this drives any UI. See docs/open-questions.md.
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

/**
 * One run and its candidates.
 *
 * ⚠️ `preAnalysis` and `diagnosis` are NOT here, and their absence is the
 * point. The five checks (FR-12) and the diagnosis run are Phase 5, so the API
 * omits both rather than sending empty values: an empty check list would read
 * as "verified, nothing wrong" when it means "never verified". `CheckResult`
 * and `DiagnosisResult` stay declared below because the shapes are agreed —
 * add the fields here with the work that fills them, not before.
 */
export interface Run {
  id: string
  createdAt: string
  seed: number
  /** Deterministic time, NOT wall-clock seconds (ADR-011). Never render it as
   * a duration — the system makes no wall-clock promise. */
  deterministicBudget: number
  state: RunState
  modelVersion: string
  /** The weights in force: ONE vector prices every candidate of this run. */
  weights: Record<string, number>
  /** In rank order, best first. Display this order; do not sort. */
  candidates: Candidate[]
  /** Profile names whose timetable was identical to one already obtained. */
  duplicatesRemoved: string[]
  deterministicTimeUsed: number
  wallClockSeconds: number
  error: string | null
}

/** A run without its placements, for a list. */
export interface RunSummary {
  id: string
  createdAt: string
  seed: number
  state: RunState
  candidateCount: number
  duplicatesRemoved: string[]
}

/**
 * FR-16 — the candidate the system puts forward, and the rule that chose it.
 *
 * ⚠️ Not to be confused with `Recommendation` below, which is a different
 * thing entirely: one of the closed 3-action catalogue, belonging to
 * regeneration (FR-23, Phase 5).
 */
export interface RecommendedCandidate {
  candidate: string
  rule: string
  score: number
  dominatedBy: string | null
}
