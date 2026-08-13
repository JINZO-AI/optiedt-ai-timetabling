import { useMemo, useState } from 'react'

import {
  useComparison,
  useCurrentUser,
  useDominance,
  useInstance,
  useRecommendation,
  useRegenerate,
  useRun,
  useRuns,
} from '@/api/queries'
import { userMessage } from '@/api/errors'
import { AssistantPanel } from '@/features/assistant/AssistantPanel'
import { criterionLabel, profileBlurb, profileLabel } from '@/labels'
import { ContributionsTable } from '@/features/comparison/ContributionsTable'
import { DominanceNotice } from '@/features/comparison/DominanceNotice'
import { RegenerationPanel } from '@/features/comparison/RegenerationPanel'
import { Page } from '@/shell/Page'
import type { Candidate, ConstraintDefinition } from '@/types/domain'

/**
 * FR-14 and FR-15 — two candidates side by side, and why they differ.
 *
 * Both candidates are priced by the run's **weights in force**, one vector for
 * the whole portfolio. A candidate's `profileName` is provenance — how it was
 * obtained — never its own scoring weight: the exact-decomposition identity
 * only holds when the same w_i prices both sides.
 *
 * ⚠️ **The screen does not claim what a profile "favours".** A favouring
 * profile promises the best value of its **headline** criterion, not a win
 * across its constituency — the teacher criteria genuinely conflict, and
 * solving S3 alone drives S5 to 113. So a caption reading "favours teachers"
 * would overstate what the screen can show. The measured sub-scores are
 * displayed instead, and they speak for themselves.
 *
 * **The dominance signal landed in Phase 6 M1**, once **C-14** was resolved.
 * Phase 4 shipped none at all, deliberately: under the strict reading then in
 * force the only signal both specification documents described — "a dominated
 * *top* candidate" — is provably unreachable, and a control that never fires
 * teaches the reader it means "no problem found". What is displayed now is
 * dominance *anywhere in the portfolio*, under the standard Pareto rule.
 */
/**
 * One precision for every figure on this screen.
 *
 * ⚠️ Scores and the difference **must** be shown at the same precision, or the
 * screen contradicts itself in front of the one reader it is built for. Two
 * candidates scoring 79.8163 and 79.7943 display as "79.82" and "79.79" at two
 * decimals; a head of department subtracts those and gets 0.03, while the
 * decomposition correctly totals 0.02 — the true difference is 0.022. Nothing
 * is wrong with either figure, and the page still looks like it cannot add up.
 * At three decimals the same pair reads 79.816, 79.794 and +0.022, and the
 * subtraction works by hand.
 */
const COMPARISON_DIGITS = 3

