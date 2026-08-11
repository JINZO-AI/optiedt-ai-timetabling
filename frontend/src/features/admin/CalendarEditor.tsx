import { useEffect, useMemo, useState } from 'react'

import { DAY_NAMES, gridAxes } from '@/features/timetable/model'
import type { CalendarData, Holiday } from '@/types/domain'

/**
 * FR-9 — the administrator configures the calendar.
 *
 * ⚠️ **Configuration, not a constraint.** ADR-003 gives a calendar exactly two
 * effects: closing slots, after which H9 removes them from every session's
 * domain, and shifting displayed hours. Nothing here reaches the solver, and a
 * screen that "fixed" a holiday by asking for a new rule would be asking for a
 * bug (invariant 7).
 *
 * **Three things the design turns on.**
 *
 * 1. **The loaded week is shown beside the stated one.** Without it an
 *    administrator cannot tell a half-day their predecessor closed from one the
 *    institution's own files never opened, and "réinitialiser" would be a
 *    button whose effect had to be guessed.
 * 2. **The open-slot count is on screen while editing.** Closing a half-day
 *    changes what every future run can produce, and this instance has 8 spare
 *    two-period windows in the whole week (C-13). An administrator should see
 *    the margin they are spending, before spending it.
 * 3. **A calendar that leaves no room for a timetable is saved, not refused.**
 *    The honest answer is FR-12's pre-analysis naming the shortfall on the next
 *    run; a save button that overruled the institution would be deciding
 *    feasibility outside the solver.
 */
