/**
 * FR-10 — "Print or export a timetable view".
 *
 * This module is the *export* half. The *print* half is a stylesheet and a
 * button, because printing is something the browser already does well; what it
 * cannot do by itself is say **what** was printed, which is why
 * `PrintHeader.tsx` exists and why both halves draw their provenance from
 * `provenanceEntries` below rather than each formatting its own.
 *
 * ⚠️ **Why this may live in the presentation layer.** `docs/architecture.md`
 * permits the presentation layer to "display, filter, print" and forbids it to
 * "compute a score, decide an order". Everything here re-serialises figures the
 * API already sent: the row order is day-then-period — a grid axis, exactly
 * like `gridAxes` in `model.ts` — and no score, rank or placement is computed.
 * Do not add a column this file would have to work out for itself.
 *
 * **Separator and decimals are French on purpose.** The interface is French and
 * the instance is French, so the file is opened by a French spreadsheet: `;` as
 * the field separator and `,` as the decimal mark is the pairing Excel-fr reads
 * without an import dialogue. A comma-separated file with `71.4` in it opens as
 * one text column, which is an export in name only. `downloadCsv` adds a UTF-8
 * BOM for the same reason — without it `Périodes` arrives as `PÃ©riodes`.
 *
 * **The provenance preamble is not decoration.** FR-19's criterion is that a
 * published timetable traces back to its run, seed and weights; a timetable that
 * left the application carrying none of that would break the trace precisely at
 * the moment it becomes the copy someone actually argues with.
 */

import { DAY_NAMES, type Lookups, type RoomOccupancy } from '@/features/timetable/model'
import type { Candidate, Placement, Run } from '@/types/domain'

const SEPARATOR = ';'

/** French decimal mark, to match the separator above. */
export function frNumber(value: number, digits: number): string {
  return value.toFixed(digits).replace('.', ',')
}

/**
 * One CSV field, quoted only when it has to be.
 *
 * A group label or a detail string may contain the separator; unquoted, it
 * would silently split one row into two and the file would still look
 * plausible, which is the failure mode worth guarding.
 */
