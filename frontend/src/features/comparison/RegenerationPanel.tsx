import { useState } from 'react'

import type { RegenerateRequest } from '@/api/queries'
import type { Candidate, ConstraintDefinition, Run } from '@/types/domain'

/**
 * FR-23 — accept a recommendation and regenerate.
 *
 * ⚠️ **This control does not change a timetable, and the wording on screen says
 * so in as many words.** Accepting a recommendation changes ONE solver input
 * and launches a **new run** through the same engine (ADR-007, invariant 3).
 * The candidate on screen is untouched and stays readable afterwards — it is a
 * new candidate under a new run that carries the answer (invariant 6).
 *
 * That distinction is the whole reason the feature is defensible, and it is
 * exactly the thing a button labelled "improve this timetable" would destroy.
 * A reader who believes the system edited their timetable has no reason to
 * trust that H1–H12 still hold in it.
 *
 * **Only the three catalogue actions are offered.** There is no free-text
 * field, and a suggestion matching no action type is displayed as a remark
 * carrying no control to act on it. `RegenerateRequest` is a union, so a fourth
 * option here is a type error rather than a convention.
 *
 * ⚠️ **The panel computes nothing.** The weights it shows come from the run,
 * the sessions from the candidate's placements. It arranges them for display,
 * which is what the presentation layer is permitted to do.
 */
export function RegenerationPanel({
  run,
  candidate,
  catalogue,
  onAccept,
  pending,
  error,
  launched,
}: {
  run: Run
  candidate: Candidate
  catalogue: Map<string, ConstraintDefinition>
  onAccept: (action: RegenerateRequest) => void
  pending: boolean
  error: string | null
  /** The id of the run the last acceptance launched, or null. */
  launched: string | null
}) {
  const criteria = Object.keys(run.weights).sort()
  // Sorted before the default is taken from it: the initial selection has to be
  // the one the reader SEES first, or the form acts on a session they did not
  // choose and did not notice was chosen for them.
  const sessions = candidate.placements.map((p) => p.session).sort()

  const [kind, setKind] = useState<RegenerateRequest['kind']>('weight_delta')
  const [criterion, setCriterion] = useState(criteria[0] ?? '')
  const [weight, setWeight] = useState('')
  const [session, setSession] = useState(sessions[0] ?? '')

  const current = run.weights[criterion]

  function submit() {
    if (kind === 'weight_delta') {
      const value = Number(weight)
      if (!Number.isFinite(value) || value < 0) return
      onAccept({ kind: 'weight_delta', criterion, newWeight: value })
    } else if (kind === 'lock_session') {
      onAccept({ kind: 'lock_session', session })
    } else {
      const placement = candidate.placements.find((p) => p.session === session)
      if (!placement) return
      onAccept({ kind: 'exclude_slot', session, slot: placement.slot })
    }
  }

  return (
    <>
      <p className="panel__note">
        Accepter une recommandation ne modifie <b>pas</b> ce candidat. Elle change{' '}
        <b>une seule donnée d’entrée</b> et lance une <b>nouvelle exécution</b> par le même solveur :
        H1–H12 sont déclarées à l’identique, donc elles tiennent dans le nouveau candidat pour la
        même raison qu’elles tenaient dans celui-ci. Le candidat affiché reste consultable.
      </p>

      <div className="form-row">
        <div className="field">
          <label htmlFor="regen-kind">Action</label>
          <select
            id="regen-kind"
            value={kind}
            onChange={(e) => setKind(e.target.value as RegenerateRequest['kind'])}
          >
            <option value="weight_delta">Modifier un poids (weight_delta)</option>
            <option value="lock_session">Figer une séance (lock_session)</option>
            <option value="exclude_slot">Écarter un créneau (exclude_slot)</option>
          </select>
        </div>

        {kind === 'weight_delta' ? (
          <>
            <div className="field">
              <label htmlFor="regen-criterion">Critère</label>
              <select
                id="regen-criterion"
                value={criterion}
                onChange={(e) => setCriterion(e.target.value)}
              >
                {criteria.map((code) => (
                  <option key={code} value={code}>
                    {code} — {catalogue.get(code)?.name ?? code} (actuel {run.weights[code]})
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="regen-weight">Nouveau poids</label>
              <input
                id="regen-weight"
                type="number"
                min="0"
                step="0.05"
                value={weight}
                placeholder={current === undefined ? '' : String(current)}
                onChange={(e) => setWeight(e.target.value)}
              />
            </div>
          </>
        ) : (
          <div className="field">
            <label htmlFor="regen-session">Séance</label>
            <select
              id="regen-session"
              value={session}
              onChange={(e) => setSession(e.target.value)}
            >
              {sessions.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="field">
          {/* Spacer, to line the button up with the labelled fields beside it.
              ⚠️ NOT a <label htmlFor="regen-submit">: that associates with the
              button and REPLACES its accessible name with the spacer's own
              text, so a screen reader announces an unnamed control. Caught by
              RegenerationPanel.test, which could not find the button by name. */}
          <span className="field__label-spacer" aria-hidden="true" />
          <button id="regen-submit" type="button" onClick={submit} disabled={pending}>
            {pending ? 'Lancement…' : 'Accepter et régénérer'}
          </button>
        </div>
      </div>

      {kind === 'exclude_slot' && (
        <p className="panel__note">
          Le créneau écarté est celui que la séance occupe dans ce candidat. Le solveur devra lui en
          trouver un autre.
        </p>
      )}

      {error !== null && <p className="warning">{error}</p>}

      {launched !== null && (
        <p className="panel__note">
          <b>Nouvelle exécution lancée : {launched}.</b> Ce candidat-ci est inchangé. La nouvelle
          exécution passe par les mêmes étapes que toute autre — vérifications, résolution,
          notation — et apparaîtra dans le sélecteur d’exécutions ci-dessus une fois terminée.
        </p>
      )}

      {run.origin !== null && (
        <p className="panel__note">
          Cette exécution est elle-même issue d’une recommandation acceptée sur{' '}
          <b>{run.origin.run}</b> : {run.origin.actionDetail}. Les contraintes déjà acceptées sont
          conservées et la nouvelle s’y ajoute.
        </p>
      )}
    </>
  )
}
