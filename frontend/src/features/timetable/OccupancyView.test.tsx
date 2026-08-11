import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { OccupancyView } from '@/features/timetable/OccupancyView'
import { buildLookups, roomOccupancy } from '@/features/timetable/model'
import type { Candidate, InstanceData } from '@/types/domain'

/**
 * FR-18 — "Display occupancy of each classroom and laboratory".
 *
 *     Criterion (⚠️ **project decision**, C-9 resolved 2026-08-11 — derived
 *     from repository evidence and engineering research because supervisor
 *     clarification was unavailable; NOT supervisor-written):
 *     "An authorised user can consult, for EACH classroom and EACH laboratory,
 *     the share of the week's open periods it occupies on a given candidate."
 *
 * ⚠️ **`roomOccupancy` had NO test of any kind until this file**, which C-9
 * recorded. It is the third implementation of one definition — C-4's
 * `utilisation(r,k)`, also written in `analysis/criteria.py` and
 * `solver/objective.py` — and C-4 records what the last divergence between two
 * of them cost. These tests are what stop this one drifting.
 *
 * `acceptance/test_fr18.py` establishes that the API carries everything the
 * figure is derived from. What only a rendering test can establish is here:
 * that the arithmetic is right, that every room reaches the screen, and that
 * the figure is **labelled for what it measures**.
 */

const HOURS: [string, string][] = [
  ['08:30', '10:00'],
  ['10:10', '11:40'],
]

function hours(period: number): [string, string] {
  return HOURS[period % HOURS.length] ?? ['00:00', '00:00']
}

/**
 * Two days of two periods = 4 slots, of which **3 open** (slot 3 is closed).
 *
 * Three is deliberate and not a round number: a denominator of 4 would let a
 * bug that counted closed slots produce the same ratio for a room occupying 2
 * of 4 as for one occupying 1.5 of 3. With 3 the two disagree.
 */
function instance(): InstanceData {
  return {
    programmes: [],
    promotions: [],
    groups: [
      { id: 'G1', promotion: 'P1', parentGroup: null, level: 'PROMO', label: 'L1', size: 30 },
    ],
    teachers: [],
    courses: [
      {
        id: 'C1',
        code: 'INF101',
        department: 'D',
        programme: 'P',
        level: 'L1',
        semester: 1,
        credits: 6,
      },
    ],
    sessions: [
      {
        id: 'S-LONG',
        course: 'C1',
        group: 'G1',
        teacher: 'T001',
        type: 'CM',
        durationPeriods: 2,
        occurrencesPerWeek: 1,
        requiredRoomType: 'Amphi',
        locked: false,
      },
      {
        id: 'S-SHORT',
        course: 'C1',
        group: 'G1',
        teacher: 'T001',
        type: 'TD',
        durationPeriods: 1,
        occurrencesPerWeek: 1,
        requiredRoomType: 'Salle',
        locked: false,
      },
    ],
    rooms: [
      { id: 'R-AMPHI', building: 'B', code: 'A1', capacity: 200, type: 'Amphi', equipment: [] },
      { id: 'R-SALLE', building: 'B', code: 'S1', capacity: 40, type: 'Salle', equipment: [] },
      // ⚠️ Used by nothing. The row this view must NOT drop.
      { id: 'R-VIDE', building: 'B', code: 'S2', capacity: 40, type: 'Salle', equipment: [] },
    ],
    slots: [0, 1, 2, 3].map((index) => ({
      index,
      dayIndex: Math.floor(index / 2),
      periodIndex: index % 2,
      startHour: hours(index % 2)[0],
      endHour: hours(index % 2)[1],
      isOpen: index !== 3,
    })),
    constraints: [],
    calendarConfig: {},
  }
}

function candidate(): Candidate {
  return {
    id: 'cand-1',
    run: 'run-1',
    profileName: 'balanced',
    cost: 0,
    score: 80,
    placements: [
      { session: 'S-LONG', slot: 0, room: 'R-AMPHI' },
      { session: 'S-SHORT', slot: 2, room: 'R-SALLE' },
    ],
    subScores: [],
  }
}

function rows() {
  const data = instance()
  return roomOccupancy(candidate(), data, buildLookups(data))
}

afterEach(cleanup)

