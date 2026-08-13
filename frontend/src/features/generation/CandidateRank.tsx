import { useState } from 'react'

import { criterionLabel, profileBlurb, profileLabel } from '@/labels'
import type { Candidate, ConstraintDefinition } from '@/types/domain'

/**
 * FR-5 and FR-6 — the portfolio, ranked, in one scannable list.
 *
 * ⚠️ **Nothing here computes a score, re-normalises a sub-score or decides an
 * order.** `rank` is the candidate's position in the list the API returned, and
 * every figure is rendered as the API sent it — the presentation layer may
 * "display, filter, print, ask" and may not "compute a score, decide an order"
 * (`docs/architecture.md`). The bar widths are pixels derived from values the
 * server already normalised; they are typography, not arithmetic.
 *
 * ⚠️ **The fingerprint is the reason this is a list and not three cards.** Two
 * candidates can score within a tenth of each other and get there completely
 * differently — that is the whole point of solving three profiles. Seven bars
 * per row makes the difference visible before a single number is read, and the
 * table underneath is one press away for the reader who wants the terms.
 */
export function CandidateRank({
  candidates,
  catalogue,
  weights,
  onPublish,
  publishing,
  publishedId,
}: {
  candidates: Candidate[]
  catalogue: Map<string, ConstraintDefinition>
  weights: Record<string, number>
  onPublish?: (candidateId: string) => void
  publishing?: string | null
  publishedId?: string | null
}) {
  const [open, setOpen] = useState<string | null>(null)

  return (
    <div className="rank-list">
      {candidates.map((candidate, index) => {
        const rank = index + 1
        const expanded = open === candidate.id
        return (
          <article
            key={candidate.id}
            className={`rank${rank === 1 ? ' rank--top' : ''}${expanded ? ' rank--open' : ''}`}
          >
            <div className="rank__row">
              <div className="rank__num" aria-label={`Rank ${rank}`}>
                {rank}
              </div>

              <div className="rank__id">
                <div className="rank__profile">
                  {profileLabel(candidate.profileName)}
                  {rank === 1 && <span className="rank__lead">Top ranked</span>}
                  {publishedId === candidate.id && <span className="badge badge--ok">Published</span>}
                </div>
                <div className="rank__blurb">{profileBlurb(candidate.profileName) ?? candidate.id}</div>
              </div>

              <Fingerprint candidate={candidate} />

              <div className="rank__score">
                {candidate.score.toFixed(2)}
                <small>/100</small>
              </div>

              <div className="rank__actions">
                <button
                  type="button"
                  className="ghost button--sm"
                  aria-expanded={expanded}
                  onClick={() => setOpen(expanded ? null : candidate.id)}
                >
                  {expanded ? 'Hide terms' : 'Show terms'}
                </button>
                {onPublish && (
                  <button
                    type="button"
                    className="secondary button--sm"
                    disabled={publishing !== null && publishing !== undefined}
                    onClick={() => onPublish(candidate.id)}
                  >
                    {publishing === candidate.id ? 'Publishing…' : 'Publish'}
                  </button>
                )}
              </div>
            </div>

            {expanded && (
              <div className="rank__detail">
                {/* The raw value sits beside the normalised one on purpose. The
                    normalised one is what the score is built from; the raw one
                    is what a head of department recognises ("13 idle
                    periods"), and dropping it would leave the score defensible
                    only in principle. */}
                <table className="subscores">
                  <thead>
                    <tr>
                      <th>Criterion</th>
                      <th>Weight</th>
                      <th>Measured</th>
                      <th>Normalised</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidate.subScores.map((sub) => {
                      const weight = weights[sub.criterion]
                      return (
                        <tr key={sub.criterion}>
                          <td>
                            <span className="code">{sub.criterion}</span>
                            <span className="criterion-name">
                              {' '}
                              {catalogue.get(sub.criterion)?.name ?? criterionLabel(sub.criterion)}
                            </span>
                          </td>
                          <td>{weight === undefined ? '—' : weight.toFixed(2)}</td>
                          <td>{formatRaw(sub.rawValue)}</td>
                          <td>
                            {sub.normalised.toFixed(3)}
                            <span className="bar__track">
                              <span
                                className="bar"
                                style={{ width: `${Math.round(sub.normalised * 100)}%` }}
                              />
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>

                <p className="hint rank__foot">
                  <span className="code">{candidate.id}</span> · {candidate.placements.length}{' '}
                  sessions placed · scored under the run's weights in force, so every candidate is
                  priced alike
                </p>
              </div>
            )}
          </article>
        )
      })}
    </div>
  )
}

/**
 * Seven bars, one per soft criterion, each as tall as its normalised value.
 *
 * ⚠️ Redundant with the table below it, deliberately: the bars are for
 * comparing candidates at a glance, the table for checking one of them. A
 * reader who cannot use the bars loses nothing.
 */
function Fingerprint({ candidate }: { candidate: Candidate }) {
  return (
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
  )
}

/** S6 is a sum of fractions; the rest are counts. Show each as it reads. */
function formatRaw(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}
