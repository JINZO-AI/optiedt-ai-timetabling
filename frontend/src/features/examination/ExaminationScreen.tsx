/**
 * FR-20 — generate and consult the timetable of an examination session.
 *
 * ⚠️ **The examinations are DERIVED, so this screen asks for no examination
 * data.** One examination per course, its candidates the students of the
 * course's promotion, its supervisor the CM teacher, its period the two
 * calendar keys — C-23 and ADR-013. A form collecting examinations here would
 * be the examination-data upload system FR-1 was deliberately scoped not to
 * become (SRS §4.1 names no such form).
 *
 * ⚠️ **202 and poll, like the generation screen.** A solve takes about half a
 * minute and no HTTP request is held open for it (ADR-005).
 *
 * ⚠️ **A refusal is shown verbatim and is not styled as a crash.** The common
 * case is a department dataset with no roster: `students.csv` is not one of the
 * eleven files FR-1 admits, and X1 and X2 are both about students. "Aucun
 * étudiant" with the reason is actionable; "échec" is not.
 */

import { useState } from 'react'

import { useExamRun, useGenerateExamSession } from '@/api/queries'
import { ExamCalendar } from '@/features/examination/ExamCalendar'
import type { ExamRun } from '@/types/domain'

/** The two presets a user actually chooses between, in their own words.
 *
 * ⚠️ This is U2's lesson applied at the point of writing rather than retrofitted.
 * The generation screen shipped with `Graine` and `Budget déterministe (pas des
 * secondes)` — two raw solver parameters — and the first-use session reported
 * that users "do not understand the purpose of each action". A deterministic
 * budget is a unit of WORK, not of time (ADR-011), which is precisely why it
 * cannot be labelled "seconds" and must not be shown raw.
 */
const PRESETS = [
  {
    id: 'quick',
    label: 'Rapide',
    hint: 'Un premier calendrier en une trentaine de secondes.',
    deterministicBudget: 10,
  },
  {
    id: 'thorough',
    label: 'Approfondi',
    hint: 'Cherche plus longtemps un meilleur étalement des examens.',
    deterministicBudget: 60,
  },
] as const

export function ExaminationScreen() {
  const [runId, setRunId] = useState<string | null>(null)
  const [preset, setPreset] = useState<(typeof PRESETS)[number]['id']>('quick')
  const generate = useGenerateExamSession()
  const run = useExamRun(runId)

  const chosen = PRESETS.find((p) => p.id === preset) ?? PRESETS[0]
  const current = run.data
  const running =
    generate.isPending ||
    (current !== undefined && !['COMPLETED', 'FAILED', 'INFEASIBLE'].includes(current.state))

  function launch() {
    generate.mutate(
      { seed: 42, deterministicBudget: chosen.deterministicBudget },
      { onSuccess: (created) => setRunId(created.id) },
    )
  }

  return (
    <section className="screen">
      <h2>Session d’examens</h2>
      <p className="screen__lead">
        Un examen par matière, placé sur la période d’examens configurée dans
        l’administration. Les candidats sont les étudiants de la promotion
        concernée et le surveillant est l’enseignant du cours magistral.
      </p>

      <fieldset className="exam-controls">
        <legend>Durée de la recherche</legend>
        {PRESETS.map((option) => (
          <label key={option.id} className="exam-controls__option">
            <input
              type="radio"
              name="preset"
              value={option.id}
              checked={preset === option.id}
              onChange={() => setPreset(option.id)}
              disabled={running}
            />
            <span>
              <strong>{option.label}</strong>
              <small>{option.hint}</small>
            </span>
          </label>
        ))}
        <button onClick={launch} disabled={running}>
          {running ? 'Calcul en cours…' : 'Générer le calendrier'}
        </button>
      </fieldset>

      {generate.isError && (
        <p className="warning">
          La génération n’a pas pu être lancée. Seul le responsable des emplois
          du temps peut générer une session d’examens.
        </p>
      )}

      {runId === null && !generate.isPending && (
        <p className="empty">
          Aucune session d’examens n’a encore été générée. Choisissez une durée
          de recherche puis lancez la génération : le calendrier apparaîtra ici.
        </p>
      )}

      {current && <RunStatus run={current} />}
      {current && <ExamCalendar run={current} />}
    </section>
  )
}

function RunStatus({ run }: { run: ExamRun }) {
  if (run.state === 'FAILED') {
    return (
      <div className="warning" role="alert">
        <strong>La session d’examens n’a pas pu être construite.</strong>
        {/* Verbatim: the server's reason is actionable and a paraphrase would
            not be. See the module docstring. */}
        <p>{run.error}</p>
      </div>
    )
  }
  if (run.state === 'INFEASIBLE') {
    return (
      <div className="warning" role="alert">
        <strong>Aucun calendrier ne satisfait les contraintes X1 à X4.</strong>
        <p>
          La période d’examens est trop courte, ou les salles ne suffisent pas
          pour le nombre de candidats. Allongez la période dans l’administration
          puis relancez.
        </p>
      </div>
    )
  }
  if (run.state !== 'COMPLETED') {
    return <p className="pending">Calcul en cours… ({run.state})</p>
  }
  return (
    <p className="success">
      Calendrier généré
      {run.provenOptimal ? ', optimalité prouvée' : ''}
      {run.wallClockSeconds !== null && ` en ${run.wallClockSeconds.toFixed(1)} s`}.
    </p>
  )
}
