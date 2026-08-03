import type { ConstraintDefinition, Decomposition } from '@/types/domain'

/**
 * FR-15 — the difference between two candidates, criterion by criterion.
 *
 * ⚠️ **This table IS the score calculation, read term by term.** It is not a
 * summary of it and not an explanation constructed after the fact:
 *
 *     score(A) − score(B) = 100 × Σ ( w_i × ( n_i(A) − n_i(B) ) )
 *
 * so every term is shown — the weight, both normalised values, and the
 * resulting contribution — and the column is totalled, because the acceptance
 * criterion is that the displayed contributions **sum to the displayed score
 * difference, to the precision of the display**.
 *
 * This component must never summarise, re-order by magnitude or drop a
 * near-zero term: a row missing from the table is a term missing from an
 * equation the department is invited to check by hand.
 */
export function ContributionsTable({
  decomposition,
  catalogue,
  digits = 2,
}: {
  decomposition: Decomposition
  catalogue: Map<string, ConstraintDefinition>
  digits?: number
}) {
  const displayed = roundPreservingSum(
    decomposition.contributions.map((c) => c.value),
    decomposition.scoreDifference,
    digits,
  )

  return (
    <table className="subscores contributions">
      <thead>
        <tr>
          <th>Critère</th>
          <th>Poids</th>
          <th>n(A)</th>
          <th>n(B)</th>
          <th>Contribution</th>
        </tr>
      </thead>
      <tbody>
        {decomposition.contributions.map((c, index) => (
          <tr key={c.criterion}>
            <td>
              {c.criterion}
              <span className="criterion-name"> {catalogue.get(c.criterion)?.name ?? ''}</span>
            </td>
            <td>{c.weight.toFixed(2)}</td>
            <td>{c.normalisedA.toFixed(3)}</td>
            <td>{c.normalisedB.toFixed(3)}</td>
            <td
              className={c.value >= 0 ? 'gain' : 'loss'}
              data-testid={`contribution-${c.criterion}`}
            >
              {formatSigned(displayed[index] ?? 0, digits)}
            </td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <th colSpan={4}>Somme des contributions</th>
          <td data-testid="contributions-total">
            {formatSigned(
              displayed.reduce((total, value) => total + value, 0),
              digits,
            )}
          </td>
        </tr>
        <tr>
          <th colSpan={4}>Différence des scores</th>
          <td data-testid="score-difference">
            {formatSigned(decomposition.scoreDifference, digits)}
          </td>
        </tr>
      </tfoot>
    </table>
  )
}

/**
 * Round each term so the terms still add up to the rounded total.
 *
 * ⚠️ Rounding each contribution independently does **not** preserve the sum,
 * and the acceptance criterion is about what is *displayed*. A worked case
 * from the reference instance: contributions of 2.7567 and −3.6663 sum to
 * −0.9096. At three decimals the terms show 2.757 and −3.666, summing to
 * −0.909, while the true difference shows −0.910. The table would then fail to
 * add up by one unit of the last place — in front of a reader specifically
 * invited to check it by hand.
 *
 * The largest-remainder method fixes that: floor every term, then hand the
 * leftover units to the terms whose discarded remainders were biggest. Each
 * displayed term stays within one unit of the last place of its true value —
 * which is what "to the precision of the display" allows — and the column adds
 * up exactly.
 *
 * This is a **display** device and nothing more. No stored figure is altered,
 * and the underlying contributions remain exactly what the analysis layer
 * computed; the API is still the authority on every number here.
 */
export function roundPreservingSum(
  values: number[],
  target: number,
  digits: number,
): number[] {
  const scale = 10 ** digits
  const scaled = values.map((v) => v * scale)
  const floors = scaled.map((v) => Math.floor(v))
  const targetUnits = Math.round(target * scale)

  let deficit = targetUnits - floors.reduce((total, unit) => total + unit, 0)
  const byRemainder = scaled
    .map((value, index) => ({ index, remainder: value - Math.floor(value) }))
    .sort((a, b) => b.remainder - a.remainder)

  // deficit is bounded by the number of terms, since every remainder is < 1:
  // the biggest remainders round up, the smallest round down.
  const adjustment = new Map<number, number>()
  for (let k = 0; deficit > 0 && k < byRemainder.length; k += 1, deficit -= 1) {
    const term = byRemainder[k]
    if (term) adjustment.set(term.index, 1)
  }
  for (let k = byRemainder.length - 1; deficit < 0 && k >= 0; k -= 1, deficit += 1) {
    const term = byRemainder[k]
    if (term) adjustment.set(term.index, -1)
  }

  return floors.map((unit, index) => (unit + (adjustment.get(index) ?? 0)) / scale)
}

/** A signed figure, so a contribution's direction is readable at a glance. */
function formatSigned(value: number, digits: number): string {
  const fixed = value.toFixed(digits)
  // toFixed can produce "-0.00", which reads as a loss that did not happen.
  const normalised = Number(fixed) === 0 ? (0).toFixed(digits) : fixed
  return Number(normalised) > 0 ? `+${normalised}` : normalised
}
