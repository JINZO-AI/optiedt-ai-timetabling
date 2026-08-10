import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { TimetableGrid } from '@/features/timetable/TimetableGrid'
import { buildLookups, placementsFor } from '@/features/timetable/model'
import type { Candidate, InstanceData } from '@/types/domain'

/**
 * FR-7 — "Display the timetable by teacher, by group and by room".
 *
 *     Verified against SRS §3.2 Table 9, quoted:
 *     output "Weekly grid of the resource"
 *
 * ⚠️ **This is the *output* row, and only a rendering test can make the claim.**
 * `model.test.ts` establishes that the right sessions are selected; this
 * establishes that they reach a reader as a week — the right cell, on the right
 * day, at the right hour, once each. A selection that is correct and a grid
 * that draws it in the wrong column are indistinguishable to every other test
 * in this repository.
 *
 * The same reasoning as `ContributionsTable.test.tsx`: the criterion is about
 * what is *displayed*, and the arrangement happens in the component.
 */

const HOURS: [string, string][] = [
  ['08:30', '10:00'],
  ['10:15', '11:45'],
  ['13:00', '14:30'],
  ['14:45', '16:15'],
]

function hours(period: number): [string, string] {
  return HOURS[period % HOURS.length] ?? ['00:00', '00:00']
}

/** Two days of four periods; slot = dayIndex * 4 + periodIndex. Slot 3 closed. */
function instance(): InstanceData {
  return {
    programmes: [],
    promotions: [],
    groups: [
      { id: 'G-PROMO', promotion: 'P1', parentGroup: null, level: 'PROMO', label: 'L2', size: 60 },
      { id: 'G-TP1', promotion: 'P1', parentGroup: 'G-PROMO', level: 'TP', label: 'L2-A1', size: 15 },
    ],
    teachers: [],
    courses: [
      { id: 'C1', code: 'INF101', department: 'D', programme: 'P', level: 'L2', semester: 1, credits: 6 },
      { id: 'C2', code: 'MAT202', department: 'D', programme: 'P', level: 'L2', semester: 1, credits: 6 },
    ],
    sessions: [
      {
        id: 'S-CM',
        course: 'C1',
        group: 'G-PROMO',
        teacher: 'T001',
        type: 'CM',
        durationPeriods: 2,
        occurrencesPerWeek: 1,
        requiredRoomType: 'Amphi',
        locked: false,
      },
      {
        id: 'S-TP',
        course: 'C2',
        group: 'G-TP1',
        teacher: 'T002',
        type: 'TP',
        durationPeriods: 1,
        occurrencesPerWeek: 1,
        requiredRoomType: 'Salle',
        locked: false,
      },
    ],
    rooms: [
      { id: 'R1', building: 'B', code: 'Amphi A', capacity: 200, type: 'Amphi', equipment: [] },
      { id: 'R2', building: 'B', code: 'S 102', capacity: 40, type: 'Salle', equipment: [] },
    ],
    slots: [0, 1, 2, 3, 4, 5, 6, 7].map((index) => ({
      index,
      dayIndex: Math.floor(index / 4),
      periodIndex: index % 4,
      startHour: hours(index)[0],
      endHour: hours(index)[1],
      isOpen: index !== 3,
    })),
    constraints: [],
    calendarConfig: {},
  }
}

function candidate(): Candidate {
  return {
    id: 'CAND-1',
    run: 'RUN-1',
    profileName: 'balanced',
    cost: 0,
    score: 80,
    placements: [
      // Monday, first two periods.
      { session: 'S-CM', slot: 0, room: 'R1' },
      // Tuesday, second period.
      { session: 'S-TP', slot: 5, room: 'R2' },
    ],
    subScores: [],
  }
}

function renderFor(dimension: 'teacher' | 'group' | 'room', resource: string) {
  const data = instance()
  const lookups = buildLookups(data)
  render(
    <TimetableGrid
      placements={placementsFor(candidate(), dimension, resource, lookups)}
      instance={data}
      lookups={lookups}
      dimension={dimension}
    />,
  )
}

