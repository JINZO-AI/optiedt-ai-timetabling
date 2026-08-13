import { criterionLabel } from '@/labels'
import type { ConstraintDefinition, Decomposition } from '@/types/domain'

/**
 * FR-15 — the decomposition ledger: the difference between two candidates,
 * criterion by criterion.
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
 * ⚠️ **This component must never summarise, re-order by magnitude or drop a
 * near-zero term**: a row missing from the table is a term missing from an
 * equation the department is invited to check by hand. The bars are drawn in
 * the order the API returned, for exactly that reason — sorting them would be
 * the most tempting "improvement" here and it would break the correspondence
 * between this table and the equation above.
 *
 * ⚠️ **The bars compute nothing.** Each width is a percentage of the largest
 * displayed magnitude — typography applied to a figure the analysis layer
 * already produced. The number beside it, not the bar, is the value.
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

  // The scale of the plot. One shared maximum, so a bar twice as long is a
  // term twice as large — per-row scaling would make every criterion look
  // equally decisive.
  const widest = Math.max(...displayed.map((v) => Math.abs(v)), Number.MIN_VALUE)

  const total = displayed.reduce((sum, value) => sum + value, 0)
  const balances = formatSigned(total, digits) === formatSigned(decomposition.scoreDifference, digits)

  // ⚠️ **Reading the largest and smallest term off a list is FILTERING, not
  // computing** — the same licence the presentation layer has to sort, print
  // and select (`docs/architecture.md`). Every figure below is one the
  // analysis layer produced; nothing here derives a new one. It exists because
  // "which criterion actually separates these two" is the question a head of
  // department asks first, and making them find it by eye down a seven-row
  // table is making them do the interface's job.
  const ranked = decomposition.contributions
    .map((c, index) => ({ c, value: displayed[index] ?? 0 }))
    .filter((t) => t.value !== 0)
    .sort((a, b) => b.value - a.value)
  const best = ranked[0]
  const worst = ranked[ranked.length - 1]

  return (
    <>
      {best !== undefined && worst !== undefined && best !== worst && (
        <div className="ledger-highlights">
          <Highlight
            direction="up"
            label="A gains most on"
            term={best}
            catalogue={catalogue}
            digits={digits}
          />
          <Highlight
            direction="down"
            label="A loses most on"
            term={worst}
            catalogue={catalogue}
            digits={digits}
          />
        </div>
      )}

      <div className="table-scroll">
        <table className="subscores ledger">
          <thead>
            <tr>
              <th scope="col">Criterion</th>
              <th scope="col">Weight</th>
              <th scope="col">n(A)</th>
              <th scope="col">n(B)</th>
              <th scope="col" className="ledger__axis-head">
                <span>◄ B better</span>
                <span>A better ►</span>
              </th>
              <th scope="col">Contribution</th>
            </tr>
          </thead>
          <tbody>
            {decomposition.contributions.map((c, index) => {
              const value = displayed[index] ?? 0
              const width = (Math.abs(value) / widest) * 100
              return (
                <tr key={c.criterion}>
                  <td className="ledger__label">
                    <span className="code">{c.criterion}</span>
                    <span className="criterion-name">
                      {' '}
                      {catalogue.get(c.criterion)?.name ?? criterionLabel(c.criterion)}
                    </span>
                  </td>
                  <td>{c.weight.toFixed(2)}</td>
                  <td>{c.normalisedA.toFixed(3)}</td>
                  <td>{c.normalisedB.toFixed(3)}</td>
                  <td className="ledger__cell">
                    <span className="ledger__plot">
                      {value !== 0 && (
                        <span
                          className={`ledger__bar ledger__bar--${value > 0 ? 'pos' : 'neg'}`}
                          style={{ width: `${width / 2}%` }}
                        />
                      )}
                    </span>
                  </td>
                  <td
                    className={c.value >= 0 ? 'gain' : 'loss'}
                    data-testid={`contribution-${c.criterion}`}
                  >
                    {formatSigned(value, digits)}
                  </td>
                </tr>
              )
            })}
          </tbody>
          <tfoot>
            <tr className="ledger__total">
              <th colSpan={4} scope="row">
                Sum of contributions
              </th>
              <td className="ledger__cell" />
              <td data-testid="contributions-total">{formatSigned(total, digits)}</td>
            </tr>
            <tr className="ledger__total">
              <th colSpan={4} scope="row">
                Difference in score
              </th>
              <td className="ledger__cell" />
              <td data-testid="score-difference">
                {formatSigned(decomposition.scoreDifference, digits)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* ⚠️ The identity is stated on screen rather than only in the
          documentation, because it is the reason the ranking is defensible in
          front of a department. It is read from the two figures above, not
          asserted. */}
      <p className={`ledger__identity${balances ? '' : ' ledger__identity--off'}`}>
        {balances ? '✓' : '✗'} Σ contributions = Δ score, exactly, at {digits} decimals
      </p>
    </>
  )
}

/**
 * The single term that most separates the two candidates, in one direction.
 *
 * ⚠️ Worded as an observation about the table below it, never as a verdict.
 * "A gains most on S7" is something the reader can check in two seconds; "A is
 * better for subject spread" would be a claim the decomposition does not make.
 */
function Highlight({
  direction,
  label,
  term,
  catalogue,
  digits,
}: {
  direction: 'up' | 'down'
  label: string
  term: { c: { criterion: string }; value: number }
  catalogue: Map<string, ConstraintDefinition>
  digits: number
}) {
  return (
    <p className={`ledger-highlight ledger-highlight--${direction}`}>
      <span className="ledger-highlight__label">{label}</span>
      <span className="code">{term.c.criterion}</span>
      <span className="ledger-highlight__name">
        {catalogue.get(term.c.criterion)?.name ?? criterionLabel(term.c.criterion)}
      </span>
      <span className={`ledger-highlight__value ${term.value > 0 ? 'gain' : 'loss'}`}>
        {formatSigned(term.value, digits)}
      </span>
    </p>
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
