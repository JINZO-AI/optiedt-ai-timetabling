import { useMemo, useState } from 'react'

import { useInstance, useRun, useRuns } from '@/api/queries'
import { OccupancyView } from '@/features/timetable/OccupancyView'
import { TimetableGrid } from '@/features/timetable/TimetableGrid'
import { buildLookups, placementsFor, type Dimension } from '@/features/timetable/model'

type View = Dimension | 'occupancy'

const VIEW_LABELS: Record<View, string> = {
  teacher: 'Par enseignant',
  group: 'Par groupe',
  room: 'Par salle',
  occupancy: 'Occupation des salles',
}

/**
 * FR-7 and FR-18 — the four views of a candidate.
 *
 * A run is chosen rather than assumed: a candidate is immutable and belongs to
 * the run that produced it (invariant 6), so a view is always "this timetable,
 * from that run", never a free-floating timetable.
 */
export function TimetableScreen() {
  const runs = useRuns()
  const instance = useInstance()

  const completed = (runs.data ?? []).filter((r) => r.candidateCount > 0)
  const [runId, setRunId] = useState<string | null>(null)
  const selectedRunId = runId ?? completed[0]?.id ?? null
  const run = useRun(selectedRunId)

  const [candidateId, setCandidateId] = useState<string | null>(null)
  const candidates = run.data?.candidates ?? []
  const candidate = candidates.find((c) => c.id === candidateId) ?? candidates[0]

  const [view, setView] = useState<View>('group')
  const [resourceId, setResourceId] = useState<string | null>(null)

  const lookups = useMemo(
    () => (instance.data ? buildLookups(instance.data) : null),
    [instance.data],
  )

  if (instance.isLoading || runs.isLoading) return <p className="empty">Chargement…</p>
  if (!instance.data || !lookups) return <p className="error">Instance indisponible.</p>
  if (completed.length === 0)
    return (
      <p className="empty">
        Aucune exécution ne comporte de candidat. Lancez une génération d’abord.
      </p>
    )

  const resources =
    view === 'teacher'
      ? instance.data.teachers.map((t) => ({ id: t.id, label: `${t.id} — ${t.rank}` }))
      : view === 'group'
        ? instance.data.groups.map((g) => ({ id: g.id, label: `${g.label} (${g.level})` }))
        : view === 'room'
          ? instance.data.rooms.map((r) => ({ id: r.id, label: `${r.code} — ${r.type}` }))
          : []

  const selectedResource = resourceId ?? resources[0]?.id ?? null

  return (
    <>
      <section className="panel">
        <h1>Emplois du temps</h1>

        <div className="form-row">
          <div className="field">
            <label htmlFor="run">Exécution</label>
            <select
              id="run"
              value={selectedRunId ?? ''}
              onChange={(e) => {
                setRunId(e.target.value)
                setCandidateId(null)
              }}
            >
              {completed.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.id} — {r.candidateCount} candidat(s)
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label htmlFor="candidate">Candidat</label>
            <select
              id="candidate"
              value={candidate?.id ?? ''}
              onChange={(e) => setCandidateId(e.target.value)}
            >
              {candidates.map((c, index) => (
                <option key={c.id} value={c.id}>
                  Rang {index + 1} — {c.profileName} — {c.score.toFixed(2)}/100
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="tabs">
          {(Object.keys(VIEW_LABELS) as View[]).map((key) => (
            <button
              key={key}
              className={`tab${view === key ? ' tab--active' : ''}`}
              onClick={() => {
                setView(key)
                setResourceId(null)
              }}
            >
              {VIEW_LABELS[key]}
            </button>
          ))}
        </div>

        {view !== 'occupancy' && (
          <div className="form-row" style={{ marginTop: '0.9rem' }}>
            <div className="field">
              <label htmlFor="resource">
                {view === 'teacher' ? 'Enseignant' : view === 'group' ? 'Groupe' : 'Salle'}
              </label>
              <select
                id="resource"
                value={selectedResource ?? ''}
                onChange={(e) => setResourceId(e.target.value)}
              >
                {resources.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {view === 'group' && (
          <p className="panel__note">
            Un CM réunit toute la promotion : le tableau d’un groupe inclut donc les séances de ses
            groupes parents, que ses étudiants suivent également.
          </p>
        )}
      </section>

      {candidate && (
        <section className="panel">
          {view === 'occupancy' ? (
            <OccupancyView candidate={candidate} instance={instance.data} lookups={lookups} />
          ) : selectedResource ? (
            <TimetableGrid
              placements={placementsFor(candidate, view, selectedResource, lookups)}
              instance={instance.data}
              lookups={lookups}
              dimension={view}
            />
          ) : (
            <p className="empty">Aucune ressource à afficher.</p>
          )}
        </section>
      )}
    </>
  )
}
