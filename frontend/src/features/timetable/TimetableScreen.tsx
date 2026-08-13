import { useMemo, useState } from 'react'

import { useInstance, useRun, useRuns } from '@/api/queries'
import { profileLabel } from '@/labels'
import { OccupancyView } from '@/features/timetable/OccupancyView'
import { PrintHeader } from '@/features/timetable/PrintHeader'
import { TimetableGrid } from '@/features/timetable/TimetableGrid'
import { GridKey } from '@/features/timetable/GridKey'
import {
  downloadCsv,
  exportFilename,
  occupancyCsv,
  provenanceEntries,
  timetableCsv,
} from '@/features/timetable/export'
import {
  buildLookups,
  placementsFor,
  roomOccupancy,
  type Dimension,
} from '@/features/timetable/model'
import { Page } from '@/shell/Page'

type View = Dimension | 'occupancy'

const VIEW_LABELS: Record<View, string> = {
  teacher: 'By teacher',
  group: 'By group',
  room: 'By room',
  occupancy: 'Room occupancy',
}

/**
 * FR-7 and FR-18 — the four views of a candidate.
 *
 * A run is chosen rather than assumed: a candidate is immutable and belongs to
 * the run that produced it (invariant 6), so a view is always "this timetable,
 * from that run", never a free-floating timetable.
 *
 * ⚠️ **Print and export sit in the page bar** because they act on whatever is
 * displayed, and the thing displayed is a full-width grid the reader scrolls.
 * Buttons that scroll away from the artefact they export are buttons a reader
 * has to hunt for.
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

  if (instance.isLoading || runs.isLoading)
    return (
      <Page title="Timetables">
        <p className="empty">Loading…</p>
      </Page>
    )

  if (!instance.data || !lookups)
    return (
      <Page title="Timetables">
        <p className="error" role="alert">
          The department data could not be loaded. Reload the page, or sign in again if the problem
          continues.
        </p>
      </Page>
    )

  if (completed.length === 0)
    return (
      <Page title="Timetables" subtitle="A candidate's week, by teacher, group or room">
        <p className="empty">
          No run has produced a candidate yet. Generate a timetable first and it will appear here.
        </p>
      </Page>
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
  const selectedResourceLabel =
    resources.find((r) => r.id === selectedResource)?.label ?? selectedResource

  // FR-10. Both outputs describe the same thing, so both are built from one
  // provenance list: a printed sheet and an exported file cannot disagree
  // about which run and which candidate they came from.
  const outputs =
    run.data && candidate
      ? (() => {
          const viewLabel = VIEW_LABELS[view]
          const resourceLabel = view === 'occupancy' ? null : selectedResourceLabel
          const entries = provenanceEntries(run.data, candidate, viewLabel, resourceLabel)
          return {
            entries,
            title: resourceLabel === null ? viewLabel : `${viewLabel} — ${resourceLabel}`,
            download: () =>
              downloadCsv(
                exportFilename(viewLabel, resourceLabel, candidate.id),
                view === 'occupancy'
                  ? occupancyCsv(roomOccupancy(candidate, instance.data, lookups), entries)
                  : timetableCsv(
                      selectedResource
                        ? placementsFor(candidate, view, selectedResource, lookups)
                        : [],
                      lookups,
                      entries,
                    ),
              ),
          }
        })()
      : null

  return (
    <Page
      title="Timetables"
      subtitle={
        candidate
          ? `${profileLabel(candidate.profileName)} · ${candidate.score.toFixed(2)}/100 · ${outputs?.title ?? ''}`
          : undefined
      }
      actions={
        outputs && (
          <>
            <button className="secondary" onClick={() => window.print()}>
              Print
            </button>
            <button className="secondary" onClick={outputs.download}>
              Export CSV
            </button>
          </>
        )
      }
    >
      <section className="section no-print">
        <div className="toolbar">
          <div className="field">
            <label htmlFor="run">Run</label>
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
                  {r.id} — {r.candidateCount} candidates
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label htmlFor="candidate">Candidate</label>
            <select
              id="candidate"
              value={candidate?.id ?? ''}
              onChange={(e) => setCandidateId(e.target.value)}
            >
              {candidates.map((c, index) => (
                <option key={c.id} value={c.id}>
                  #{index + 1} · {profileLabel(c.profileName)} · {c.score.toFixed(2)}/100
                </option>
              ))}
            </select>
          </div>

          {view !== 'occupancy' && (
            <div className="field toolbar__grow">
              <label htmlFor="resource">
                {view === 'teacher' ? 'Teacher' : view === 'group' ? 'Group' : 'Room'}
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
          )}
        </div>

        <div className="tabs">
          {(Object.keys(VIEW_LABELS) as View[]).map((key) => (
            <button
              key={key}
              className={`tab${view === key ? ' tab--active' : ''}`}
              aria-current={view === key ? 'page' : undefined}
              onClick={() => {
                setView(key)
                setResourceId(null)
              }}
            >
              {VIEW_LABELS[key]}
            </button>
          ))}
        </div>

        {view === 'group' && (
          <p className="hint">
            A lecture (CM) gathers the whole promotion, so a group’s timetable also includes the
            sessions of its parent groups — its students attend those too.
          </p>
        )}
        <p className="hint">
          Only the view shown here is printed. The exported file carries the run, the seed and the
          weights that produced it.
        </p>
      </section>

      {candidate && (
        <section className="panel panel--printable">
          {outputs && (
            <PrintHeader
              title={outputs.title}
              entries={outputs.entries}
              printedOn={new Date().toLocaleDateString('en-GB')}
            />
          )}
          {view === 'occupancy' ? (
            <OccupancyView candidate={candidate} instance={instance.data} lookups={lookups} />
          ) : selectedResource ? (
            <>
              <TimetableGrid
                placements={placementsFor(candidate, view, selectedResource, lookups)}
                instance={instance.data}
                lookups={lookups}
                dimension={view}
              />
              <GridKey />
            </>
          ) : (
            <p className="empty">Select a resource above to see its week.</p>
          )}
        </section>
      )}
    </Page>
  )
}
