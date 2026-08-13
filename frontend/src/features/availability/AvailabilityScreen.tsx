import { useEffect, useMemo, useState } from 'react'

import {
  useAvailability,
  useCurrentUser,
  useDeclareAvailability,
  useInstance,
} from '@/api/queries'
import { userMessage } from '@/api/errors'
import { DAY_NAMES, gridAxes } from '@/features/timetable/model'
import { Page } from '@/shell/Page'
import type { AvailabilityState } from '@/types/domain'

/**
 * FR-2 — a teacher declares availability on the weekly grid.
 *
 * ⚠️ **Two states, available and unavailable** — C-12, decided 2026-08-01.
 * `teacher_availability.csv` carries a boolean, so a third *Preferred* cell
 * would collect an answer with nowhere to record it. `AvailabilityState` and
 * the API's `AvailabilityCellIn` already admit `PREFERRED`, deliberately, so
 * adopting a real preferred-window column later changes the instance, the
 * loader and this component — not the wire format.
 *
 * The acceptance criterion is **"filled in under 5 minutes without training"**,
 * which drives the whole design: click or drag to toggle, the whole week on one
 * screen with no scrolling, the save button always in reach in the page bar,
 * and the generated rows shown as generated so a teacher can see what the
 * system assumed on their behalf before they overwrite it.
 *
 * A closed slot cannot be toggled. It is configuration (`slot.isOpen`,
 * ADR-003), and nothing is placed there whatever a teacher says — offering a
 * choice that has no effect would be a lie the interface tells.
 */
