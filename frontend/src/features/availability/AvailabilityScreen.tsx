import { useEffect, useMemo, useState } from 'react'

import { useAvailability, useDeclareAvailability, useInstance } from '@/api/queries'
import { DAY_NAMES, gridAxes } from '@/features/timetable/model'
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
 * screen with no scrolling, no save dialog to hunt for, and the generated rows
 * shown as generated so a teacher can see what the system assumed on their
 * behalf before they overwrite it.
 *
 * A closed slot cannot be toggled. It is configuration (`slot.isOpen`,
 * ADR-003), and nothing is placed there whatever a teacher says — offering a
 * choice that has no effect would be a lie the interface tells.
 */
export function AvailabilityScreen() {
  const instance = useInstance()
  const [teacherId, setTeacherId] = useState<string | null>(null)
  const selectedTeacher = teacherId ?? instance.data?.teachers[0]?.id ?? null

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

  if (instance.isLoading) return <p className="empty">Chargement…</p>
  if (!instance.data) return <p className="error">Instance indisponible.</p>

  const { days, periods } = gridAxes(instance.data.slots)

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
    <>
      <section className="panel">
        <h1>Déclarer mes indisponibilités</h1>
        <p className="panel__note">
          Cliquez une case — ou faites glisser — pour basculer entre disponible et indisponible. Les
          créneaux fermés par le calendrier ne sont pas modifiables : rien n’y est jamais placé.
        </p>

        <div className="form-row">
          <div className="field">
            <label htmlFor="teacher">Enseignant</label>
            <select
              id="teacher"
              value={selectedTeacher ?? ''}
              onChange={(e) => setTeacherId(e.target.value)}
            >
              {instance.data.teachers.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.id} — {t.rank}
                </option>
              ))}
            </select>
          </div>
          <button onClick={submit} disabled={!dirty || save.isPending}>
            {save.isPending ? 'Enregistrement…' : 'Enregistrer'}
          </button>
          {dirty && <span className="state state--running">non enregistré</span>}
        </div>

        {isSynthetic && !dirty && (
          <p className="warning">
            Cette déclaration a été <b>générée</b>, pas saisie par l’enseignant. Elle existe seulement
            pour que l’instance soit résoluble avant toute connexion. Enregistrer la remplacera.
          </p>
        )}

        {save.isError && <p className="error">Échec de l’enregistrement : {String(save.error)}</p>}
      </section>

      <section className="panel">
        <table
          className="grid grid--availability"
          onPointerUp={() => setPainting(null)}
          onPointerLeave={() => setPainting(null)}
        >
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
                          <span>fermé</span>
                        </td>
                      )

                    const off = unavailable.has(slot.index)
                    return (
                      <td
                        key={day}
                        role="checkbox"
                        aria-checked={!off}
                        aria-label={`${DAY_NAMES[day] ?? day} ${sample?.startHour ?? period} ${
                          off ? 'indisponible' : 'disponible'
                        }`}
                        tabIndex={0}
                        data-testid={`slot-${slot.index}`}
                        className={`cell cell--toggle ${off ? 'cell--off' : 'cell--on'}`}
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
                        {off ? 'Indisponible' : 'Disponible'}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>

        <div className="meta">
          <span>
            Indisponibilités déclarées <b>{unavailable.size}</b>
          </span>
          <span>
            Créneaux ouverts <b>{instance.data.slots.filter((s) => s.isOpen).length}</b>
          </span>
        </div>
      </section>
    </>
  )
}
