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
 * The rule is the standard Pareto one, adopted 2026-08-05 (C-14): at least as
 * good on EVERY criterion, strictly better on AT LEAST ONE. It replaced a
 * stricter reading (`>` everywhere) that was silent precisely when it mattered
 * — S10 carries weight 0, so a candidate beaten on all six weighted criteria
 * and tied on the seventh was reported as not dominated.
 *
 * ⚠️ Do NOT build a "the top candidate is dominated" indicator from this. That
 * state is PROVABLY UNREACHABLE, not merely rare: if B dominates A then
 * n_i(B) >= n_i(A) for every criterion, so
 *
 *   score(B) - score(A) = 100 * sum( w_i * ( n_i(B) - n_i(A) ) )
 *
 * is a sum of non-negative terms, hence score(B) >= score(A); and where it is
 * exactly zero — the strict gain landing on a zero-weight criterion —
 * TIE_BREAK_ORDER covers all seven criteria and resolves in B's favour. So A
 * can never rank first. Confirmed over 200,000 random dominated pairs: zero
 * counterexamples. **Adopting Pareto did not change this.**
 *
 * Dominance itself is NOT dead — a dominated RUNNER-UP is ordinary, and
 * `features/comparison/DominanceNotice.tsx` reports it, portfolio-wide, since
 * Phase 6 M1.
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
 *
 * `detail` carries the figures even when `passed` is true, and the screen must
 * show them. Passing is not the same as being safe: computer laboratories sit
 * at 90.9 % of their two-period windows — 8 spare in the whole week — while
 * the period figure reads a reassuring 71 %. Displaying only a tick would hide
 * the number that actually binds, which is the mistake C-13 cost three
 * sessions of work.
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
 *
 * ⚠️ **The natural reading of `conflictingCodes` is backwards.** It is an
 * unsat core: enforcing exactly those rules, with every other rule set aside,
 * already admits no timetable. It is NOT a repair list — relaxing them need
 * not make the instance solvable, because other rules may forbid the same
 * placements. Never render it as "change these and it will solve".
 *
 * ⚠️ **An empty `conflictingCodes` is two different outcomes**, and only
 * `isConclusive` separates them:
 *
 *  - conclusive and empty — no *relaxable* rule explains it. Only H1, H3, H7
 *    and H12 are posted constraints an assumption can attach to; H4–H6 and
 *    H8–H10 restrict a variable's domain before the search begins. The
 *    conflict is in the data, and `preAnalysis` is where to look.
 *  - not conclusive — CP-SAT could not prove the infeasibility within the
 *    budget. That is NOT evidence the instance is sound; it is the C-13 shape.
 *
 * `detail` says which, in words.
 */
export interface DiagnosisResult {
  conflictingCodes: string[]
  isMinimal: boolean
  isConclusive: boolean
  detail: string
}

/**
 * A published timetable, WITH the trace back to what produced it.
 *
 * ⚠️ The seed, weights, model version and budget are part of the payload
 * because the acceptance criterion is *"every published timetable traces back
 * to its run, seed and weights"* — a reader must not have to join three
 * endpoints to establish provenance. They are assembled server-side from the
 * run record on every read, never stored beside the publication, so there is
 * only ever one answer to "what produced this?".
 */
export interface PublishedTimetable {
  candidate: Candidate
  run: string
  seed: number
  weights: Record<string, number>
  modelVersion: string
  /** Deterministic time, NOT wall-clock seconds (ADR-011). */
  deterministicBudget: number
  publishedAt: string
  publishedBy: string
}

/**
 * The signed-in account — FR-11.
 *
 * ⚠️ It decides which screens the interface OFFERS, never what is permitted:
 * every endpoint checks the role for itself, because a client that hides a
 * control has not prevented the request.
 *
 * `teacher` is set only for a TEACHER and is the teacher id their account owns.
 * The availability screen reads it instead of offering a dropdown — which is
 * the whole of "a teacher account obtains only its own availability".
 */
