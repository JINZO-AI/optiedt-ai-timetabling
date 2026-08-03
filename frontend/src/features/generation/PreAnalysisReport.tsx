import type { CheckResult } from '@/types/domain'

/**
 * FR-12 — the five structural checks, as the run recorded them.
 *
 * ⚠️ **The figures are shown whether or not a check passed**, and that is the
 * whole design of this component. Computer laboratories sit at 90.9 % of their
 * two-period windows — 8 spare in the entire week — while the period figure
 * reads a comfortable 71 %. Both numbers are true; only one determines whether
 * a timetable exists. A report that collapsed to five green ticks would hide
 * the one that binds, which is exactly the reading error that cost three
 * sessions on C-13.
 *
 * A failing check names the resource and the quantity missing, never a bare
 * boolean — that named detail is the content the requirement asks for.
 *
 * This component decides nothing. It renders what `GET /runs/{id}` returned;
 * the arithmetic is `optiedt.preanalysis`, server-side, and no figure here is
 * computed in the browser.
 */
export function PreAnalysisReport({ checks }: { checks: CheckResult[] }) {
  if (checks.length === 0) {
    // ⚠️ Not "everything is fine". An empty list means the stage did not run —
    // a run still PENDING, or one that failed before stage 1.
    return (
      <p className="panel__note">
        Vérification préalable non exécutée pour cette exécution.
      </p>
    )
  }

  const failed = checks.filter((c) => !c.passed)

  return (
    <>
      {failed.length > 0 ? (
        <p className="error">
          {failed.length} vérification(s) en échec. Une couverture de créneaux en échec est une
          preuve par tiroirs qu’aucun emploi du temps n’existe : ce n’est pas une question de
          performance du solveur.
        </p>
      ) : (
        <p className="panel__note">
          Les cinq vérifications passent. Réussir n’est pas être à l’aise : lisez la ressource
          contraignante ci-dessous.
        </p>
      )}

      <table className="checks">
        <thead>
          <tr>
            <th scope="col">Vérification</th>
            <th scope="col">Résultat</th>
            <th scope="col">Ressource</th>
            <th scope="col">Manquant</th>
            <th scope="col">Détail</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((check) => (
            <tr key={check.name} className={check.passed ? undefined : 'checks__row--failed'}>
              <th scope="row">{LABELS[check.name] ?? check.name}</th>
              <td>
                <span className={`state state--${check.passed ? 'done' : 'bad'}`}>
                  {check.passed ? 'OK' : 'ÉCHEC'}
                </span>
              </td>
              <td>{check.resource ?? '—'}</td>
              <td className="num">
                {check.missingQuantity === null ? '—' : check.missingQuantity}
              </td>
              <td className="checks__detail">{check.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}

/**
 * French labels for the five codes. The CODE is what the API sends and what
 * the documentation names, so it is kept as the fallback rather than mapped
 * away — an unknown code must show as itself, not vanish.
 */
const LABELS: Record<string, string> = {
  ROOM_SUITABILITY: 'Salle adaptée pour chaque séance',
  SLOT_COVERAGE: 'Couverture des créneaux par type de salle',
  TEACHER_LOAD: 'Charge maximale par grade',
  TEACHER_FREE_SLOTS: 'Créneaux libres suffisants par enseignant',
  GROUP_HIERARCHY: 'Cohérence de la hiérarchie des groupes',
}
