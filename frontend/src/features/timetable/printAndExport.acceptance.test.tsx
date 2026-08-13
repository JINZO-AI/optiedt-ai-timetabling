import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { PrintHeader } from '@/features/timetable/PrintHeader'
import { TimetableGrid } from '@/features/timetable/TimetableGrid'
import { provenanceEntries, timetableRows } from '@/features/timetable/export'
import { buildLookups, placementsFor } from '@/features/timetable/model'
import type { Candidate, InstanceData, Run } from '@/types/domain'

/**
 * FR-10 — print or export a timetable view.
 *
 *     Criterion (⚠️ **project decision**, adopted in C-9 on 2026-08-10 —
 *     derived from repository evidence because supervisor clarification was
 *     unavailable; NOT supervisor-written):
 *
 *     "A timetable view can be printed or exported, and what leaves the screen
 *     is THE DISPLAYED VIEW."
 *
 *     Derived from, and only from, the specification's own words:
 *     - **CdC §3, for the students:** "Printing and export of the displayed
 *       view."
 *     - **CdC, module list:** "Display module: views by teacher, by group, by
 *       classroom, by laboratory and by examination, printing and export."
 *     - **SRS §4.1:** "Timetable view: weekly grid filtered by teacher, group,
 *       classroom or laboratory, **with printing of the displayed view**."
 *
 * ⚠️ **"The displayed view" is the whole content of the criterion**, and it is
 * the only part that can fail quietly. That a button exists is not the promise;
 * the promise is that the sheet and the file describe *what is on the screen*.
 * So this file renders the grid, exports the same view, and compares the two as
 * sets. C-9 records that Phase 9's closing audit performed exactly this
 * comparison **by hand** — 6 cells against 6 rows. This is that check,
 * automated.
 *
 * ⚠️ **This is a FRONTEND acceptance file, and it is the first one.** Every
 * other acceptance file lives in `backend/tests/acceptance/`. FR-10 cannot:
 * Phase 9 delivered print and export **without touching a single backend
 * file**, because `docs/architecture.md` puts "display, filter, print" in the
 * presentation layer. A requirement whose entire surface is the rendered DOM
 * has to be verified there, or its status would be decided by a directory
 * layout rather than by evidence. Recorded in `docs/testing-strategy.md` §4.
 */

const HOURS: [string, string][] = [
  ['08:30', '10:00'],
  ['10:15', '11:45'],
  ['13:00', '14:30'],
  ['14:45', '16:15'],
]

function hours(index: number): [string, string] {
  return HOURS[index % HOURS.length] ?? ['00:00', '00:00']
}

/** Two days of four periods; slot = dayIndex * 4 + periodIndex. Slot 3 closed. */
function instance(): InstanceData {
  return {
    programmes: [],
    promotions: [],
    groups: [
      { id: 'G-PROMO', promotion: 'P1', parentGroup: null, level: 'PROMO', label: 'L2', size: 60 },
      {
        id: 'G-TP1',
        promotion: 'P1',
        parentGroup: 'G-PROMO',
        level: 'TP',
        label: 'L2-A1',
        size: 15,
      },
    ],
    teachers: [],
    courses: [
      {
        id: 'C1',
        code: 'INF101',
        department: 'D',
        programme: 'P',
        level: 'L2',
        semester: 1,
        credits: 6,
      },
      {
        id: 'C2',
        code: 'MAT202',
        department: 'D',
        programme: 'P',
        level: 'L2',
        semester: 1,
        credits: 6,
      },
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
      { session: 'S-CM', slot: 0, room: 'R1' },
      { session: 'S-TP', slot: 5, room: 'R2' },
    ],
    subScores: [],
  }
}

function run(): Run {
  return {
    id: 'RUN-1',
    state: 'COMPLETED',
    seed: 42,
    deterministicBudget: 90,
    modelVersion: 'test',
    weights: { S2: 0.25 },
    candidates: [candidate()],
    preAnalysis: [],
    diagnosis: null,
    duplicatesRemoved: [],
    deterministicTimeUsed: 1,
    wallClockSeconds: 1,
    error: null,
    origin: null,
    overrides: { lockedPlacements: [], excludedSlots: [], excludedRooms: [] },
  } as unknown as Run
}

