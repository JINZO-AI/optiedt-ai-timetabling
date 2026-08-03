import { roomOccupancy, type Lookups } from '@/features/timetable/model'
import type { Candidate, InstanceData } from '@/types/domain'

/**
 * FR-18 — occupancy of each classroom and laboratory, on one candidate.
 *
 * Grouped by room type because the types are not comparable: on the reference
 * instance the computer laboratories run far tighter than the classrooms, and
 * a single ranked list would read as "some rooms are busy" rather than as
 * "this type is the binding resource".
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
        Périodes occupées sur les {rows[0]?.openPeriods ?? 0} créneaux ouverts de la semaine. ⚠️ Ce
        taux compte des <em>périodes</em>. Pour les laboratoires, la borne qui contraint réellement
        est le nombre de fenêtres de deux périodes consécutives — lire le taux par période seul est
        ce qui a laissé passer une instance sans solution (C-13).
      </p>
      {[...byType.entries()].map(([type, group]) => (
        <div key={type} className="occupancy">
          <h3>{type}</h3>
          <table className="subscores">
            <thead>
              <tr>
                <th>Salle</th>
                <th>Périodes</th>
                <th>Ouvertes</th>
                <th>Taux</th>
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
