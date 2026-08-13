import type { ConstraintDefinition, DiagnosisResult } from '@/types/domain'

/**
 * FR-8 — the rules in conflict when no timetable exists.
 *
 * Three things this component is careful about, all of them ways a conflict
 * report can mislead while looking correct:
 *
 * 1. **It claims minimality only when the solver proved it.** Each rule is
 *    withdrawn and re-solved, so a set can be genuinely irreducible — but a
 *    withdrawal the solver could not decide keeps its rule for want of
 *    evidence, and then `isMinimal` is false and the wording says so (C-17).
 *
 * 2. **It never implies the named rules are the only possible explanation.**
 *    When two rules both forbid the same placement, either alone explains the
 *    conflict and the search reports one of them — the same one every time,
 *    because rules are withdrawn in catalogue order, but not the only true
 *    answer.
 *
 * 3. **An empty list is not reassurance.** Conclusive-and-empty means no
 *    relaxable rule explains the conflict, so the answer is in the data and
 *    the pre-analysis report. Inconclusive means the solver could not prove
 *    the infeasibility at all — which is NOT evidence the instance is sound.
 *    Presenting either as "no problem found" is the C-13 inference that cost
 *    three sessions.
 *
 * The catalogue supplies each code's name, so the report names a rule rather
 * than a code the reader has to look up.
 */
export function ConflictReport({
  diagnosis,
  catalogue,
}: {
  diagnosis: DiagnosisResult
  catalogue: Map<string, ConstraintDefinition>
}) {
  if (!diagnosis.isConclusive) {
    return (
      <>
        <p className="error">
          Diagnosis inconclusive: within the budget given, the solver neither found a timetable nor
          proved that none exists.
        </p>
        <p className="panel__note">
          ⚠️ This does not establish that the data is sound. An instance can have no solution at all
          without the solver being able to construct the proof — which is exactly what happened on
          C-13. Read the data checks above, then try again with a longer search.
        </p>
        <p className="panel__note">{diagnosis.detail}</p>
      </>
    )
  }

  if (diagnosis.conflictingCodes.length === 0) {
    return (
      <>
        <p className="warning">
          No withdrawable rule explains the conflict.
        </p>
        <p className="panel__note">
          Only H1, H3, H7 and H12 are posted constraints that can be withdrawn one at a time. H4 to
          H6 and H8 to H10 restrict a variable's domain before the search even begins, so they
          cannot be relaxed. The conflict is therefore in the data — the checks above name the
          resource and the quantity that is missing.
        </p>
        <p className="panel__note">{diagnosis.detail}</p>
      </>
    )
  }

  return (
    <>
      <p className="error">
        No timetable exists. The rules below are enough to explain the conflict.
      </p>

      <ul className="conflicts">
        {diagnosis.conflictingCodes.map((code) => (
          <li key={code}>
            <b>{code}</b>
            {catalogue.get(code) ? ` — ${catalogue.get(code)?.name}` : null}
          </li>
        ))}
      </ul>

      {diagnosis.isMinimal ? (
        <p className="panel__note">
          <b>Minimal</b> set: each rule was withdrawn and the model re-solved. Removing any one of
          them makes the instance solvable, and every other withdrawable rule was removed without
          lifting the conflict. ⚠️ Minimal among the four withdrawable rules only — H4 to H6 and H8
          to H10 restrict the domain before
          the search begins and are always in force.
        </p>
      ) : (
        <p className="warning">
          ⚠️ <b>Sufficient but not minimal</b>: at least one removal could not be decided within
          the budget given, so that rule was kept for want of proof rather than because it turned
          out to be necessary. Increase the search budget
          to narrow the diagnosis.
        </p>
      )}

      <p className="panel__note">
        ⚠️ When two rules forbid the same placement, either one on its own explains the conflict.
        The report names one of them, always the same one — rules are withdrawn in catalogue order —
        but that is not the only true answer.
      </p>
    </>
  )
}
