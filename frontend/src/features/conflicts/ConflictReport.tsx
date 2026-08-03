import type { ConstraintDefinition, DiagnosisResult } from '@/types/domain'

/**
 * FR-8 — the rules in conflict when no timetable exists.
 *
 * Three things this component is careful about, all of them ways a conflict
 * report can mislead while looking correct:
 *
 * 1. **It never says "the smallest set".** The subset CP-SAT returns is
 *    heuristically reduced. The wording is "sufficient to explain", which is
 *    what `docs/architecture.md` requires of the interface.
 *
 * 2. **It never says "change these and it will solve".** The codes are an
 *    unsat core — enforcing exactly those rules already admits no timetable —
 *    not a repair list. Relaxing them need not make the instance solvable,
 *    because other rules may forbid the same placements.
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

      <p className="panel__note">
        ⚠️ Ensemble <b>suffisant</b>, et non le plus petit : le sous-ensemble renvoyé par le
        solveur est réduit heuristiquement, sans garantie de minimalité. Imposer ces seules règles,
        toutes les autres étant mises de côté, suffit déjà à rendre l’instance insoluble — ce n’est
        donc pas une liste de réparations : les modifier est nécessaire, pas nécessairement
        suffisant.
      </p>
    </>
  )
}