export function CalendarEditor({
  calendar,
  onSave,
  onReset,
  saving,
  error,
}: {
  calendar: CalendarData
  onSave: (payload: {
    slots: { slot: number; isOpen: boolean }[]
    holidays: Holiday[] | null
    shortenedDay: { start: string; end: string; shiftMinutes: number } | null
  }) => void
  onReset: () => void
  saving: boolean
  error: string | null
}) {
  const serverOpen = useMemo(
    () => new Set(calendar.slots.filter((s) => s.isOpen).map((s) => s.index)),
    [calendar.slots],
  )
  const [open, setOpen] = useState<Set<number>>(serverOpen)
  const [holidays, setHolidays] = useState<Holiday[]>(calendar.holidays)
  const [shortened, setShortened] = useState(calendar.shortenedDay)
  const [dirty, setDirty] = useState(false)

  // Re-seed whenever the server answers, unless there are edits in flight — the
  // same guard the availability grid uses, and for the same reason: a refetch
  // must never discard what somebody is in the middle of typing.
  useEffect(() => {
    if (!dirty) {
      setOpen(serverOpen)
      setHolidays(calendar.holidays)
      setShortened(calendar.shortenedDay)
    }
  }, [serverOpen, calendar.holidays, calendar.shortenedDay, dirty])

  const { days, periods } = gridAxes(calendar.slots)
  const loadedOpen = new Set(calendar.loadedOpenSlots)

  function toggle(index: number) {
    setDirty(true)
    setOpen((current) => {
      const next = new Set(current)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  function submit() {
    onSave({
      slots: calendar.slots.map((s) => ({ slot: s.index, isOpen: open.has(s.index) })),
      holidays,
      shortenedDay: shortened,
    })
    setDirty(false)
  }

  return (
    <>
      <section className="panel">
        <h2>Calendrier</h2>
        <p className="panel__note">
          Fermer une demi-journée retire ces créneaux de tous les emplois du temps produits
          ensuite — sans modification du code. Les fichiers de l’instance ne sont pas touchés :
          « Réinitialiser » rétablit le calendrier chargé.
        </p>

        <div className="form-row">
          <button onClick={submit} disabled={saving}>
            {saving ? 'Enregistrement…' : 'Enregistrer le calendrier'}
          </button>
          <button className="link" onClick={onReset} disabled={saving}>
            Réinitialiser
          </button>
          {dirty && <span className="state state--running">non enregistré</span>}
          {calendar.editedBy && (
            <span className="meta__item">
              Dernière modification par <b>{calendar.editedBy}</b>
            </span>
          )}
        </div>

        {error && <p className="error">Échec de l’enregistrement : {error}</p>}
      </section>

      <section className="panel">
        <table className="grid grid--availability">
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
              const sample = calendar.slots.find((s) => s.periodIndex === period)
              return (
                <tr key={period}>
                  <th className="grid__hour">
                    {sample ? `${sample.startHour}–${sample.endHour}` : `P${period}`}
                  </th>
                  {days.map((day) => {
                    const slot = calendar.slots.find(
                      (s) => s.dayIndex === day && s.periodIndex === period,
                    )
                    if (!slot) return <td key={day} className="cell cell--none" />
                    const isOpen = open.has(slot.index)
                    // A slot the loaded files open and the stated calendar
                    // closes — the only kind of cell that is a decision rather
                    // than a fact.
                    const changed = loadedOpen.has(slot.index) !== isOpen
                    return (
                      <td
                        key={day}
                        role="checkbox"
                        aria-checked={isOpen}
                        aria-label={`${DAY_NAMES[day] ?? day} ${sample?.startHour ?? period} ${
                          isOpen ? 'ouvert' : 'fermé'
                        }`}
                        tabIndex={0}
                        data-testid={`calendar-slot-${slot.index}`}
                        className={`cell cell--toggle ${isOpen ? 'cell--on' : 'cell--off'}`}
                        onClick={() => toggle(slot.index)}
                        onKeyDown={(e) => {
                          if (e.key === ' ' || e.key === 'Enter') {
                            e.preventDefault()
                            toggle(slot.index)
                          }
                        }}
                      >
                        {isOpen ? 'Ouvert' : 'Fermé'}
                        {changed && <span className="tag">modifié</span>}
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
            Créneaux ouverts <b data-testid="open-slot-count">{open.size}</b>
          </span>
          <span>
            Ouverts dans les fichiers chargés <b>{calendar.loadedOpenSlots.length}</b>
          </span>
        </div>
      </section>

      <HolidayList holidays={holidays} stated={calendar.holidaysStated} onChange={(next) => {
        setDirty(true)
        setHolidays(next)
      }} />

      <ShortenedDayFields
        value={shortened}
        shifted={calendar.shiftedHours}
        onChange={(next) => {
          setDirty(true)
          setShortened(next)
        }}
      />
    </>
  )
}

/**
 * The academic calendar's holidays.
 *
 * ⚠️ **The note about closure is not decoration.** A reader who adds "Aïd" here
 * and expects the week to change would be wrong, and would discover it only
 * after a run. ADR-003 routes a holiday through slot closure; this list is the
 * institutional record, and the grid above is what acts.
 */
function HolidayList({
  holidays,
  stated,
  onChange,
}: {
  holidays: Holiday[]
  stated: boolean
  onChange: (next: Holiday[]) => void
}) {
  const [label, setLabel] = useState('')
  const [date, setDate] = useState('')

  return (
    <section className="panel">
      <h2>Jours fériés</h2>
      <p className="panel__note">
        Enregistrer une liste remplace celle des fichiers chargés. ⚠️ Un jour férié ne ferme pas de
        créneau à lui seul : fermez les demi-journées concernées dans la grille ci-dessus (ADR-003).
      </p>
      {!stated && (
        <p className="panel__note" data-testid="holidays-not-stated">
          Aucune liste n’a encore été saisie : celle de l’instance ({holidays.length}) fait foi.
        </p>
      )}

      <div className="form-row">
        <div className="field">
          <label htmlFor="holiday-date">Date</label>
          <input
            id="holiday-date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="holiday-label">Intitulé</label>
          <input id="holiday-label" value={label} onChange={(e) => setLabel(e.target.value)} />
        </div>
        <button
          disabled={!date || !label.trim()}
          onClick={() => {
            onChange([
              ...holidays,
              { date, label: label.trim(), lunar: false, approximate: false, blocking: true },
            ])
            setDate('')
            setLabel('')
          }}
        >
          Ajouter
        </button>
      </div>

      {holidays.length === 0 ? (
        <p className="empty">Aucun jour férié.</p>
      ) : (
        <ul className="list">
          {holidays.map((h, index) => (
            <li key={`${h.date}-${h.label}`}>
              <span>
                {h.date} — {h.label}
                {h.approximate && <span className="tag">date approchée</span>}
              </span>
              <button
                className="link"
                aria-label={`Retirer ${h.label}`}
                onClick={() => onChange(holidays.filter((_, i) => i !== index))}
              >
                Retirer
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/**
 * The shortened-day window — ADR-003's second effect.
 *
 * ⚠️ **It shifts what is DISPLAYED and printed, and nothing else.** The slot
 * index does not change, so no variable and no constraint is affected. The
 * preview below exists so that is visible rather than asserted: an
 * administrator sees the hours the window produces before saving it.
 */
function ShortenedDayFields({
  value,
  shifted,
  onChange,
}: {
  value: { start: string; end: string; shiftMinutes: number } | null
  shifted: { slot: number; startHour: string; endHour: string }[]
  onChange: (next: { start: string; end: string; shiftMinutes: number } | null) => void
}) {
  const current = value ?? { start: '', end: '', shiftMinutes: 0 }
  const preview = shifted.slice(0, 5)

  return (
    <section className="panel">
      <h2>Horaire décalé</h2>
      <p className="panel__note">
        Pendant cette période, les heures affichées et imprimées sont décalées. ⚠️ Les créneaux ne
        changent pas de numéro : aucune variable ni contrainte n’est touchée (ADR-003).
      </p>

      <div className="form-row">
        <div className="field">
          <label htmlFor="shortened-start">Début</label>
          <input
            id="shortened-start"
            type="date"
            value={current.start}
            onChange={(e) => onChange({ ...current, start: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="shortened-end">Fin</label>
          <input
            id="shortened-end"
            type="date"
            value={current.end}
            onChange={(e) => onChange({ ...current, end: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="shortened-shift">Décalage (minutes)</label>
          <input
            id="shortened-shift"
            type="number"
            value={current.shiftMinutes}
            onChange={(e) => onChange({ ...current, shiftMinutes: Number(e.target.value) })}
          />
        </div>
        {value !== null && (
          <button className="link" onClick={() => onChange(null)}>
            Retirer la période
          </button>
        )}
      </div>

      {preview.length > 0 && (
        <table className="table" data-testid="shifted-preview">
          <thead>
            <tr>
              <th>Créneau</th>
              <th>Heures décalées</th>
            </tr>
          </thead>
          <tbody>
            {preview.map((row) => (
              <tr key={row.slot}>
                <td>{row.slot}</td>
                <td>
                  {row.startHour}–{row.endHour}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