export function ComparisonScreen() {
  const runs = useRuns()
  const instance = useInstance()
  // SRS Table 2: launching a run — including the new run an accepted
  // recommendation starts — belongs to the person in charge. Read from the
  // authenticated identity, never from anything the client chose.
  const mayRegenerate = useCurrentUser().data?.role === 'PERSON_IN_CHARGE'

  const withCandidates = (runs.data ?? []).filter((r) => r.candidateCount >= 2)
  const [runId, setRunId] = useState<string | null>(null)
  const selectedRunId = runId ?? withCandidates[0]?.id ?? null
  const run = useRun(selectedRunId)
  const recommendation = useRecommendation(selectedRunId)

  const candidates = run.data?.candidates ?? []
  const [aId, setAId] = useState<string | null>(null)
  const [bId, setBId] = useState<string | null>(null)
  const a = candidates.find((c) => c.id === aId) ?? candidates[0]
  const b = candidates.find((c) => c.id === bId) ?? candidates[1]

  const comparison = useComparison(selectedRunId, a?.id ?? null, b?.id ?? null)
  const dominance = useDominance(selectedRunId)
  const regenerate = useRegenerate(selectedRunId)
  const [launched, setLaunched] = useState<string | null>(null)

  const catalogue = useMemo(
    () =>
      new Map<string, ConstraintDefinition>(
        (instance.data?.constraints ?? []).map((c) => [c.code, c]),
      ),
    [instance.data],
  )

  if (runs.isLoading)
    return (
      <Page title="Compare candidates">
        <p className="empty">Loading runs…</p>
      </Page>
    )

  if (withCandidates.length === 0)
    return (
      <Page
        title="Compare candidates"
        subtitle="Two timetables, and exactly where they differ"
      >
        <p className="empty">
          No run has two candidates to compare yet. Generate a timetable first — a run produces
          several candidates, and this screen explains the difference between any two of them.
        </p>
      </Page>
    )

  const sameCandidate = a !== undefined && b !== undefined && a.id === b.id
  const difference = comparison.data?.scoreDifference ?? null

  return (
    <Page
      title="Compare candidates"
      subtitle={
        selectedRunId
          ? `Run ${selectedRunId} · ${candidates.length} candidates · priced under one set of weights`
          : undefined
      }
      actions={
        <label className="bar-field">
          <span>Run</span>
          <select
            aria-label="Run"
            value={selectedRunId ?? ''}
            onChange={(e) => {
              setRunId(e.target.value)
              setAId(null)
              setBId(null)
            }}
          >
            {withCandidates.map((r) => (
              <option key={r.id} value={r.id}>
                {r.id} — {r.candidateCount} candidates
              </option>
            ))}
          </select>
        </label>
      }
    >
      {/* ⚠️ The recommendation is a computed verdict, so it is presented as one
          — the rule that produced it is named, and it is never worded as
          advice from the assistant. */}
      {recommendation.data && (
        <p className="note recommendation">
          <span className="badge badge--run">Computed recommendation</span>
          <span>
            <b>{recommendation.data.candidate}</b> — {recommendation.data.rule}
          </span>
        </p>
      )}

      <div className="split">
        <div className="split__main">
          <section className="section">
            <div className="h2h">
              <Side
                side="A"
                candidate={a}
                candidates={candidates}
                value={a?.id ?? ''}
                onChange={setAId}
                id="candidate-a"
              />

              <div className="h2h__delta">
                <span className="h2h__delta-value">
                  {difference === null ? '—' : formatSigned(difference, COMPARISON_DIGITS)}
                </span>
                <span className="h2h__delta-label">
                  {difference === null || difference === 0
                    ? 'no difference'
                    : difference > 0
                      ? 'A leads by'
                      : 'B leads by'}
                </span>
              </div>

              <Side
                side="B"
                candidate={b}
                candidates={candidates}
                value={b?.id ?? ''}
                onChange={setBId}
                id="candidate-b"
              />
            </div>
          </section>

          {sameCandidate && (
            <p className="warning">Choose two different candidates to compare.</p>
          )}

          {a && b && !sameCandidate && (
            <>
              <section className="section">
                <div className="section__head">
                  <h2 className="section__title">
                    Where the difference comes from
                    <span className="section__code">FR-15</span>
                  </h2>
                </div>
                <p className="panel__note">
                  A criterion contributes 100 × weight × (n(A) − n(B)). The contributions sum{' '}
                  <em>exactly</em> to the difference in score: this table is the score calculation
                  read term by term, not a summary of it.
                </p>
                {comparison.isLoading && <p className="empty empty--inline">Calculating…</p>}
                {comparison.data && (
                  <ContributionsTable
                    decomposition={comparison.data}
                    catalogue={catalogue}
                    digits={COMPARISON_DIGITS}
                  />
                )}
              </section>

              <section className="section">
                <div className="section__head">
                  <h2 className="section__title">
                    Dominance
                    <span className="section__code">ADR-002 · Pareto</span>
                  </h2>
                </div>
                {dominance.isLoading && <p className="empty empty--inline">Checking…</p>}
                {dominance.data && (
                  <DominanceNotice
                    verdicts={dominance.data}
                    candidates={candidates}
                    compared={[a.id, b.id]}
                  />
                )}
              </section>

              {/* ⚠️ **Regeneration is offered only to the role that may perform
                  it.** A teacher reaching this screen was previously shown the
                  control and, on pressing it, the server's own words: "ApiError:
                  403: role TEACHER may not do this". The endpoint was right to
                  refuse — what was wrong was offering the action at all, and
                  then printing an internal message at a user.

                  ⚠️ **Hiding it is NOT the authorisation.** `POST
                  .../regenerate` still checks the role for itself (FR-11); this
                  decides only what is on screen. */}
              {run.data && (
                <section className="section">
                  <div className="section__head">
                    <h2 className="section__title">
                      Improve this timetable
                      <span className="section__code">FR-23</span>
                    </h2>
                  </div>
                  {mayRegenerate ? (
                    <RegenerationPanel
                      run={run.data}
                      candidate={a}
                      catalogue={catalogue}
                      pending={regenerate.isPending}
                      error={
                        regenerate.error === null
                          ? null
                          : userMessage(regenerate.error, 'regenerate')
                      }
                      launched={launched}
                      onAccept={(action) => {
                        regenerate.mutate(
                          { candidateId: a.id, action },
                          // The new run is announced by ID rather than switched
                          // to. Replacing what is on screen would read as this
                          // candidate having changed, which is the one thing
                          // regeneration must never look like.
                          { onSuccess: (created) => setLaunched(created.runId) },
                        )
                      }}
                    />
                  ) : (
                    <p className="empty empty--inline">
                      Accepting a recommendation starts a new run, which only the timetable officer
                      may do. You can read this comparison and its explanation in full.
                    </p>
                  )}
                </section>
              )}
            </>
          )}
        </div>

        {/* ⚠️ Rendered whether or not a language service is configured. Hiding
            it when the service is off would make a working application look
            incomplete: the panel then shows the computed form, which is a
            complete answer (invariant 5). */}
        <aside className="split__aside">
          <AssistantPanel runId={selectedRunId as string} candidateId={a?.id ?? null} />
        </aside>
      </div>
    </Page>
  )
}