export interface CurrentUser {
  id: string
  username: string
  role: UserRole
  teacher: string | null
  /** Set only for a STUDENT — SRS Table 2's "timetable of their group". */
  group: string | null
}

/** One entry of the academic calendar — FR-9.
 *
 * ⚠️ A holiday does not close a slot by itself. ADR-003 gives the calendar two
 * effects and a holiday reaches the model through the first: an administrator
 * closes the slots concerned, and H9 does the rest. The weekly grid is a
 * repeating template with no dates on it.
 */
export interface Holiday {
  date: string
  label: string
  lunar: boolean
  approximate: boolean
  blocking: boolean
}

/** ⚠️ Displayed hours only (ADR-003). The slot index does not move. */
export interface ShortenedDay {
  start: string
  end: string
  shiftMinutes: number
}

export interface ShiftedHour {
  slot: number
  startHour: string
  endHour: string
}

/**
 * The calendar in force, and what it was edited away from — FR-9.
 *
 * `slots` already carry the administrator's closures; `loadedOpenSlots` is what
 * the 13 CSVs supply, so the screen can show a closure as a *change* rather
 * than as a state, and "réinitialiser" is a visible act.
 */
export interface CalendarData {
  slots: Slot[]
  loadedOpenSlots: number[]
  holidays: Holiday[]
  /** ⚠️ False means nobody has stated a list, so the instance's own stands —
   * deliberately different from an empty list, which states there are none. */
  holidaysStated: boolean
  shortenedDay: ShortenedDay | null
  shiftedHours: ShiftedHour[]
  openSlotCount: number
  editedAt: string | null
  editedBy: string | null
}

/** An account as the administration screen sees it. Carries no credential. */
export interface Account {
  id: string
  username: string
  role: UserRole
  teacher: string | null
  group: string | null
}

/**
 * The published timetable of the signed-in student's group — SRS Table 2.
 *
 * ⚠️ `placements` is filtered **on the server**. A payload carrying every
 * group's week with the browser hiding the rest would be granting the student
 * every group's week and calling the difference presentation.
 */
export interface StudentTimetable {
  group: string
  groupLabel: string
  placements: Placement[]
  publishedAt: string | null
  publishedBy: string | null
  run: string | null
  candidate: string | null
}

/**
 * One run and its candidates.
 *
 * Two fields report on stages rather than on results, and both are read wrong
 * by default:
 *
 *  - `preAnalysis` — **an empty array means the stage did not run**, never
 *    "verified, nothing wrong".
 *  - `diagnosis` — `null` on every run that produced a timetable, because
 *    stage 3 is entered only from `INFEASIBLE`. A non-null diagnosis does NOT
 *    mean a conflict was named; read `isConclusive` and `conflictingCodes`.
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
  /** The five checks, in the order they are reported. Empty means not run. */
  preAnalysis: CheckResult[]
  /** Stage 3's report. `null` unless the run reached `DIAGNOSED`. */
  diagnosis: DiagnosisResult | null
  /** In rank order, best first. Display this order; do not sort. */
  candidates: Candidate[]
  /** Profile names whose timetable was identical to one already obtained. */
  duplicatesRemoved: string[]
  deterministicTimeUsed: number
  wallClockSeconds: number
  error: string | null
  /** Where a regenerated run came from — FR-23. `null` on a run launched from
   * the generation screen, which is most of them. */
  origin: RunOrigin | null
  /** The locks and exclusions this run solved under, composed along the
   * regeneration chain. All three arrays empty on an ordinary run. */
  overrides: RunOverrides
}

/**
 * Where a regenerated run came from — FR-23.
 *
 * ⚠️ `actionDetail` is prose for a reader. Do NOT parse it back into an action:
 * the catalogue is closed (ADR-007) and an action is built from typed fields or
 * not at all.
 */
export interface RunOrigin {
  run: string
  candidate: string
  actionKind: RecommendationActionKind
  actionDetail: string
}