function field(value: string): string {
  if (!/[;"\r\n]/.test(value)) return value
  return `"${value.replace(/"/g, '""')}"`
}

/** CRLF, which is what RFC 4180 specifies and what Excel expects. */
export function toCsv(rows: string[][]): string {
  return rows.map((row) => row.map(field).join(SEPARATOR)).join('\r\n')
}

/**
 * What produced this timetable, as label/value pairs.
 *
 * One list, two renderings — the CSV writes it as rows and `PrintHeader`
 * renders it as a header — so a printed sheet and an exported file can never
 * disagree about which run they came from.
 */
export function provenanceEntries(
  run: Run,
  candidate: Candidate,
  viewLabel: string,
  resourceLabel: string | null,
): [string, string][] {
  const entries: [string, string][] = [
    ['View', viewLabel],
    ...(resourceLabel === null ? [] : ([['Resource', resourceLabel]] as [string, string][])),
    ['Run', run.id],
    ['Candidate', candidate.id],
    ['Profile', candidate.profileName],
    ['Score', `${frNumber(candidate.score, 2)} / 100`],
    ['Seed', String(run.seed)],
    ['Model version', run.modelVersion],
    // Deterministic time, never seconds (ADR-011). The parenthesis is the same
    // wording the generation screen uses; dropping it here would let a reader
    // take the figure for a duration.
    ['Search budget (deterministic units, not seconds)', frNumber(run.deterministicBudget, 2)],
  ]
  // The whole weight vector, as `TraceTable` shows it on screen: one criterion
  // omitted would make the score unrecomputable from the file.
  for (const criterion of Object.keys(run.weights).sort()) {
    entries.push([`Weight ${criterion}`, frNumber(run.weights[criterion] ?? 0, 3)])
  }
  return entries
}

const TIMETABLE_HEADER = [
  'Day',
  'Start',
  'End',
  'Periods',
  'Course',
  'Type',
  'Group',
  'Teacher',
  'Room',
]

/**
 * One row per placement, in day-then-period order.
 *
 * ⚠️ **A two-period session is ONE row**, ending at the end hour of its second
 * period. The grid draws a continuation cell so the week keeps its shape; a
 * file that copied that would report 218 sessions as 322 and overstate the
 * teaching load of every teacher in it.
 *
 * ⚠️ **Which is why `Périodes` is a column.** Two periods need not be adjacent
 * on the clock: a session in the two periods either side of the midday break
 * runs 11:50–15:30, and start-and-end alone would read as one unbroken block of
 * 3h40. The grid shows two bands and the file has to be able to say the same
 * thing. Found by exporting a real TP subgroup, not by reading the code.
 */
export function timetableRows(placements: Placement[], lookups: Lookups): string[][] {
  return [...placements]
    .sort((a, b) => a.slot - b.slot)
    .flatMap((placement) => {
      const session = lookups.sessionById.get(placement.session)
      const start = lookups.slotByIndex.get(placement.slot)
      if (!session || !start) return []
      const end = lookups.slotByIndex.get(placement.slot + session.durationPeriods - 1) ?? start
      return [
        [
          DAY_NAMES[start.dayIndex] ?? `Jour ${start.dayIndex}`,
          start.startHour,
          end.endHour,
          String(session.durationPeriods),
          lookups.courseCodeById.get(session.course) ?? session.course,
          session.type,
          lookups.groupLabelById.get(session.group) ?? session.group,
          session.teacher,
          lookups.roomCodeById.get(placement.room) ?? placement.room,
        ],
      ]
    })
}

const OCCUPANCY_HEADER = [
  'Room',
  'Type',
  'Periods occupied',
  'Open slots',
  'Occupancy rate (periods occupied / open slots, %)',
]

/**
 * FR-18's table, exported.
 *
 * ⚠️ **The C-13 caveat travels with the figures.** On screen the ratio sits
 * under a paragraph saying it counts *periods* and that the bound which
 * actually binds a laboratory is the two-period window. A bare column of
 * percentages in a spreadsheet, read without that sentence, is exactly the
 * misreading that let an infeasible instance pass verification — so the note is
 * a row of the file, not a property of the screen.
 */
export function occupancyRows(rows: RoomOccupancy[]): string[][] {
  return rows.map((row) => [
    row.code,
    row.type,
    String(row.occupiedPeriods),
    String(row.openPeriods),
    frNumber(row.ratio * 100, 1),
  ])
}

export const OCCUPANCY_CAVEAT =
  'Occupancy rate = periods occupied / open slots in the week. ' +
  'It measures TIME in use, not how full the seats are: in the international ' +
  'space-management vocabulary (the UFO framework) this is a frequency rate, ' +
  'and the word occupancy there means seats filled. For laboratories the ' +
  'bound that ' +
  'actually binds is the number of consecutive two-period windows (C-13).'
/**
 * ⚠️ **The caveat names what the rate measures, and that is not decoration.**
 *
 * The figure is `occupied periods / open periods` — C-4's `utilisation(r,k)`,
 * the same quantity `analysis/criteria.py` scores S6 against. In the SMG "UFO"
 * vocabulary used across UK/US/AU higher-education space management, that is a
 * **frequency** rate, and the word *occupancy* is reserved for seats
 * (occupants / capacity). A spreadsheet leaves this application and is read by
 * people who may know that vocabulary, so an unqualified "Taux" would invite
 * exactly the wrong reading. See C-9's resolution in `docs/open-questions.md`
 * for why the time-based reading is the right one for FR-18 — and for the
 * measurement showing the two readings *invert* on this instance.
 */

function withProvenance(provenance: [string, string][], table: string[][]): string {
  return toCsv([...provenance.map(([label, value]) => [label, value]), [], ...table])
}

export function timetableCsv(
  placements: Placement[],
  lookups: Lookups,
  provenance: [string, string][],
): string {
  return withProvenance(provenance, [TIMETABLE_HEADER, ...timetableRows(placements, lookups)])
}

export function occupancyCsv(rows: RoomOccupancy[], provenance: [string, string][]): string {
  return withProvenance(
    [...provenance, ['Note', OCCUPANCY_CAVEAT]],
    [OCCUPANCY_HEADER, ...occupancyRows(rows)],
  )
}

/**
 * A filename that says what the file is without being opened.
 *
 * Anything a filesystem argues about becomes `-`; a downloads folder holding
 * `optiedt-par-groupe-L2-INFO-G1-CAND-0003.csv` is self-describing, and the
 * candidate id keeps two exports of the same group from overwriting each other.
 */
export function exportFilename(
  viewLabel: string,
  resourceLabel: string | null,
  candidateId: string,
): string {
  const parts = ['optiedt', viewLabel, resourceLabel ?? '', candidateId].filter((p) => p !== '')
  const slug = parts
    .join('-')
    .normalize('NFD')
    // After NFD an accented letter is an ASCII base plus a combining mark, so
    // dropping every non-ASCII code point turns "é" into "e". Doing it the
    // other way round — straight to the class below — would turn it into a
    // separator instead and give "p-riodes".
    .replace(/[^\x00-\x7F]/g, '')
    .replace(/[^A-Za-z0-9-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .toLowerCase()
  return `${slug}.csv`
}

/**
 * Written as a code point rather than typed, because an invisible character in
 * a source file is one careless re-encoding away from silently disappearing.
 */
const BYTE_ORDER_MARK = String.fromCharCode(0xfeff)

/**
 * Hand the file to the browser.
 *
 * The BOM is required: without it Excel reads the file as the local ANSI
 * codepage and every accented heading arrives mangled.
 */
export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob([BYTE_ORDER_MARK + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
