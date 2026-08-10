import { describe, expect, it } from 'vitest'

import {
  ancestorsOrSelf,
  buildLookups,
  gridAxes,
  occupancyBySlot,
  placementsFor,
} from '@/features/timetable/model'
import type { Candidate, InstanceData } from '@/types/domain'

/**
 * FR-7 — "Display the timetable by teacher, by group and by room".
 *
 *     Verified against SRS §3.2 Table 9, quoted:
 *     input      "Published timetable and chosen filter"
 *     processing "Selection of the sessions concerning the resource"
 *     output     "Weekly grid of the resource"
 *
 * ⚠️ **This file is the *processing* row, and it is a display-layer file on
 * purpose.** `docs/architecture.md` permits the presentation layer to "display,
 * filter, print", so the selection genuinely lives here — and no backend test
 * can reach it. `backend/tests/acceptance/test_fr07.py` is the other half: that
 * the API hands this layer enough to filter with. Both are needed and neither
 * substitutes for the other, exactly as FR-15's two halves are.
 *
 * The grid itself — Table 9's *output* row — is `TimetableGrid.test.tsx`.
 */

const HOURS: [string, string][] = [
  ['08:30', '10:00'],
  ['10:15', '11:45'],
  ['13:00', '14:30'],
  ['14:45', '16:15'],
]

/** `noUncheckedIndexedAccess` is on, and a fixture may not opt out of it. */
function hours(period: number): [string, string] {
  return HOURS[period % HOURS.length] ?? ['00:00', '00:00']
}

function session(
  id: string,
  group: string,
  teacher: string,
  durationPeriods: number,
): InstanceData['sessions'][number] {
  return {
    id,
    course: 'C1',
    group,
    teacher,
    type: durationPeriods === 2 ? 'TP' : 'CM',
    durationPeriods,
    occurrencesPerWeek: 1,
    requiredRoomType: 'Salle',
    locked: false,
  }
}

/**
 * Two days of four periods; slot = dayIndex * 4 + periodIndex. Slot 3 is
 * closed, so the week has a hole the axes must still account for.
 *
 * The hierarchy is the real one — promotion → TD → TP — because the group
 * filter's whole subtlety is that it climbs it.
 */
function instance(): InstanceData {
  return {
    programmes: [],
    promotions: [],
    groups: [
      { id: 'G-PROMO', promotion: 'P1', parentGroup: null, level: 'PROMO', label: 'L2', size: 60 },
      { id: 'G-TD1', promotion: 'P1', parentGroup: 'G-PROMO', level: 'TD', label: 'L2-A', size: 30 },
      { id: 'G-TD2', promotion: 'P1', parentGroup: 'G-PROMO', level: 'TD', label: 'L2-B', size: 30 },
      { id: 'G-TP1', promotion: 'P1', parentGroup: 'G-TD1', level: 'TP', label: 'L2-A1', size: 15 },
      { id: 'G-TP2', promotion: 'P1', parentGroup: 'G-TD1', level: 'TP', label: 'L2-A2', size: 15 },
    ],
    teachers: [],
    courses: [
      { id: 'C1', code: 'INF101', department: 'D', programme: 'P', level: 'L2', semester: 1, credits: 6 },
    ],
    sessions: [
      // A CM for the whole promotion, two periods long.
      session('S-CM', 'G-PROMO', 'T001', 2),
      // A TD for one half of it.
      session('S-TD', 'G-TD1', 'T002', 1),
      // A TP for one subgroup, and one for its sibling.
      session('S-TP1', 'G-TP1', 'T003', 1),
      session('S-TP2', 'G-TP2', 'T003', 1),
    ],
    rooms: [
      { id: 'R1', building: 'B', code: 'S 101', capacity: 200, type: 'Salle', equipment: [] },
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
      { session: 'S-CM', slot: 0, room: 'R1' },
      { session: 'S-TD', slot: 2, room: 'R2' },
      { session: 'S-TP1', slot: 4, room: 'R2' },
      { session: 'S-TP2', slot: 5, room: 'R1' },
    ],
    subScores: [],
  }
}

const lookups = () => buildLookups(instance())
const selected = (dimension: 'teacher' | 'group' | 'room', id: string) =>
  placementsFor(candidate(), dimension, id, lookups())
    .map((p) => p.session)
    .sort()

