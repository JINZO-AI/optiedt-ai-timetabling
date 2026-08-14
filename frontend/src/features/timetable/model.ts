/**
 * Turning placements into something a person can read.
 *
 * This is display logic only. It filters and arranges what the API sent: it
 * computes **no score** and decides **no ranking** — which is the boundary
 * `docs/architecture.md` draws, the presentation layer being allowed to
 * "display, filter, print" and forbidden to "compute a score, decide an
 * order". The sorts below order grid axes and room codes, not candidates by
 * quality; do not read them as licence to rank anything.
 *
 * A `Placement` carries ids alone, so every label here comes from the instance
 * payload.
 */

import type {
  Candidate,
  Group,
  InstanceData,
  Placement,
  Session,
  Slot,
} from '@/types/domain'

/**
 * Weekday names for the grid header.
 *
 * ⚠️ UI chrome, not instance data. `slots.csv` carries a `day_name` column the
 * loader does not read, so translating here changes no data and breaks no
 * `verify-instance` figure. Domain vocabulary that IS data — CM/TD/TP, Amphi,
 * Salle, Lab_Info — stays verbatim (docs/domain-model.md).
 */
export const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

export interface Lookups {
  sessionById: Map<string, Session>
  groupById: Map<string, Group>
  slotByIndex: Map<number, Slot>
  courseCodeById: Map<string, string>
  roomCodeById: Map<string, string>
  groupLabelById: Map<string, string>
}

export function buildLookups(instance: InstanceData): Lookups {
  return {
    sessionById: new Map(instance.sessions.map((s) => [s.id, s])),
    groupById: new Map(instance.groups.map((g) => [g.id, g])),
    slotByIndex: new Map(instance.slots.map((s) => [s.index, s])),
    courseCodeById: new Map(instance.courses.map((c) => [c.id, c.code])),
    roomCodeById: new Map(instance.rooms.map((r) => [r.id, r.code])),
    groupLabelById: new Map(instance.groups.map((g) => [g.id, g.label])),
  }
}

/**
 * A group and every group above it, promotion last.
 *
 * The chain is promotion → tutorial group → laboratory subgroup, and it is why
 * a subgroup's timetable is not just its own sessions: a CM gathers the whole
 * promotion, so its students sit through it too. Showing a TP subgroup only
 * the sessions addressed to it would display a week with holes the students do
 * not actually have. Same relation H12 uses in the solver — reimplemented here
 * over plain data, as the analysis layer does.
 */
export function ancestorsOrSelf(groupId: string, groupById: Map<string, Group>): string[] {
  const chain: string[] = []
  let current: string | null = groupId
  // Bounded by the chain length rather than by `while (current)`: a malformed
  // parent cycle in the data would otherwise hang the interface.
  for (let depth = 0; depth < 8 && current !== null; depth += 1) {
    chain.push(current)
    current = groupById.get(current)?.parentGroup ?? null
  }
  return chain
}

export type Dimension = 'teacher' | 'group' | 'room'

/** The placements one resource is concerned by, on one candidate. */
export function placementsFor(
  candidate: Candidate,
  dimension: Dimension,
  resourceId: string,
  lookups: Lookups,
): Placement[] {
  if (dimension === 'room') {
    return candidate.placements.filter((p) => p.room === resourceId)
  }
  if (dimension === 'teacher') {
    return candidate.placements.filter(
      (p) => lookups.sessionById.get(p.session)?.teacher === resourceId,
    )
  }
  const reaching = new Set(ancestorsOrSelf(resourceId, lookups.groupById))
  return candidate.placements.filter((p) => {
    const group = lookups.sessionById.get(p.session)?.group
    return group !== undefined && reaching.has(group)
  })
}

export interface OccupiedCell {
  placement: Placement
  session: Session
  /** True on the second period of a two-period session, so it is not drawn twice. */
  continuation: boolean
}

/**
 * Which slot each placement occupies, expanded over its duration.
 *
 * 104 of the 218 sessions span two periods, and a two-period session must fit
 * inside one day (H8), so slot+1 never crosses a day boundary.
 */
export function occupancyBySlot(
  placements: Placement[],
  lookups: Lookups,
): Map<number, OccupiedCell> {
  const cells = new Map<number, OccupiedCell>()
  for (const placement of placements) {
    const session = lookups.sessionById.get(placement.session)
    if (!session) continue
    for (let step = 0; step < session.durationPeriods; step += 1) {
      cells.set(placement.slot + step, {
        placement,
        session,
        continuation: step > 0,
      })
    }
  }
  return cells
}

/** Distinct day and period indices actually present in the grid. */
export function gridAxes(slots: Slot[]): { days: number[]; periods: number[] } {
  const days = [...new Set(slots.map((s) => s.dayIndex))].sort((a, b) => a - b)
  const periods = [...new Set(slots.map((s) => s.periodIndex))].sort((a, b) => a - b)
  return { days, periods }
}

export interface RoomOccupancy {
  roomId: string
  code: string
  type: string
  occupiedPeriods: number
  openPeriods: number
  ratio: number
}

/**
 * FR-18 — how heavily each room is used on one candidate.
 *
 * ⚠️ **This formula is not local to the display layer, and changing it here
 * alone would be a defect.** It is `utilisation(r,k)` exactly as **C-4**
 * defined it on 2026-07-30 — occupied periods over open slots — the same
 * quantity `analysis/criteria.py` measures S6's deviation against and
 * `solver/objective.py` encodes for CP-SAT. Three implementations of one
 * definition; C-4 records what the last divergence between two of them cost
 * (S6 priced 28× too high, caught by review rather than by a test).
 *
 * Counted against **open** slots only: a closed half-day is configuration
 * (`slot.is_open`, ADR-003), and counting it as unused capacity would make
 * every room look emptier than it is. ⚠️ Since Phase 11 an administrator can
 * close a half-day through the interface, so this denominator **moves** — that
 * is correct, and `model.test.ts` pins it.
 *
 * ⚠️ It measures **time**, not seats. In the SMG "UFO" vocabulary standard in
 * higher-education space management this is a *frequency* rate, and
 * "occupancy" means occupants over capacity — two readings that **invert** on
 * this instance. C-9's resolution records why the time reading is FR-18's:
 * SRS Table 36 puts FR-18 among the *views*, beside the teacher and group
 * views, which show when a resource is busy.
 *
 * ⚠️ This is the *period* figure. For the laboratories it is the reassuring
 * one — the bound that actually binds is two-period windows, and reading the
 * period figure alone is what let an infeasible instance pass verification
 * (C-13). It is fine here, where nothing is being judged feasible; do not
 * carry it into a feasibility check.
 */
export function roomOccupancy(
  candidate: Candidate,
  instance: InstanceData,
  lookups: Lookups,
): RoomOccupancy[] {
  const openPeriods = instance.slots.filter((s) => s.isOpen).length
  const used = new Map<string, number>()
  for (const placement of candidate.placements) {
    const session = lookups.sessionById.get(placement.session)
    if (!session) continue
    used.set(placement.room, (used.get(placement.room) ?? 0) + session.durationPeriods)
  }
  return instance.rooms
    .map((room) => {
      const occupied = used.get(room.id) ?? 0
      return {
        roomId: room.id,
        code: room.code,
        type: room.type,
        occupiedPeriods: occupied,
        openPeriods,
        ratio: openPeriods === 0 ? 0 : occupied / openPeriods,
      }
    })
    .sort((a, b) => a.type.localeCompare(b.type) || a.code.localeCompare(b.code))
}