/** The three catalogue actions. Closed — a fourth is a change to ADR-007. */
export type RecommendationActionKind = 'weight_delta' | 'lock_session' | 'exclude_slot'

/** The locks and exclusions one run solved under. Sorted by the API. */
export interface RunOverrides {
  lockedPlacements: Placement[]
  excludedSlots: [string, number][]
  excludedRooms: [string, string][]
}

/**
 * Text from the language service — FR-22, FR-24, FR-25.
 *
 * ⚠️ **`generated` must be shown, not merely carried.** A reader has to be able
 * to tell a sentence a language model wrote from one the application computed.
 * The computed form is the honest one, so a screen that hid the distinction
 * would mislead in the direction that flatters the model.
 *
 * `fallbackReason` is null on a generated answer. Otherwise it says why: the
 * service is off, unreachable, timed out, or — the one worth reading — the
 * answer contained a figure absent from the context and was discarded.
 */
export interface AssistantAnswer {
  text: string
  generated: boolean
  fallbackReason: string | null
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

/**
 * FR-1 — the department data, and where it came from.
 *
 * `imported: false` means no dataset has been supplied and the reference files
 * govern. ⚠️ Distinct from an imported dataset that happens to match them:
 * collapsing the two would make the withdrawal control meaningless.
 */
export interface DatasetSummary {
  imported: boolean
  importedAt: string | null
  importedBy: string | null
  files: string[]
  programmes: number
  promotions: number
  groups: number
  teachers: number
  courses: number
  sessions: number
  rooms: number
  slots: number
  holidays: number
}

/**
 * One line the server refused — SRS §3.2 Table 4's "report of the rejected
 * lines". `line` is the physical line number, header included; `null` means the
 * fault is the file as a whole.
 */
export interface RejectedLine {
  file: string
  line: number | null
  reason: string
  field: string | null
  value: string | null
}

/**
 * One stored statement a replacement would orphan — the A7 project decision.
 *
 * ⚠️ **Not a rejected line, and the screen must not present it as one.** A
 * rejected line is fixed by editing the file; an incompatibility is fixed by a
 * person withdrawing a declaration or a closure. Showing them in one list would
 * tell somebody to correct a file that is already correct.
 */
export interface Incompatibility {
  overlay: string
  subject: string
  reason: string
  remedy: string
}

export interface DatasetImportResult {
  accepted: boolean
  dataset: DatasetSummary
  rejectedLines: RejectedLine[]
  incompatibilities: Incompatibility[]
  /**
   * False when a line failed to parse, so references were not examined yet.
   * Fixing the types can reveal a further round; the screen says so rather than
   * letting a user infer that the list was complete.
   */
  referencesChecked: boolean
}

/**
 * One examination, placed — FR-20.
 *
 * ⚠️ **`rooms` is an ARRAY and that is R-6, not a convenience.** SRS §3.2
 * Table 19 promises "one slot and one or more rooms assigned to each
 * examination", and §6.8 explains why: an examination may occupy several rooms
 * at once, so room assignment is a sum of capacities rather than the choice of
 * a single room. The weekly `Placement` carries one `room`; the two must not be
 * conflated, and `slot` here indexes the EXAMINATION PERIOD, not the week.
 */
export interface ExamPlacement {
  examination: string
  course: string
  promotion: string
  supervisor: string
  candidateCount: number
  slot: number
  day: string
  periodIndex: number
  rooms: string[]
  /** Σ of the assigned rooms' capacities, so a reader can check X2 on screen. */
  assignedCapacity: number
}

export interface ExamRun {
  id: string
  state: RunState
  createdAt: string
  seed: number
  deterministicBudget: number
  examinationCount: number
  slotCount: number
  spreadPenalty: number | null
  provenOptimal: boolean | null
  wallClockSeconds: number | null
  placements: ExamPlacement[]
  /**
   * Verbatim from the server. Usually a refusal to derive the session at all —
   * an empty roster, an unset examination period — which is actionable in a way
   * that "generation failed" is not, so the screen shows it as written.
   */
  error: string | null
}
