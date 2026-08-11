import { roomOccupancy, type Lookups } from '@/features/timetable/model'
import type { Candidate, InstanceData } from '@/types/domain'

/**
 * FR-18 — occupancy of each classroom and laboratory, on one candidate.
 *
 *     Criterion (project decision, C-9 resolved 2026-08-11 — derived from
 *     repository evidence and engineering research because supervisor
 *     clarification was unavailable):
 *     "An authorised user can consult, for EACH classroom and EACH laboratory,
 *     the share of the week's open periods it occupies on a given candidate."
 *
 * ⚠️ **The quantity is `occupied periods / open periods`, and it is not this
 * screen's invention.** It is `utilisation(r,k)` as C-4 defined it on
 * 2026-07-30 for S6, implemented in `analysis/criteria.py` and again in
 * `solver/objective.py`. This view and that criterion must agree; if the
 * formula here ever changes, S6 is measuring something else from the same
 * placements.
 *
 * ⚠️ **It measures TIME, not seats, and the label says so.** In the SMG "UFO"
 * vocabulary standard in higher-education space management, this is a
 * *frequency* rate and "occupancy" means occupants over capacity. The two
 * readings **invert** on this instance — Salle is the emptiest by time and the
 * fullest by seats — so an unqualified "Taux" would be actively misleading to
 * a reader who knows that vocabulary. C-9 records why the time reading is the
 * right one for FR-18: SRS Table 36 puts FR-18 among the *views*.
 *
 * Grouped by room type because the types are not comparable: on the reference
 * instance the computer laboratories run far tighter than the classrooms, and
 * a single ranked list would read as "some rooms are busy" rather than as
 * "this type is the binding resource".
 *
 * ⚠️ **Every room appears, including one no session was placed in.** A room at
 * 0 % is the most actionable row in the table, and a view that silently
 * omitted it would answer "which rooms are used?" while appearing to answer
 * "how is each room used?" — which is what the criterion asks.
 */
export function OccupancyView({
  candidate,
  instance,
  lookups,
}: {
  candidate: Candidate
  instance: InstanceData
  lookups: Lookups
}) {
  const rows = roomOccupancy(candidate, instance, lookups)
  const byType = new Map<string, typeof rows>()
  for (const row of rows) {
    const existing = byType.get(row.type)
    if (existing) existing.push(row)
    else byType.set(row.type, [row])
  }

  return (
    <>
      <p className="panel__note">
        <b>Taux d’occupation = périodes occupées / {rows[0]?.openPeriods ?? 0} créneaux ouverts</b> de
        la semaine. ⚠️ Il mesure le <em>temps</em> d’utilisation, et non le remplissage en places : une
        salle peu occupée dans le temps peut être pleine à chaque séance. Pour les laboratoires, la
        borne qui contraint réellement est le nombre de fenêtres de deux périodes consécutives — lire
        le taux par période seul est ce qui a laissé passer une instance sans solution (C-13).
      </p>
      {[...byType.entries()].map(([type, group]) => (
        <div key={type} className="occupancy">
          <h3>{type}</h3>
          <table className="subscores">
            <thead>
              <tr>
                <th>Salle</th>
                <th>Périodes occupées</th>
                <th>Créneaux ouverts</th>
                <th>Taux d’occupation</th>
              </tr>
            </thead>
            <tbody>
              {group.map((row) => (
                <tr key={row.roomId}>
                  <td>{row.code}</td>
                  <td>{row.occupiedPeriods}</td>
                  <td>{row.openPeriods}</td>
                  <td>
                    {(row.ratio * 100).toFixed(1)} %
                    <span className="bar__track">
                      <span
                        className="bar"
                        style={{ width: `${Math.min(100, Math.round(row.ratio * 100))}%` }}
                      />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </>
  )
}
