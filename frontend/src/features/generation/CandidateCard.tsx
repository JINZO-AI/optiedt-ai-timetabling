import type { Candidate, ConstraintDefinition } from '@/types/domain'

/**
 * FR-5 — one candidate, its overall score out of 100 and its seven sub-scores.
 *
 * ⚠️ Every figure here is rendered as the API sent it. Nothing on this page
 * computes a score, re-normalises a sub-score or decides an order — the
 * presentation layer may "display, filter, print, ask" and may not "compute a
 * score, decide an order" (docs/architecture.md). `rank` is the candidate's
 * position in the list the API returned, not a position this component worked
 * out.
 *
 * The criterion's raw value is shown beside its normalised value on purpose.
 * The normalised one is what the score is built from; the raw one is what a
 * head of department can recognise ("13 idle periods"), and dropping it would
 * leave the score defensible only in principle.
 */
export function CandidateCard({
  candidate,
  rank,
  catalogue,
  weights,
}: {
  candidate: Candidate
  rank: number
  catalogue: Map<string, ConstraintDefinition>
  weights: Record<string, number>
}) {
  return (
    <article className={`candidate${rank === 1 ? ' candidate--top' : ''}`}>
      <div className="candidate__head">
        <div>
          <div className="candidate__rank">Rang {rank}</div>
          <div className="candidate__profile">{candidate.profileName}</div>
        </div>
        <div className="candidate__score">
          {candidate.score.toFixed(2)}
          <span> /100</span>
        </div>
      </div>

      <table className="subscores">
        <thead>
          <tr>
            <th>Critère</th>
            <th>Poids</th>
            <th>Valeur</th>
            <th>Normalisé</th>
          </tr>
        </thead>
        <tbody>
          {candidate.subScores.map((sub) => {
            const definition = catalogue.get(sub.criterion)
            const weight = weights[sub.criterion]
            return (
              <tr key={sub.criterion}>
                <td>
                  {sub.criterion}
                  <span className="criterion-name"> {definition?.name ?? ''}</span>
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

      <div className="meta">
        <span>
          Séances placées <b>{candidate.placements.length}</b>
        </span>
      </div>
    </article>
  )
}

/** S6 is a sum of fractions; the rest are counts. Show each as it reads. */
function formatRaw(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}
