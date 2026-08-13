/**
 * FR-20 — generate and consult the timetable of an examination session.
 *
 * ⚠️ **The examinations are DERIVED, so this screen asks for no examination
 * data.** One examination per course, its candidates the students of the
 * course's promotion, its supervisor the CM teacher, its period the two
 * calendar keys — C-23 and ADR-013. A form collecting examinations here would
 * be the examination-data upload system FR-1 was deliberately scoped not to
 * become (SRS §4.1 names no such form).
 *
 * ⚠️ **202 and poll, like the generation screen.** A solve takes about half a
 * minute and no HTTP request is held open for it (ADR-005).
 *
 * ⚠️ **A refusal is shown verbatim and is not styled as a crash.** The common
 * case is a department dataset with no roster: `students.csv` is not one of the
 * eleven files FR-1 admits, and X1 and X2 are both about students. "No students
 * for this course" with the reason is actionable; "failed" is not.
 */

import { useState } from 'react'

import { useExamRun, useExamRuns, useGenerateExamSession } from '@/api/queries'
import { ExamCalendar } from '@/features/examination/ExamCalendar'
import { Page } from '@/shell/Page'
import type { ExamRun } from '@/types/domain'

/** The two presets a user actually chooses between, in their own words.
 *
 * ⚠️ This is U2's lesson applied at the point of writing rather than retrofitted.
 * The generation screen shipped with `Graine` and `Budget déterministe (pas des
 * secondes)` — two raw solver parameters — and the first-use session reported
 * that users "do not understand the purpose of each action". A deterministic
 * budget is a unit of WORK, not of time (ADR-011), which is precisely why it
 * cannot be labelled "seconds" and must not be shown raw.
 */
const PRESETS = [
  {
    id: 'quick',
    label: 'Quick',
    hint: 'A first calendar in around half a minute.',
    deterministicBudget: 10,
  },
  {
    id: 'thorough',
    label: 'Thorough',
    hint: 'Searches longer for a better spread of examinations.',
    deterministicBudget: 60,
  },
] as const

/** The four rules the examination model enforces, named where a user meets them. */
const RULES = [
  ['X1', 'Every candidate sits every examination they are entered for'],
  ['X2', 'Rooms seat all the candidates — an examination may take several'],
  ['X3', 'A room hosts one examination per period'],
  ['X4', 'No supervisor is in two places at once'],
  ['SX1', 'Examinations are spread across the period rather than bunched'],
] as const

export function ExaminationScreen() {
  const [runId, setRunId] = useState<string | null>(null)
  const [preset, setPreset] = useState<(typeof PRESETS)[number]['id']>('quick')
  const generate = useGenerateExamSession()
  const previous = useExamRuns()

  // ⚠️ **Fall back to the most recent run on the server.** `runId` is component
  // state, so navigating away and back lost a calendar the server still had —
  // found by driving the application, not by a test. The list endpoint returns
  // newest first, so this recovers the session a user just generated instead of
  // showing them an empty screen that says nothing has been generated.
  const latest = previous.data?.[0]?.id ?? null
  const shown = runId ?? latest
  const run = useExamRun(shown)

  const chosen = PRESETS.find((p) => p.id === preset) ?? PRESETS[0]
  const current = run.data
  const running =
    generate.isPending ||
    (current !== undefined && !['COMPLETED', 'FAILED', 'INFEASIBLE'].includes(current.state))

  function launch() {
    generate.mutate(
      { seed: 42, deterministicBudget: chosen.deterministicBudget },
      { onSuccess: (created) => setRunId(created.id) },
    )
  }

  return (
    <Page
      title="Examination session"
      subtitle="One examination per course, placed within the examination period set in Administration"
      status={current && <ExamState run={current} />}
      actions={
        <>
          <label className="bar-field">
            <span>Effort</span>
            <select
              aria-label="Search effort"
              value={preset}
              onChange={(e) => setPreset(e.target.value as (typeof PRESETS)[number]['id'])}
              disabled={running}
            >
              {PRESETS.map((option) => (
                <option key={option.id} value={option.id} title={option.hint}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button onClick={launch} disabled={running}>
            {running ? 'Generating…' : 'Generate calendar'}
          </button>
        </>
      }
    >
      <section className="section">
        <p className="screen__lead">
          The candidates are the students of the promotion concerned, and the supervisor is the
          teacher who gives the lecture — both derived from the department data rather than
          collected here. {chosen.hint}
        </p>

        {/* ⚠️ **The rules are named on the screen that enforces them.** When a
            session comes back INFEASIBLE, "no calendar satisfies X1 to X4" is
            only actionable if the reader has been told what X1 to X4 are. */}
        <ul className="rulelist">
          {RULES.map(([code, text]) => (
            <li key={code}>
              <span className="code">{code}</span>
              <span>{text}</span>
            </li>
          ))}
        </ul>
      </section>

      {generate.isError && (
        <p className="warning" role="alert">
          The examination session could not be started. Only the timetable officer can generate one.
        </p>
      )}

      {shown === null && !generate.isPending && (
        <p className="empty">
          No examination session has been generated yet. Choose a search effort and press{' '}
          <b>Generate calendar</b> — the calendar will appear here.
        </p>
      )}

      {current && <RunStatus run={current} />}
      {current && <ExamCalendar run={current} />}
    </Page>
  )
}

function ExamState({ run }: { run: ExamRun }) {
  if (run.state === 'COMPLETED') return <span className="badge badge--ok">Completed</span>
  if (run.state === 'FAILED') return <span className="badge badge--bad">Failed</span>
  if (run.state === 'INFEASIBLE') return <span className="badge badge--warn">No solution</span>
  return <span className="badge badge--run">{run.state}</span>
}

function RunStatus({ run }: { run: ExamRun }) {
  if (run.state === 'FAILED') {
    return (
      <div className="warning" role="alert">
        <strong>The examination session could not be built.</strong>
        {/* Verbatim: the server's reason is actionable and a paraphrase would
            not be. See the module docstring. */}
        <p>{run.error}</p>
      </div>
    )
  }
  if (run.state === 'INFEASIBLE') {
    return (
      <div className="warning" role="alert">
        <strong>No calendar satisfies rules X1 to X4.</strong>
        <p>
          The examination period is too short, or the rooms cannot seat the candidates. Lengthen the
          period in Administration and try again.
        </p>
      </div>
    )
  }
  if (run.state !== 'COMPLETED') {
    return (
      <p className="pending">
        <span className="ai__thinking-dots" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
        Working… ({run.state})
      </p>
    )
  }
  return (
    <p className="success">
      Calendar generated
      {run.provenOptimal ? ', proven optimal' : ''}
      {run.wallClockSeconds !== null && ` in ${run.wallClockSeconds.toFixed(1)} s`}.
    </p>
  )
}
