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
          Diagnostic non concluant : le solveur n’a ni trouvé d’emploi du temps ni prouvé qu’il
          n’en existe aucun dans le budget accordé.
        </p>
        <p className="panel__note">
          ⚠️ Ceci n’établit pas que l’instance est saine. Une instance peut n’admettre aucune
          solution sans que les propagateurs puissent en construire la preuve — c’est exactement
          ce qui s’est produit sur C-13. Lisez la vérification préalable ci-dessus, puis relancez
          avec un budget déterministe plus élevé.
        </p>
        <p className="panel__note">{diagnosis.detail}</p>
      </>
    )
  }

  if (diagnosis.conflictingCodes.length === 0) {
    return (
      <>
        <p className="warning">
          Aucune règle relaxable n’explique le conflit.
        </p>
        <p className="panel__note">
          Seules H1, H3, H7 et H12 sont des contraintes posées auxquelles une hypothèse peut être
          attachée. H4 à H6 et H8 à H10 restreignent le domaine d’une variable avant même le début
          de la recherche : elles ne peuvent pas être relaxées. Le conflit est donc dans les
          données — la vérification préalable ci-dessus nomme la ressource et la quantité
          manquante.
        </p>
        <p className="panel__note">{diagnosis.detail}</p>
      </>
    )
  }

  return (
    <>
      <p className="error">
        Aucun emploi du temps n’existe. Les règles suivantes suffisent à expliquer le conflit.
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
          Ensemble <b>minimal</b> : chaque règle a été retirée puis le modèle résolu à nouveau.
          Retirer l’une quelconque d’entre elles suffit à rendre l’instance solvable, et toutes
          les autres règles retirables l’ont été sans lever le conflit. ⚠️ Minimal parmi les
          quatre règles retirables seulement — H4 à H6 et H8 à H10 restreignent le domaine avant
          la recherche et restent toujours en vigueur.
        </p>
      ) : (
        <p className="warning">
          ⚠️ Ensemble <b>suffisant mais non minimal</b> : le retrait d’au moins une règle n’a pas
          pu être tranché dans le budget accordé, et cette règle a donc été conservée faute de
          preuve, non parce qu’elle s’est révélée nécessaire. Augmentez le budget déterministe
          pour resserrer le diagnostic.
        </p>
      )}

      <p className="panel__note">
        ⚠️ Lorsque deux règles interdisent le même placement, chacune suffit à elle seule à
        expliquer le conflit : le rapport en nomme une, toujours la même — les règles sont
        retirées dans l’ordre du catalogue — mais ce n’est pas la seule réponse vraie.
      </p>
    </>
  )
}
