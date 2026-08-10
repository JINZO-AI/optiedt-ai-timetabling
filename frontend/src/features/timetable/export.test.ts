import { describe, expect, it } from 'vitest'

import {
  OCCUPANCY_CAVEAT,
  exportFilename,
  frNumber,
  occupancyCsv,
  provenanceEntries,
  timetableCsv,
  timetableRows,
  toCsv,
} from '@/features/timetable/export'
import { buildLookups, placementsFor, type RoomOccupancy } from '@/features/timetable/model'
import type { Candidate, InstanceData, Run } from '@/types/domain'

/**
 * FR-10 — "Print or export a timetable view", the export half.
 *
 * ⚠️ **FR-10 has no acceptance criterion to verify against** (C-9: no
 * input/processing/output row in SRS §3.2, and absent from Table 36 entirely).
 * These are therefore display-layer tests in the manner of the existing
 * `vitest` ones, not an acceptance file — there is no quoted promise to open
 * with, and inventing one would be worse than having none.
 *
 * What each test pins is a way the file could be wrong while looking right:
 * a two-period session counted twice, a separator inside a course code
 * splitting a row, an occupancy ratio arriving in a spreadsheet stripped of the
 * sentence that says which bound actually binds.
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

/** Only `id` and `code` matter here; the rest is padding the type requires. */
function course(id: string, code: string): InstanceData['courses'][number] {
  return { id, code, department: 'D', programme: 'P', level: 'L2', semester: 1, credits: 6 }
}