describe('selecting the sessions concerning the resource', () => {
  it('gives a teacher only the sessions they teach', () => {
    expect(selected('teacher', 'T003')).toEqual(['S-TP1', 'S-TP2'])
    expect(selected('teacher', 'T001')).toEqual(['S-CM'])
  })

  it('gives a room only the sessions held in it', () => {
    expect(selected('room', 'R1')).toEqual(['S-CM', 'S-TP2'])
    expect(selected('room', 'R2')).toEqual(['S-TD', 'S-TP1'])
  })

  it('gives a subgroup its ancestors sessions as well as its own', () => {
    // A CM gathers the whole promotion and a TD its half, so a TP subgroup's
    // students sit through both. Showing only S-TP1 would print a week with
    // two holes those students do not have — which is a wrong timetable, not
    // a terse one.
    expect(selected('group', 'G-TP1')).toEqual(['S-CM', 'S-TD', 'S-TP1'])
  })

  it('does not give a subgroup its siblings sessions', () => {
    // The failure this guards is the mirror image of the one above and is
    // easy to introduce while fixing it: walking the hierarchy DOWNWARD, or
    // grouping a whole promotion flat, puts S-TP2 into G-TP1's week. They are
    // disjoint sets of students. The solver made exactly this mistake once and
    // it made the reference instance look infeasible — see
    // `solver/constraints/overlap.py`.
    expect(selected('group', 'G-TP1')).not.toContain('S-TP2')
    expect(selected('group', 'G-TD2')).toEqual(['S-CM'])
  })

  it('gives a promotion only what addresses the promotion itself', () => {
    // Upward, never downward: the promotion does not attend its subgroups' TPs.
    expect(selected('group', 'G-PROMO')).toEqual(['S-CM'])
  })

  it('returns nothing for a resource with no sessions rather than everything', () => {
    // An unfiltered fallback is the dangerous failure here: a teacher with a
    // free week would be shown the whole department's timetable as if it were
    // theirs.
    expect(selected('teacher', 'T-NOBODY')).toEqual([])
    expect(selected('room', 'R-NOBODY')).toEqual([])
    expect(selected('group', 'G-NOBODY')).toEqual([])
  })
})

describe('the group hierarchy the selection walks', () => {
  it('climbs from a subgroup to its promotion', () => {
    expect(ancestorsOrSelf('G-TP1', lookups().groupById)).toEqual([
      'G-TP1',
      'G-TD1',
      'G-PROMO',
    ])
  })

  it('stops rather than hanging when the data contains a cycle', () => {
    // Malformed data must degrade the view, never freeze the browser. The
    // chain is bounded by depth for exactly this case.
    const cyclic = new Map(lookups().groupById)
    cyclic.set('G-PROMO', { ...cyclic.get('G-PROMO')!, parentGroup: 'G-TP1' })

    const chain = ancestorsOrSelf('G-TP1', cyclic)

    expect(chain.length).toBeLessThanOrEqual(8)
  })
})

describe('placing the selection in the week', () => {
  it('occupies every period a session runs for, not only its first', () => {
    const cells = occupancyBySlot(placementsFor(candidate(), 'group', 'G-PROMO', lookups()), lookups())

    // S-CM starts at slot 0 and lasts two periods.
    expect([...cells.keys()].sort((a, b) => a - b)).toEqual([0, 1])
  })

  it('marks the second period as a continuation so it is not drawn twice', () => {
    const cells = occupancyBySlot(placementsFor(candidate(), 'group', 'G-PROMO', lookups()), lookups())

    expect(cells.get(0)?.continuation).toBe(false)
    expect(cells.get(1)?.continuation).toBe(true)
    // Both cells name one session: the grid draws one block, and the
    // occupancy of the second period is still recoverable.
    expect(cells.get(1)?.session.id).toBe('S-CM')
  })

  it('keeps the closed slot in the axes so the week keeps its shape', () => {
    // Slot 3 is closed. Dropping it would shift every later period up a row
    // and silently redraw the day.
    const { days, periods } = gridAxes(instance().slots)

    expect(days).toEqual([0, 1])
    expect(periods).toEqual([0, 1, 2, 3])
  })
})
