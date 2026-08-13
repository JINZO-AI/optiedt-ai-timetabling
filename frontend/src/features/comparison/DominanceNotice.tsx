import type { Candidate, DominanceVerdict } from '@/types/domain'

/**
 * FR-17 — a candidate another improves on across the board.
 *
 * Built in Phase 6 M1, once **C-14** was resolved. Phase 4 deliberately shipped
 * no dominance signal at all, because under the reading then in force the only
 * signal the specification described — "a dominated **top** candidate" — is
 * provably unreachable, and a control that never fires teaches the reader it
 * means "no problem found".
 *
 * Three things this component is careful about:
 *
 * 1. **It reports dominance anywhere in the portfolio**, not at its head. The
 *    top-ranked candidate can never be dominated (a dominated candidate cannot
 *    outscore its dominator), so a signal attached to it would be permanently
 *    silent. A dominated runner-up is ordinary.
 *
 * 2. **An empty result says what was checked.** "No candidate is dominated" is
 *    a finding; blank space is not. The rule is restated on screen so the
 *    reader can tell the two apart — the same discipline as ConflictReport and
 *    PreAnalysisReport.
 *
 * 3. **It states the rule rather than a verdict alone.** Dominance is exact and
 *    needs no weights, which is exactly what makes it a useful complement to
 *    the weighted sum (ADR-002) — and a reader who does not know that cannot
 *    tell it apart from a second opinion about the score.
 */
export function DominanceNotice({
  verdicts,
  candidates,
  compared,
}: {
  verdicts: DominanceVerdict[]
  candidates: Candidate[]
  /** The two candidates on screen, so the notice can say whether they are involved. */
  compared: readonly [string, string]
}) {
  const dominated = verdicts.filter((v) => v.dominatedBy !== null)
  const rankOf = new Map(candidates.map((c, index) => [c.id, index + 1]))
  const label = (id: string) => {
    const rank = rankOf.get(id)
    return rank === undefined ? id : `${id} (rang ${rank})`
  }

  const rule = (
    <p className="panel__note">
      A candidate is <b>dominated</b> when another does at least as well on <b>every</b> one of the
      seven criteria and strictly better on at least one. This test is exact and uses no weights:
      it complements the weighted score, it does not replace it.
    </p>
  )

  if (dominated.length === 0) {
    return (
      <>
        <p className="panel__note">
          <b>No candidate in this run is dominated.</b> Each one wins on at least one criterion:
          the ranking is settling a genuine trade-off, not concealing one.
        </p>
        {rule}
      </>
    )
  }

  const onScreen = dominated.filter((v) => compared.includes(v.candidate))

  return (
    <>
      <p className="warning">
        {dominated.length === 1
          ? '1 candidate is dominated.'
          : `${dominated.length} candidates are dominated.`}{' '}
        Another candidate beats them on every criterion at once.
      </p>

      <ul className="conflicts">
        {dominated.map((v) => (
          <li key={v.candidate}>
            <b>{label(v.candidate)}</b> is dominated by <b>{label(v.dominatedBy as string)}</b>
            {compared.includes(v.candidate) ? ' — shown below' : null}
          </li>
        ))}
      </ul>

      {onScreen.length === 0 && (
        <p className="panel__note">
          Neither of the two candidates compared here is affected; the finding concerns the rest of
          the portfolio.
        </p>
      )}

      {rule}

      <p className="panel__note">
        ⚠️ The top-ranked candidate is never dominated, and that is not an observation: a dominated
        candidate cannot score higher than the one dominating it. So do not read the absence of a
        signal on the first rank as a result.
      </p>
    </>
  )
}