/** Two days of four periods; slot = dayIndex * 4 + periodIndex. */
function instance(): InstanceData {
  return {
    programmes: [],
    promotions: [],
    groups: [
      { id: 'G-PROMO', promotion: 'P1', parentGroup: null, level: 'PROMO', label: 'L2', size: 60 },
      { id: 'G-TD1', promotion: 'P1', parentGroup: 'G-PROMO', level: 'TD', label: 'L2-A', size: 30 },
      {
        id: 'G-TP1',
        promotion: 'P1',
        parentGroup: 'G-TD1',
        level: 'TP',
        label: 'L2-A1',
        size: 15,
      },
    ],
    teachers: [],
    courses: [
      course('C1', 'INF101'),
      // A code carrying the field separator: unquoted it would split the row.
      course('C2', 'MAT;202'),
    ],
    sessions: [
      {
        id: 'S1',
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
        id: 'S2',
        course: 'C2',
        group: 'G-TP1',
        teacher: 'T002',
        type: 'TP',
        durationPeriods: 1,
        occurrencesPerWeek: 1,
        requiredRoomType: 'Lab_Info',
        locked: false,
      },
    ],
    rooms: [
      { id: 'R1', building: 'B', code: 'Amphi A', capacity: 200, type: 'Amphi', equipment: [] },
      { id: 'R2', building: 'B', code: 'Lab 1', capacity: 20, type: 'Lab_Info', equipment: [] },
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
    id: 'CAND-0003',
    run: 'RUN-0001',
    profileName: 'teacher-favouring',
    cost: 42,
    score: 81.1,
    placements: [
      // S2 sits in the afternoon, S1 in the morning: unsorted on purpose, so
      // the day-then-period ordering is doing work rather than agreeing by luck.
      { session: 'S2', slot: 2, room: 'R2' },
      { session: 'S1', slot: 0, room: 'R1' },
    ],
    subScores: [],
  }
}

function run(): Run {
  return {
    id: 'RUN-0001',
    createdAt: '2026-08-10T09:00:00Z',
    seed: 20260807,
    deterministicBudget: 90,
    state: 'COMPLETED',
    modelVersion: 'optiedt-1.0',
    weights: { S2: 0.2, S3: 0.15, S10: 0 },
    preAnalysis: [],
    diagnosis: null,
    candidates: [],
    duplicatesRemoved: [],
    deterministicTimeUsed: 89.4,
    wallClockSeconds: 148,
    error: null,
    origin: null,
    overrides: { lockedPlacements: [], excludedSlots: [], excludedRooms: [] },
  }
}

const lookups = () => buildLookups(instance())

describe('a field that contains the separator cannot split a row', () => {
  it('quotes it instead', () => {
    expect(toCsv([['a;b', 'c']])).toBe('"a;b";c')
  })

  it('doubles an embedded quote, per RFC 4180', () => {
    expect(toCsv([['say "no"']])).toBe('"say ""no"""')
  })

  it('leaves an ordinary field unquoted', () => {
    expect(toCsv([['Lundi', '08:30']])).toBe('Lundi;08:30')
  })

  it('keeps a course code carrying a semicolon on one row', () => {
    const csv = timetableCsv(candidate().placements, lookups(), [])
    const body = csv.split('\r\n').filter((line) => line.includes('MAT;202'))
    expect(body).toHaveLength(1)
    const row = body[0] ?? ''
    expect(row).toContain('"MAT;202"')
    // Nine columns. Splitting naively on the separator yields ten, because the
    // quoted one contributes an extra — which is the point: a reader that
    // honours the quotes sees nine, and the row did not become two.
    expect(row.split(';')).toHaveLength(10)
  })
})

describe('one row per session, never one per period', () => {
  it('emits a two-period session once, ending at the end of its second period', () => {
    const rows = timetableRows(candidate().placements, lookups())
    const lecture = rows.filter((r) => r[4] === 'INF101')

    expect(lecture).toHaveLength(1)
    expect(lecture[0]?.[1]).toBe('08:30') // start of slot 0
    // ⚠️ The failure this guards: taking the END of the FIRST period, which
    // would print a two-hour lecture as a one-hour one on every sheet.
    expect(lecture[0]?.[2]).toBe('11:45') // end of slot 1, not 10:00
  })

  it('states the period count, so a session straddling a break is not read as unbroken', () => {
    // Two periods need not be adjacent on the clock. On the reference instance a
    // TP either side of the midday break exports as 11:50–15:30, and start and
    // end alone would read as 3h40 of continuous laboratory work.
    const rows = timetableRows(candidate().placements, lookups())
    expect(rows.find((r) => r[4] === 'INF101')?.[3]).toBe('2')
    expect(rows.find((r) => r[4] === 'MAT;202')?.[3]).toBe('1')
  })

  it('produces exactly as many rows as there are placements', () => {
    // The grid draws a continuation cell for the second period of a two-period
    // session. A file that copied that would report the week as longer than it
    // is — 218 sessions as 322 on the reference instance.
    const placements = candidate().placements
    expect(timetableRows(placements, lookups())).toHaveLength(placements.length)
  })

  it('orders rows by day and then period', () => {
    const rows = timetableRows(candidate().placements, lookups())
    expect(rows.map((r) => [r[0], r[1]])).toEqual([
      ['Lundi', '08:30'],
      ['Lundi', '13:00'],
    ])
  })

  it('names the course, type, group, teacher and room', () => {
    const rows = timetableRows(candidate().placements, lookups())
    expect(rows[0]).toEqual([
      'Lundi',
      '08:30',
      '11:45',
      '2',
      'INF101',
      'CM',
      'L2',
      'T001',
      'Amphi A',
    ])
  })

  it('skips a placement whose session is unknown rather than writing a half row', () => {
    const rows = timetableRows([{ session: 'GHOST', slot: 0, room: 'R1' }], lookups())
    expect(rows).toEqual([])
  })
})

describe("a group's export carries the sessions its students actually attend", () => {
  it('includes the promotion lecture in a TP subgroup file', () => {
    // Same rule as the screen (`placementsFor`): a CM gathers the whole
    // promotion, so a subgroup exported with only its own sessions would hand a
    // student a week with holes they do not have. This composes the screen's
    // filter with the exporter, which is where the property could be lost.
    const rows = timetableRows(
      placementsFor(candidate(), 'group', 'G-TP1', lookups()),
      lookups(),
    )
    expect(rows.map((r) => r[4]).sort()).toEqual(['INF101', 'MAT;202'])
  })
})

describe('the exported file says what produced it', () => {
  it('carries the run, the seed, the model version and the candidate', () => {
    const entries = provenanceEntries(run(), candidate(), 'Par groupe', 'L2-A1')
    const asObject = Object.fromEntries(entries)

    expect(asObject['Exécution']).toBe('RUN-0001')
    expect(asObject['Graine']).toBe('20260807')
    expect(asObject['Version du modèle']).toBe('optiedt-1.0')
    expect(asObject['Candidat']).toBe('CAND-0003')
    expect(asObject['Profil']).toBe('teacher-favouring')
    expect(asObject['Vue']).toBe('Par groupe')
    expect(asObject['Ressource']).toBe('L2-A1')
  })

  it('carries the whole weight vector, including a criterion weighted zero', () => {
    // One criterion omitted and the score is no longer recomputable from the
    // file; S10 carries weight 0 and is exactly the one an "empty means absent"
    // shortcut would drop.
    const asObject = Object.fromEntries(provenanceEntries(run(), candidate(), 'Par salle', 'Lab 1'))
    expect(asObject['Pondération S2']).toBe('0,200')
    expect(asObject['Pondération S3']).toBe('0,150')
    expect(asObject['Pondération S10']).toBe('0,000')
  })

  it('never calls the deterministic budget a number of seconds', () => {
    const labels = provenanceEntries(run(), candidate(), 'Par salle', 'Lab 1').map(([l]) => l)
    // ADR-011: the budget is deterministic work, not wall clock. The screen
    // says so; a file that dropped the qualifier would invite the reading back.
    expect(labels).toContain('Budget déterministe (pas des secondes)')
  })

  it('omits the resource line on a view that has no single resource', () => {
    const labels = provenanceEntries(run(), candidate(), 'Occupation des salles', null).map(
      ([l]) => l,
    )
    expect(labels).not.toContain('Ressource')
  })

  it('puts the provenance above the table, separated by a blank line', () => {
    const lines = timetableCsv(candidate().placements, lookups(), [['Exécution', 'RUN-0001']]).split(
      '\r\n',
    )
    expect(lines[0]).toBe('Exécution;RUN-0001')
    expect(lines[1]).toBe('')
    expect(lines[2]).toBe('Jour;Début;Fin;Périodes;Cours;Type;Groupe;Enseignant;Salle')
  })
})

describe('the occupancy export keeps the warning that goes with the figure', () => {
  const rows: RoomOccupancy[] = [
    {
      roomId: 'R2',
      code: 'Lab 1',
      type: 'Lab_Info',
      occupiedPeriods: 160,
      openPeriods: 224,
      ratio: 160 / 224,
    },
  ]

  it('states the ratio counts periods and names the window bound', () => {
    // ⚠️ C-13. A bare column of percentages in a spreadsheet, read without this
    // sentence, is the exact misreading that let an infeasible instance pass
    // verification and cost three sessions. On screen the caveat is a paragraph;
    // in the file it has to be a row or it does not travel.
    const csv = occupancyCsv(rows, [])
    expect(csv).toContain(OCCUPANCY_CAVEAT)
    expect(OCCUPANCY_CAVEAT).toMatch(/deux périodes consécutives/)
  })

  it('writes the reassuring period figure, and it is the one the screen shows', () => {
    const csv = occupancyCsv(rows, [])
    expect(csv).toContain('Lab 1;Lab_Info;160;224;71,4')
  })
})

describe('numbers are written for the spreadsheet that will open them', () => {
  it('uses a decimal comma, to match the semicolon separator', () => {
    // With `;` as the separator a French Excel reads `71,4` as a number and
    // `71.4` as text. A column of text is an export in name only.
    expect(frNumber(71.4285, 1)).toBe('71,4')
    expect(frNumber(0, 3)).toBe('0,000')
  })
})

describe('the filename says what the file is', () => {
  it('reduces accents to their base letter rather than dropping them', () => {
    expect(exportFilename('Par enseignant', 'Prof. Béchir', 'CAND-0003')).toBe(
      'optiedt-par-enseignant-prof-bechir-cand-0003.csv',
    )
  })

  it('keeps the candidate id, so two exports of one resource do not collide', () => {
    const a = exportFilename('Par groupe', 'L2-A1', 'CAND-0001')
    const b = exportFilename('Par groupe', 'L2-A1', 'CAND-0002')
    expect(a).not.toBe(b)
  })

  it('drops the resource segment when there is none', () => {
    expect(exportFilename('Occupation des salles', null, 'CAND-0003')).toBe(
      'optiedt-occupation-des-salles-cand-0003.csv',
    )
  })
})
