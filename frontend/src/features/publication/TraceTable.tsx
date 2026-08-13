import type { PublishedTimetable } from '@/types/domain'

/**
 * The trace behind a published timetable — the acceptance criterion, displayed.
 *
 *     Every published timetable traces back to its run, seed and weights.
 *
 * ⚠️ **Every field here is shown, not summarised.** "Published on 4 August by
 * the person in charge" satisfies nobody who has to re-derive the timetable a
 * year later; the run id, the seed, the model version and the full weight
 * vector are what make that possible, so all four are on screen.
 *
 * ⚠️ **`deterministicBudget` is not a duration.** It is deterministic time
 * (ADR-011); rendering it as seconds would state a promise the system does not
 * make, since the wall-clock cost of one unit is machine-dependent.
 *
 * This component computes nothing. Every figure arrives already assembled by
 * the API from the run record.
 */
export function TraceTable({ published }: { published: PublishedTimetable }) {
  const weights = Object.entries(published.weights).sort(([a], [b]) => a.localeCompare(b))

  return (
    <table className="trace">
      <tbody>
        <tr>
          <th scope="row">Run</th>
          <td className="num">{published.run}</td>
        </tr>
        <tr>
          <th scope="row">Candidate</th>
          <td className="num">
            {published.candidate.id} — profile {published.candidate.profileName}
          </td>
        </tr>
        <tr>
          <th scope="row">Seed</th>
          <td className="num">{published.seed}</td>
        </tr>
        <tr>
          <th scope="row">Search budget</th>
          <td className="num">
            {published.deterministicBudget} <span className="hint">(deterministic units, not seconds)</span>
          </td>
        </tr>
        <tr>
          <th scope="row">Model version</th>
          <td className="num">{published.modelVersion}</td>
        </tr>
        <tr>
          <th scope="row">Weights in force</th>
          <td className="num">
            {weights.map(([code, weight]) => `${code} ${weight}`).join(' · ')}
          </td>
        </tr>
        <tr>
          <th scope="row">Published on</th>
          <td className="num">
            {published.publishedAt} by {published.publishedBy}
          </td>
        </tr>
      </tbody>
    </table>
  )
}
