import {
  DAY_NAMES,
  gridAxes,
  occupancyBySlot,
  type Dimension,
  type Lookups,
} from '@/features/timetable/model'
import type { InstanceData, Placement } from '@/types/domain'

/**
 * FR-7 — the weekly grid for one resource.
 *
 * A closed slot is drawn as closed rather than omitted, so the week keeps its
 * shape and a closed Saturday afternoon is visibly closed rather than
 * mysteriously absent. Closed-ness comes from `slot.isOpen`, which the
 * calendar configuration drives (ADR-003, invariant 7) — the grid never
 * decides for itself that a day is closed.
 */
export function TimetableGrid({
  placements,
  instance,
  lookups,
  dimension,
}: {
  placements: Placement[]
  instance: InstanceData
  lookups: Lookups
  dimension: Dimension
}) {
  const { days, periods } = gridAxes(instance.slots)
  const cells = occupancyBySlot(placements, lookups)

  return (
    <table className="grid">
      <thead>
        <tr>
          <th className="grid__corner" />
          {days.map((day) => (
            <th key={day}>{DAY_NAMES[day] ?? `Jour ${day}`}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {periods.map((period) => {
          const sample = instance.slots.find((s) => s.periodIndex === period)
          return (
            <tr key={period}>
              <th className="grid__hour">
                {sample ? `${sample.startHour}–${sample.endHour}` : `P${period}`}
              </th>
              {days.map((day) => {
                const slot = instance.slots.find(
                  (s) => s.dayIndex === day && s.periodIndex === period,
                )
                if (!slot) return <td key={day} className="cell cell--none" />
                if (!slot.isOpen)
                  return (
                    <td key={day} className="cell cell--closed">
                      <span>fermé</span>
                    </td>
                  )

                const cell = cells.get(slot.index)
                if (!cell) return <td key={day} className="cell" />
                if (cell.continuation)
                  return <td key={day} className="cell cell--continued" />

                const { session, placement } = cell
                return (
                  <td key={day} className={`cell cell--busy cell--${session.type}`}>
                    <div className="cell__course">
                      {lookups.courseCodeById.get(session.course) ?? session.course}
                    </div>
                    <div className="cell__type">{session.type}</div>
                    <div className="cell__detail">
                      {dimension !== 'group' && (
                        <span>
                          {lookups.groupLabelById.get(session.group) ?? session.group}
                        </span>
                      )}
                      {dimension !== 'teacher' && <span>{session.teacher}</span>}
                      {dimension !== 'room' && (
                        <span>{lookups.roomCodeById.get(placement.room) ?? placement.room}</span>
                      )}
                    </div>
                  </td>
                )
              })}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