/** The cells of one period row, in day order, as the reader sees them. */
function periodRow(startHour: string): HTMLElement[] {
  const header = screen.getByText(new RegExp(`^${startHour}`))
  const row = header.closest('tr')
  if (!row) throw new Error(`no row for ${startHour}`)
  return [...row.querySelectorAll('td')]
}

afterEach(cleanup)

describe('the weekly grid of a resource', () => {
  it('lays out every day of the week and every period of the day', () => {
    renderFor('group', 'G-TP1')

    expect(screen.getByText('Lundi')).toBeTruthy()
    expect(screen.getByText('Mardi')).toBeTruthy()
    // Four period rows, closed one included: the week keeps its shape.
    expect(screen.getByText(/^08:30/)).toBeTruthy()
    expect(screen.getByText(/^14:45/)).toBeTruthy()
  })

  it('puts a session in the cell for its own day and period', () => {
    renderFor('group', 'G-TP1')

    // S-TP is at slot 5 — Tuesday (day 1), second period (10:15).
    const [monday, tuesday] = periodRow('10:15')

    expect(within(tuesday!).getByText('MAT202')).toBeTruthy()
    expect(monday!.textContent).not.toContain('MAT202')
  })

  it('draws a two-period session once, and holds the second period for it', () => {
    // ⚠️ The failure this guards is a course code printed twice down a column,
    // which reads as two sessions of the same course back to back — a
    // different timetable from the one that was generated.
    renderFor('group', 'G-TP1')

    expect(screen.getAllByText('INF101')).toHaveLength(1)

    const [firstPeriodMonday] = periodRow('08:30')
    const [secondPeriodMonday] = periodRow('10:15')

    expect(within(firstPeriodMonday!).getByText('INF101')).toBeTruthy()
    // The continuation cell is marked rather than left blank: an empty cell
    // would read as a free period the students do not have.
    expect(secondPeriodMonday!.className).toContain('cell--continued')
  })

  it('draws a closed slot as closed rather than as free', () => {
    // ADR-003 and invariant 7: a closed half-day is configuration, and the
    // grid reads `isOpen` rather than deciding for itself. A closed slot shown
    // blank would invite someone to ask why nothing was scheduled there.
    renderFor('group', 'G-TP1')

    const lastPeriodMonday = periodRow('14:45')[0]

    expect(lastPeriodMonday!.className).toContain('cell--closed')
    expect(lastPeriodMonday!.textContent).toContain('fermé')
  })

  it('shows a group its ancestors sessions, which is what its students attend', () => {
    // The rendered counterpart of `model.test.ts`'s selection rule: G-TP1 has
    // one session of its own and sits through the promotion's CM.
    renderFor('group', 'G-TP1')

    expect(screen.getByText('INF101')).toBeTruthy()
    expect(screen.getByText('MAT202')).toBeTruthy()
  })

  it('omits from each cell the dimension the reader already selected', () => {
    // A teacher's own grid repeating their id in all 28 cells is noise; the
    // group and the room are what they need. The same cell viewed by room
    // names the teacher instead.
    renderFor('teacher', 'T002')
    expect(screen.queryByText('T002')).toBeNull()
    expect(screen.getByText('L2-A1')).toBeTruthy()
    expect(screen.getByText('S 102')).toBeTruthy()

    cleanup()

    renderFor('room', 'R2')
    expect(screen.getByText('T002')).toBeTruthy()
    expect(screen.queryByText('S 102')).toBeNull()
  })

  it('renders an empty week for a resource with nothing scheduled', () => {
    // Empty, not absent, and not everyone else's timetable.
    renderFor('teacher', 'T-NOBODY')

    expect(screen.getByText('Lundi')).toBeTruthy()
    expect(screen.queryByText('INF101')).toBeNull()
    expect(screen.queryByText('MAT202')).toBeNull()
  })
})