/** The courses a reader can actually see drawn in the grid. */
function drawnCourses(container: HTMLElement): string[] {
  return [...container.querySelectorAll('.cell--busy .cell__course')]
    .map((node) => node.textContent ?? '')
    .sort()
}

afterEach(cleanup)

describe('what leaves the screen is the displayed view', () => {
  it.each(['teacher', 'group', 'room'] as const)(
    'the exported file describes exactly the %s view that was drawn',
    (dimension) => {
      const data = instance()
      const lookups = buildLookups(data)
      const resource = { teacher: 'T001', group: 'G-TP1', room: 'R1' }[dimension]
      const shown = placementsFor(candidate(), dimension, resource, lookups)

      const { container } = render(
        <TimetableGrid
          placements={shown}
          instance={data}
          lookups={lookups}
          dimension={dimension}
        />,
      )
      const exported = timetableRows(shown, lookups)

      // Column 4 of a row is the course code — the same string the cell draws.
      expect(exported.map((row) => row[4]).sort()).toEqual(drawnCourses(container))
    },
  )

  it('exports the filtered view, not the whole candidate', () => {
    // ⚠️ The failure this catches is the tempting one: exporting
    // `candidate.placements` instead of the placements the screen was given.
    // The file would then be correct, complete, and about a different thing
    // from the sheet beside it.
    const data = instance()
    const lookups = buildLookups(data)
    const wholeCandidate = timetableRows(candidate().placements, lookups)

    const justTheSubgroup = timetableRows(
      placementsFor(candidate(), 'room', 'R2', lookups),
      lookups,
    )

    expect(wholeCandidate).toHaveLength(2)
    expect(justTheSubgroup).toHaveLength(1)
    expect(justTheSubgroup[0]?.[4]).toBe('MAT202')
  })

  it('emits one row for a two-period session, though the grid draws two cells', () => {
    // The grid draws a continuation cell so the week keeps its shape. A file
    // that copied that would report 218 sessions as 322 and overstate every
    // teacher's load — so "the displayed view" is the view's CONTENT, not its
    // cell count.
    const data = instance()
    const lookups = buildLookups(data)
    const shown = placementsFor(candidate(), 'group', 'G-PROMO', lookups)

    const { container } = render(
      <TimetableGrid
        placements={shown}
        instance={data}
        lookups={lookups}
        dimension="group"
      />,
    )

    expect(container.querySelectorAll('.cell--continued')).toHaveLength(1)
    expect(timetableRows(shown, lookups)).toHaveLength(1)
    expect(timetableRows(shown, lookups)[0]?.[3]).toBe('2')
  })

  it('names the run and the candidate on both the sheet and the file', () => {
    // ⚠️ Without this a printed grid is anonymous: two sheets from two
    // candidates of one run are indistinguishable on paper, which is exactly
    // the confusion a printed timetable is handed out to settle. One
    // provenance list, two renderings — so the two can never disagree.
    const entries = provenanceEntries(run(), candidate(), 'Par groupe', 'L2-A1')

    const { container } = render(
      <PrintHeader title="Par groupe — L2-A1" entries={entries} printedOn="11/08/2026" />,
    )

    const printed = container.textContent ?? ''
    for (const [label, value] of entries) {
      expect(printed).toContain(label)
      expect(printed).toContain(value)
    }
    expect(entries.map(([label]) => label)).toContain('Run')
  })
})

describe('a view that can be printed at all', () => {
  it('marks the print header as print-only, so the screen is not duplicated', () => {
    // The same facts are already above the grid on screen, in the selectors.
    const { container } = render(
      <PrintHeader title="Par groupe" entries={[['Groupe', 'L2-A1']]} printedOn="11/08/2026" />,
    )

    expect(container.querySelector('.print-only')).toBeTruthy()
  })
})