/**
 * One side of the comparison: which candidate, its score, its fingerprint.
 *
 * ⚠️ The score is shown at `COMPARISON_DIGITS`, the same precision as the
 * difference beside it, so the subtraction works by hand.
 */
function Side({
  side,
  candidate,
  candidates,
  value,
  onChange,
  id,
}: {
  side: 'A' | 'B'
  candidate: Candidate | undefined
  candidates: Candidate[]
  value: string
  onChange: (id: string) => void
  id: string
}) {
  return (
    <div className={`h2h__side h2h__side--${side.toLowerCase()}`}>
      <label className="h2h__eyebrow" htmlFor={id}>
        Candidate {side}
      </label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        {candidates.map((c, index) => (
          <option key={c.id} value={c.id}>
            #{index + 1} · {profileLabel(c.profileName)} · {c.score.toFixed(2)}/100
          </option>
        ))}
      </select>

      {candidate && (
        <>
          <div className="h2h__figure">
            {candidate.score.toFixed(COMPARISON_DIGITS)}
            <small>/100</small>
          </div>
          <p className="rank__blurb">{profileBlurb(candidate.profileName) ?? candidate.id}</p>
          <div
            className="fingerprint"
            role="img"
            aria-label={candidate.subScores
              .map((s) => `${criterionLabel(s.criterion)} ${s.normalised.toFixed(2)}`)
              .join(', ')}
          >
            {candidate.subScores.map((sub) => (
              <span
                key={sub.criterion}
                className="fingerprint__bar"
                style={{ height: `${Math.max(6, Math.round(sub.normalised * 100))}%` }}
                title={`${sub.criterion} · ${criterionLabel(sub.criterion)} — ${sub.normalised.toFixed(3)}`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function formatSigned(value: number, digits: number): string {
  const fixed = value.toFixed(digits)
  const normalised = Number(fixed) === 0 ? (0).toFixed(digits) : fixed
  return Number(normalised) > 0 ? `+${normalised}` : normalised
}