describe('the quantity — C-4s utilisation(r,k)', () => {
  it('counts occupied PERIODS, so a two-period session counts twice', () => {
    // ⚠️ The error this catches is the one `solver/occupancy.py` exists to
    // prevent in the model: counting a session once when it spans two periods.
    // Here it would report the amphitheatre at half its real use.
    const amphi = rows().find((r) => r.roomId === 'R-AMPHI')

    expect(amphi?.occupiedPeriods).toBe(2)
  })

  it('divides by the OPEN slots, not by every slot in the grid', () => {
    // Invariant 7: a closed half-day is configuration. Counting it as unused
    // capacity would make every room look emptier than it is.
    const amphi = rows().find((r) => r.roomId === 'R-AMPHI')

    expect(amphi?.openPeriods).toBe(3)
    expect(amphi?.ratio).toBeCloseTo(2 / 3, 10)
  })

  it('follows the calendar when a half-day is closed', () => {
    // ⚠️ Only reachable since Phase 11 made the calendar editable. The same
    // teaching in a shorter week is a larger share of it, and a figure pinned
    // to the old denominator would under-report every room silently.
    const shortened = instance()
    shortened.slots = shortened.slots.map((s) => (s.index === 2 ? { ...s, isOpen: false } : s))

    const amphi = roomOccupancy(candidate(), shortened, buildLookups(shortened)).find(
      (r) => r.roomId === 'R-AMPHI',
    )

    expect(amphi?.openPeriods).toBe(2)
    expect(amphi?.ratio).toBeCloseTo(2 / 2, 10)
  })

  it('reports a room no session was placed in, at zero', () => {
    // **The criterion's word is EACH.** A room at 0 % is the most actionable
    // row in the table; dropping it would answer a different question.
    const empty = rows().find((r) => r.roomId === 'R-VIDE')

    expect(empty).toBeDefined()
    expect(empty?.occupiedPeriods).toBe(0)
    expect(empty?.ratio).toBe(0)
  })

  it('reports every room of every type', () => {
    expect(rows().map((r) => r.roomId).sort()).toEqual(['R-AMPHI', 'R-SALLE', 'R-VIDE'])
  })
})

describe('what reaches the screen', () => {
  it('shows each room with its periods, its denominator and its rate', () => {
    const data = instance()
    render(
      <OccupancyView candidate={candidate()} instance={data} lookups={buildLookups(data)} />,
    )

    const row = screen.getAllByRole('row').find((r) => within(r).queryByText('A1'))
    expect(row).toBeTruthy()
    expect(within(row!).getByText('2')).toBeTruthy()
    expect(within(row!).getByText('3')).toBeTruthy()
    expect(within(row!).getByText(/66\.7 %/)).toBeTruthy()
  })

  it('shows the unused room rather than hiding it', () => {
    const data = instance()
    render(
      <OccupancyView candidate={candidate()} instance={data} lookups={buildLookups(data)} />,
    )

    const row = screen.getAllByRole('row').find((r) => within(r).queryByText('S2'))
    expect(row).toBeTruthy()
    expect(within(row!).getByText(/0\.0 %/)).toBeTruthy()
  })

  it('groups the rooms by type, because the types are not comparable', () => {
    const data = instance()
    render(
      <OccupancyView candidate={candidate()} instance={data} lookups={buildLookups(data)} />,
    )

    // ⚠️ By ROLE, not by text: "Salle" is also a column header, so a plain
    // text query matches two nodes and would pass for a component that had
    // stopped grouping entirely.
    expect(screen.getByRole('heading', { name: 'Amphi' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Salle' })).toBeTruthy()
  })

  it('says the rate measures TIME and not seats', () => {
    // ⚠️ **The finding that made this assertion necessary.** In the SMG "UFO"
    // vocabulary standard in higher-education space management, "occupancy"
    // means occupants over capacity and this figure is a *frequency* rate —
    // and the two readings INVERT on the reference instance. An unqualified
    // "Taux" would be read as a seat statistic by anyone who knows the term.
    const data = instance()
    render(
      <OccupancyView candidate={candidate()} instance={data} lookups={buildLookups(data)} />,
    )

    // Asserted on the note's whole text: a regex query matches both the
    // paragraph and the <em> inside it, which is two nodes, not a failure.
    // Located by the C-13 phrase, which appears once and only in the note:
    // "Taux d’occupation" is now also a column header.
    const note = screen.getByText(/deux périodes consécutives/).closest('p')
    expect(note?.textContent).toMatch(/Taux d’occupation = périodes occupées/)
    expect(note?.textContent).toMatch(/temps/i)
    expect(note?.textContent).toMatch(/remplissage en places/i)
  })

  it('keeps the C-13 warning beside the figure', () => {
    // The period figure is the reassuring one for the laboratories. Reading it
    // alone is what let an infeasible instance pass verification.
    const data = instance()
    render(
      <OccupancyView candidate={candidate()} instance={data} lookups={buildLookups(data)} />,
    )

    expect(screen.getByText(/deux périodes consécutives/)).toBeTruthy()
  })
})
