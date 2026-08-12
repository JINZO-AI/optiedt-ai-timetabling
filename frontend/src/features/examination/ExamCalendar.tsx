/**
 * FR-20's view — SRS §5.5: "Examination view: calendar of the session by group
 * and by room."
 *
 * The display only, split from the screen the way `DatasetPanel` is split from
 * `DatasetScreen`, so the calendar can be rendered and read back in a test
 * without a query client.
 *
 * ⚠️ **This component computes nothing and decides nothing.** Every figure it
 * shows — the slot, the day, the rooms, the assigned capacity, the spread
 * penalty — arrives already computed from the API, exactly as the weekly views
 * do (`docs/architecture.md`: the presentation layer may not "compute a score,
 * decide an order"). What it does is arrange: group by day, sort by period,
 * and name the rooms.
 *
 * ⚠️ **The two groupings are the specification's own, not a choice.** §5.5 asks
 * for the calendar "by group and by room", so the view offers both and neither
 * is a filter over the other — a reader checking room usage and a reader
 * checking a promotion's spread are asking different questions.
 */

import { useMemo, useState } from 'react'

import type { ExamPlacement, ExamRun } from '@/types/domain'

type Grouping = 'group' | 'room'

export function ExamCalendar({ run }: { run: ExamRun }) {
  const [grouping, setGrouping] = useState<Grouping>('group')

  const days = useMemo(() => byDay(run.placements), [run.placements])

  if (run.placements.length === 0) {
    return null
  }

  return (
    <section className="exam-calendar">
      <header className="exam-calendar__header">
        <h3>Calendrier de la session d’examens</h3>
        <div className="exam-calendar__tabs" role="tablist" aria-label="Regroupement">
          <button
            role="tab"
            aria-selected={grouping === 'group'}
            onClick={() => setGrouping('group')}
          >
            Par groupe
          </button>
          <button
            role="tab"
            aria-selected={grouping === 'room'}
            onClick={() => setGrouping('room')}
          >
            Par salle
          </button>
        </div>
      </header>

      <p className="exam-calendar__summary">
        {run.examinationCount} examens placés sur {run.slotCount} créneaux
        disponibles.{' '}
        {run.spreadPenalty !== null && (
          <>
            Étalement (SX1) : <strong>{run.spreadPenalty}</strong> — nombre
            d’examens d’une même promotion partageant un jour, au-delà du
            premier.
          </>
        )}
      </p>

      {grouping === 'group' ? <ByGroup days={days} /> : <ByRoom run={run} />}
    </section>
  )
}

function ByGroup({ days }: { days: [string, ExamPlacement[]][] }) {
  return (
    <div className="exam-calendar__days">
      {days.map(([day, placements]) => (
        <article key={day} className="exam-calendar__day">
          <h4>{formatDay(day)}</h4>
          <table>
            <thead>
              <tr>
                <th scope="col">Période</th>
                <th scope="col">Examen</th>
                <th scope="col">Promotion</th>
                <th scope="col">Candidats</th>
                <th scope="col">Salles</th>
                <th scope="col">Capacité</th>
                <th scope="col">Surveillant</th>
              </tr>
            </thead>
            <tbody>
              {placements.map((placement) => (
                <tr key={placement.examination}>
                  <td>P{placement.periodIndex + 1}</td>
                  <td>{placement.course}</td>
                  <td>{placement.promotion}</td>
                  <td>{placement.candidateCount}</td>
                  {/* R-6: several rooms is the ordinary case, not an edge one. */}
                  <td>{placement.rooms.join(', ')}</td>
                  <td>
                    {placement.assignedCapacity}
                    {placement.rooms.length > 1 && (
                      <span className="exam-calendar__split">
                        {' '}
                        ({placement.rooms.length} salles)
                      </span>
                    )}
                  </td>
                  <td>{placement.supervisor}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      ))}
    </div>
  )
}

function ByRoom({ run }: { run: ExamRun }) {
  // One row per (room, examination) pair: an examination occupying three rooms
  // genuinely occupies three rooms, and collapsing it to one row would make the
  // room view understate what is booked — the opposite of what it is for.
  const rows = useMemo(() => {
    const out: { room: string; placement: ExamPlacement }[] = []
    for (const placement of run.placements) {
      for (const room of placement.rooms) out.push({ room, placement })
    }
    return out.sort(
      (a, b) =>
        a.room.localeCompare(b.room, undefined, { numeric: true }) ||
        a.placement.slot - b.placement.slot,
    )
  }, [run.placements])

  return (
    <table className="exam-calendar__rooms">
      <thead>
        <tr>
          <th scope="col">Salle</th>
          <th scope="col">Jour</th>
          <th scope="col">Période</th>
          <th scope="col">Examen</th>
          <th scope="col">Promotion</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ room, placement }) => (
          <tr key={`${room}-${placement.examination}`}>
            <td>{room}</td>
            <td>{formatDay(placement.day)}</td>
            <td>P{placement.periodIndex + 1}</td>
            <td>{placement.course}</td>
            <td>{placement.promotion}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function byDay(placements: ExamPlacement[]): [string, ExamPlacement[]][] {
  const grouped = new Map<string, ExamPlacement[]>()
  for (const placement of placements) {
    const existing = grouped.get(placement.day)
    if (existing) existing.push(placement)
    else grouped.set(placement.day, [placement])
  }
  for (const list of grouped.values()) {
    list.sort((a, b) => a.periodIndex - b.periodIndex || a.course.localeCompare(b.course))
  }
  return [...grouped.entries()].sort(([a], [b]) => a.localeCompare(b))
}

export function formatDay(iso: string): string {
  const parsed = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return iso
  return parsed.toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })
}