export function AvailabilityScreen() {
  const instance = useInstance()
  const me = useCurrentUser()
  const [teacherId, setTeacherId] = useState<string | null>(null)

  // ⚠️ A TEACHER edits their own grid and no one else's, and which teacher
  // that is comes from the TOKEN (FR-11). Until Phase 5 this screen offered a
  // dropdown of all 44 and the API believed whichever id was in the path.
  //
  // The dropdown remains for the person in charge, who has read and write on
  // all data (SRS Table 2). Hiding it from a teacher is a convenience, not the
  // protection: the API refuses another teacher's grid with 403 regardless.
  const ownTeacher = me.data?.role === 'TEACHER' ? me.data.teacher : null
  const mayChooseTeacher = me.data !== undefined && me.data.role !== 'TEACHER'
  const selectedTeacher = ownTeacher ?? teacherId ?? instance.data?.teachers[0]?.id ?? null

  const declared = useAvailability(selectedTeacher)
  const save = useDeclareAvailability(selectedTeacher)

  /** Slot indices the teacher is unavailable for. The grid's whole state. */
  const [unavailable, setUnavailable] = useState<Set<number>>(new Set())
  const [dirty, setDirty] = useState(false)
  const [painting, setPainting] = useState<AvailabilityState | null>(null)

  const serverUnavailable = useMemo(
    () => new Set((declared.data ?? []).map((row) => row.slot)),
    [declared.data],
  )
  const isSynthetic = (declared.data ?? []).some((row) => row.source === 'SYNTHETIC')

  // Re-seed from the server whenever the teacher changes or a save lands.
  // Guarded on `dirty` so a poll cannot discard edits in progress.
  useEffect(() => {
    if (!dirty) setUnavailable(new Set(serverUnavailable))
  }, [serverUnavailable, dirty])

  useEffect(() => {
    setDirty(false)
  }, [selectedTeacher])

  if (instance.isLoading)
    return (
      <Page title="Availability">
        <p className="empty">Loading…</p>
      </Page>
    )

  if (!instance.data)
    return (
      <Page title="Availability">
        <p className="error" role="alert">
          The department data could not be loaded. Reload the page, or sign in again if the problem
          continues.
        </p>
      </Page>
    )

  const { days, periods } = gridAxes(instance.data.slots)
  const openSlots = instance.data.slots.filter((s) => s.isOpen).length

  function toggle(slotIndex: number, forced?: AvailabilityState) {
    setDirty(true)
    setUnavailable((current) => {
      const next = new Set(current)
      const target = forced ?? (next.has(slotIndex) ? 'AVAILABLE' : 'UNAVAILABLE')
      if (target === 'UNAVAILABLE') next.add(slotIndex)
      else next.delete(slotIndex)
      return next
    })
  }

  function submit() {
    save.mutate(
      {
        semester: 2,
        cells: [...unavailable].sort((a, b) => a - b).map((slot) => ({
          slot,
          state: 'UNAVAILABLE' as const,
        })),
      },
      { onSuccess: () => setDirty(false) },
    )
  }

  return (
    <Page
      title="Availability"
      subtitle={
        selectedTeacher
          ? `${selectedTeacher} · ${unavailable.size} of ${openSlots} open slots declared unavailable`
          : undefined
      }
      status={
        dirty ? (
          <span className="badge badge--warn">Unsaved</span>
        ) : save.isSuccess ? (
          <span className="badge badge--ok">Saved</span>
        ) : undefined
      }
      actions={
        <>
          {mayChooseTeacher && (
            <label className="bar-field">
              <span>Teacher</span>
              <select
                aria-label="Teacher"
                value={selectedTeacher ?? ''}
                onChange={(e) => setTeacherId(e.target.value)}
              >
                {instance.data.teachers.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.id} — {t.rank}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button onClick={submit} disabled={!dirty || save.isPending}>
            {save.isPending ? 'Saving…' : 'Save availability'}
          </button>
        </>
      }
    >
      {isSynthetic && !dirty && (
        <p className="warning">
          <b>This declaration was generated, not entered by you.</b> It exists only so the instance
          can be solved before anyone signs in. Saving replaces it with your own.
        </p>
      )}

      {save.isError && (
        <p className="error" role="alert">
          {userMessage(save.error, 'save')}
        </p>
      )}

      <section className="section">
        <p className="screen__lead">
          Click a cell — or drag across several — to switch it between available and unavailable.
          Slots the academic calendar closes cannot be changed: nothing is ever scheduled in them.
        </p>

        <div className="gridwrap">
          <table
            className="grid grid--availability"
            onPointerUp={() => setPainting(null)}
            onPointerLeave={() => setPainting(null)}
          >
            <thead>
              <tr>
                <th className="grid__corner" />
                {days.map((day) => (
                  <th key={day}>{DAY_NAMES[day] ?? `Day ${day}`}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {periods.map((period) => {
                const sample = instance.data.slots.find((s) => s.periodIndex === period)
                return (
                  <tr key={period}>
                    <th className="grid__hour">
                      {sample ? `${sample.startHour}–${sample.endHour}` : `P${period}`}
                    </th>
                    {days.map((day) => {
                      const slot = instance.data.slots.find(
                        (s) => s.dayIndex === day && s.periodIndex === period,
                      )
                      if (!slot) return <td key={day} className="cell cell--none" />
                      if (!slot.isOpen)
                        return (
                          <td key={day} className="cell cell--closed">
                            <span>Closed</span>
                          </td>
                        )

                      const off = unavailable.has(slot.index)
                      return (
                        <td
                          key={day}
                          role="checkbox"
                          aria-checked={!off}
                          aria-label={`${DAY_NAMES[day] ?? day} ${sample?.startHour ?? period} ${
                            off ? 'Unavailable' : 'Available'
                          }`}
                          tabIndex={0}
                          data-testid={`slot-${slot.index}`}
                          className={`cell cell--toggle ${off ? 'cell--off' : 'cell--on'}`}
                          title={off ? 'Unavailable — click to make available' : 'Available — click to declare unavailable'}
                          onPointerDown={() => {
                            const target: AvailabilityState = off ? 'AVAILABLE' : 'UNAVAILABLE'
                            setPainting(target)
                            toggle(slot.index, target)
                          }}
                          onPointerEnter={() => {
                            if (painting) toggle(slot.index, painting)
                          }}
                          onKeyDown={(e) => {
                            if (e.key === ' ' || e.key === 'Enter') {
                              e.preventDefault()
                              toggle(slot.index)
                            }
                          }}
                        >
                          {/* ⚠️ **Only the DECLARED state is written.** V1
                              printed "AVAILABLE" into every cell, so a normal
                              week — a teacher free almost everywhere — shouted
                              the same word thirty times and the four cells
                              that actually carried a decision vanished into
                              it. Available is now a quiet fill; the accessible
                              name above still says both, so a screen-reader
                              user loses nothing. */}
                          {off ? 'Unavailable' : ''}
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="grid-key">
          <span className="grid-key__item">
            <span className="grid-key__swatch grid-key__swatch--on" /> Available for teaching
          </span>
          <span className="grid-key__item">
            <span className="grid-key__swatch grid-key__swatch--off" /> Declared unavailable
          </span>
          <span className="grid-key__item">
            <span className="grid-key__swatch grid-key__swatch--closed" /> Closed by the calendar —
            cannot be changed
          </span>
        </div>
      </section>
    </Page>
  )
}
