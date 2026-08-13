import { runStateLabel } from '@/labels'
import type { RunState } from '@/types/domain'

/**
 * The three stages of a generation, and where this run has reached.
 *
 * ⚠️ **This is the pipeline `docs/architecture.md` specifies, not an
 * illustration of one.** Stages 1 and 2 always run; **stage 3 runs only when
 * stage 2 returns `INFEASIBLE`** — so diagnosis is drawn as a branch off the
 * solve rather than as a fourth step in a row, which is what it is.
 *
 * ⚠️ It answers "what is happening" during the minutes a solve takes. A spinner
 * says only that something is; this says which of three different things, and
 * a reader who knows the solve has started also knows the data checks passed.
 */

type Stage = { key: string; code: string; label: string; note: string }

const STAGES: Stage[] = [
  {
    key: 'checks',
    code: 'FR-12',
    label: 'Data checks',
    note: 'Five arithmetic checks, no solver',
  },
  { key: 'solve', code: 'H1–H12', label: 'Optimisation', note: 'CP-SAT places every session' },
  { key: 'score', code: 'S2–S10', label: 'Score & rank', note: 'Exact weighted sum' },
]

type StageState = 'waiting' | 'active' | 'done' | 'failed'

/** Where each stage stands, read from the one field the server owns. */
export function stageStates(state: RunState): Record<string, StageState> {
  const order: Record<string, number> = {
    PENDING: 0,
    PREANALYSIS: 1,
    SOLVING: 2,
    SCORING: 3,
    COMPLETED: 4,
    INFEASIBLE: 2,
    DIAGNOSING: 2,
    DIAGNOSED: 2,
    FAILED: 0,
  }
  const reached = order[state] ?? 0
  const infeasible = state === 'INFEASIBLE' || state === 'DIAGNOSING' || state === 'DIAGNOSED'

  function at(position: number): StageState {
    if (state === 'FAILED') return position === 1 ? 'failed' : 'waiting'
    if (infeasible && position === 2) return 'failed'
    if (infeasible && position === 3) return 'waiting'
    if (reached > position) return 'done'
    if (reached === position) return 'active'
    return 'waiting'
  }

  return { checks: at(1), solve: at(2), score: at(3) }
}

export function RunPipeline({ state }: { state: RunState }) {
  const states = stageStates(state)
  const branched = state === 'INFEASIBLE' || state === 'DIAGNOSING' || state === 'DIAGNOSED'

  return (
    <div className="pipeline" aria-label={`Run stage: ${runStateLabel(state)}`}>
      <ol className="pipeline__track">
        {STAGES.map((stage) => {
          const status = states[stage.key] ?? 'waiting'
          return (
            <li key={stage.key} className={`pipeline__stage pipeline__stage--${status}`}>
              <span className="pipeline__dot" aria-hidden="true" />
              <span className="pipeline__body">
                <span className="pipeline__code">{stage.code}</span>
                <span className="pipeline__label">{stage.label}</span>
                <span className="pipeline__note">{stage.note}</span>
              </span>
            </li>
          )
        })}
      </ol>

      {/* ⚠️ **`PENDING` needs a reason, and it has one.** Runs execute on a
          single-worker pool because each solve already uses every core, so a
          second one oversubscribes the machine (ADR-005). Found by launching
          two runs and watching the second sit on "Queued" for minutes with an
          all-grey pipeline and nothing saying why — which reads as a hung
          application rather than as a queue. */}
      {state === 'PENDING' && (
        <p className="pipeline__branch pipeline__branch--wait">
          <span className="pipeline__dot" aria-hidden="true" />
          Queued. Solves run one at a time — each uses every processor core, so a second run would
          slow the first rather than finish sooner. This one starts as soon as the current run ends.
        </p>
      )}

      {/* ⚠️ Drawn only when it actually ran. A permanently visible fourth step
          would teach the reader that diagnosis is part of every run, and a
          control that never fires reads as "no problem found". */}
      {branched && (
        <p className="pipeline__branch">
          <span className="pipeline__dot pipeline__dot--warn" aria-hidden="true" />
          No timetable exists under the mandatory rules — each rule was withdrawn in turn to find
          which are responsible.
        </p>
      )}
    </div>
  )
}
