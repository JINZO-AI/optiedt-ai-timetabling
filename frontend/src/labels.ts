/**
 * How the product names things to a user.
 *
 * ⚠️ **This maps identifiers to WORDS. It computes nothing.** The presentation
 * layer may "display, filter, print" and may not "compute a score, decide an
 * order" (`docs/architecture.md`) — a lookup table of names is squarely the
 * first.
 *
 * ⚠️ **Domain vocabulary is NOT translated and must not be.** `CM`, `TD`, `TP`,
 * `Amphi`, `Salle`, `Lab_Info`, `Lab_Sciences` and the teacher ranks are the
 * values the instance CSVs carry, and CLAUDE.md keeps them verbatim in code:
 * translating them would put a mapping layer between the application and its
 * own data for no benefit. What is translated here is interface chrome —
 * profile names, criterion names, run states — which no CSV contains.
 */

/**
 * The three weight profiles, in the words a department would use.
 *
 * ⚠️ **A profile's promise is the one C-15 reworded, and the wording matters.**
 * A favouring profile produces the best value of its HEADLINE criterion among
 * the candidates — it does not win every criterion of its constituency, and no
 * weighted sum can deliver that (the teacher criteria genuinely conflict). The
 * descriptions below say "leans towards", never "best for".
 */
const PROFILES: Record<string, { label: string; blurb: string }> = {
  balanced: {
    label: 'Balanced',
    blurb: 'Weighs every quality criterion at its catalogue weight',
  },
  'student-favouring': {
    label: 'Student-friendly',
    blurb: 'Leans towards fewer gaps in a student’s day',
  },
  'teacher-favouring': {
    label: 'Teacher-friendly',
    blurb: 'Leans towards fewer gaps and fewer days on site for teachers',
  },
}

export function profileLabel(profile: string): string {
  return PROFILES[profile]?.label ?? profile
}

export function profileBlurb(profile: string): string | null {
  return PROFILES[profile]?.blurb ?? null
}

/**
 * The seven soft criteria.
 *
 * ⚠️ The codes are stable identifiers and stay visible beside the name: the
 * specification, the catalogue and every document argue in codes, so a screen
 * that showed only prose would stop being checkable against them. S1, S8 and
 * S9 are retired and never reused.
 */
const CRITERIA: Record<string, string> = {
  S2: 'Student idle time',
  S3: 'Teacher idle time',
  S4: 'Extra working day',
  S5: 'Teacher preference',
  S6: 'Room efficiency',
  S7: 'Subject spread',
  S10: 'Lunch break',
}

export function criterionLabel(code: string): string {
  return CRITERIA[code] ?? code
}

/** Run states, as a person reads them. */
const RUN_STATES: Record<string, { label: string; tone: 'ok' | 'run' | 'warn' | 'bad' | 'idle' }> = {
  PENDING: { label: 'Queued', tone: 'idle' },
  PREANALYSIS: { label: 'Checking data', tone: 'run' },
  SOLVING: { label: 'Optimising', tone: 'run' },
  SCORING: { label: 'Scoring', tone: 'run' },
  COMPLETED: { label: 'Completed', tone: 'ok' },
  INFEASIBLE: { label: 'No solution exists', tone: 'warn' },
  DIAGNOSING: { label: 'Diagnosing', tone: 'run' },
  DIAGNOSED: { label: 'Conflict reported', tone: 'warn' },
  FAILED: { label: 'Failed', tone: 'bad' },
}

export function runStateLabel(state: string): string {
  return RUN_STATES[state]?.label ?? state
}

export function runStateTone(state: string): string {
  return RUN_STATES[state]?.tone ?? 'idle'
}

/** True once a run can no longer change. */
export function isSettled(state: string): boolean {
  return state === 'COMPLETED' || state === 'FAILED' || state === 'DIAGNOSED' || state === 'INFEASIBLE'
}
