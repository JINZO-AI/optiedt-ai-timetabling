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
      Un candidat est <b>dominé</b> lorsqu’un autre fait au moins aussi bien sur{' '}
      <b>chacun</b> des sept critères et strictement mieux sur au moins un. Ce test est exact et
      n’utilise aucun poids : il complète le score pondéré, il ne le remplace pas.
    </p>
  )

  if (dominated.length === 0) {
    return (
      <>
        <p className="panel__note">
          <b>Aucun candidat de cette exécution n’est dominé.</b> Chacun l’emporte sur au moins un
          critère : le classement arbitre un compromis réel, il n’en dissimule pas un.
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
          ? '1 candidat est dominé.'
          : `${dominated.length} candidats sont dominés.`}{' '}
        Un autre candidat leur est supérieur sur tous les critères à la fois.
      </p>

      <ul className="conflicts">
        {dominated.map((v) => (
          <li key={v.candidate}>
            <b>{label(v.candidate)}</b> est dominé par <b>{label(v.dominatedBy as string)}</b>
            {compared.includes(v.candidate) ? ' — affiché ci-dessous' : null}
          </li>
        ))}
      </ul>

      {onScreen.length === 0 && (
        <p className="panel__note">
          Aucun des deux candidats comparés ici n’est concerné ; la constatation porte sur le reste
          du portefeuille.
        </p>
      )}

      {rule}

      <p className="panel__note">
        ⚠️ Le candidat de tête n’est jamais dominé, et ce n’est pas une observation : un candidat
        dominé ne peut pas obtenir un score supérieur à celui qui le domine. Ne lisez donc pas
        l’absence de signal sur le premier rang comme un résultat.
      </p>
    </>
  )
}
