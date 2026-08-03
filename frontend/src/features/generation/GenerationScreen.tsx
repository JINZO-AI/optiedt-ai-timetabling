import { useState } from 'react'

import { isTerminal, useCreateRun, useInstance, useRun } from '@/api/queries'
import { CandidateCard } from '@/features/generation/CandidateCard'
import type { ConstraintDefinition, RunState } from '@/types/domain'

/**
 * FR-13, FR-5, FR-6 — launch a generation and read what came back.
 *
 * The launch returns a run id immediately and the screen polls; a solve takes
 * minutes and no request is held open for it (docs/architecture.md).
 *
 * ⚠️ The budget is **deterministic time, not seconds** (ADR-011). The field is
 * labelled that way and the elapsed wall clock is shown separately, because
 * presenting the budget as a duration would make a promise the system does not
 * make: the deterministic-to-wall-clock ratio is machine-dependent.
 */
export function GenerationScreen() {
  const [runId, setRunId] = useState<string | null>(null)
  const [seed, setSeed] = useState('42')
  const [budget, setBudget] = useState('90')

  const instance = useInstance()
  const createRun = useCreateRun()
  const run = useRun(runId)

  const catalogue = new Map<string, ConstraintDefinition>(
    (instance.data?.constraints ?? []).map((c) => [c.code, c]),
  )

  const running = run.data !== undefined && !isTerminal(run.data.state)
  const launching = createRun.isPending || running

  function launch() {
    createRun.mutate(
      { seed: Number(seed), deterministicBudget: Number(budget) },
      { onSuccess: (created) => setRunId(created.runId) },
    )
  }

  return (
    <>
      <section className="panel">
        <h1>Générer un emploi du temps</h1>
        <p className="panel__note">
          Trois profils de pondération sont résolus l’un après l’autre — équilibré, favorable aux
          étudiants, favorable aux enseignants — puis les candidats obtenus sont classés sous une
          seule et même pondération.
        </p>

        <div className="form-row">
          <div className="field">
            <label htmlFor="seed">Graine</label>
            <input
              id="seed"
              value={seed}
              inputMode="numeric"
              onChange={(e) => setSeed(e.target.value)}
              disabled={launching}
            />
          </div>
          <div className="field">
            <label htmlFor="budget">Budget déterministe (pas des secondes)</label>
            <input
              id="budget"
              value={budget}
              inputMode="decimal"
              onChange={(e) => setBudget(e.target.value)}
              disabled={launching}
            />
          </div>
          <button onClick={launch} disabled={launching}>
            {launching ? 'Génération en cours…' : 'Lancer la génération'}
          </button>
        </div>

        {createRun.isError && (
          <p className="error">Le lancement a échoué : {String(createRun.error)}</p>
        )}
      </section>

      {run.data && (
        <section className="panel">
          <div className="candidate__head">
            <h2>Exécution {run.data.id}</h2>
            <StateBadge state={run.data.state} />
          </div>

          <div className="meta">
            <span>
              Graine <b>{run.data.seed}</b>
            </span>
            <span>
              Budget déterministe <b>{run.data.deterministicBudget}</b>
            </span>
            <span>
              Déterministe consommé <b>{run.data.deterministicTimeUsed.toFixed(2)}</b>
            </span>
            <span>
              Horloge <b>{run.data.wallClockSeconds.toFixed(1)} s</b>
            </span>
            <span>
              Modèle <b>{run.data.modelVersion}</b>
            </span>
          </div>

          {run.data.duplicatesRemoved.length > 0 && (
            <p className="warning">
              Doublons retirés : {run.data.duplicatesRemoved.join(', ')}. Ces profils ont produit un
              emploi du temps identique à un autre déjà obtenu.
            </p>
          )}

          {run.data.state === 'INFEASIBLE' && (
            <p className="warning">
              Aucun emploi du temps n’existe pour cette instance. Le rapport nommant les règles en
              conflit relève du diagnostic, qui n’est pas encore implémenté.
            </p>
          )}

          {run.data.error && <p className="error">{run.data.error}</p>}
        </section>
      )}

      {run.data && run.data.candidates.length > 0 && (
        <section className="panel">
          <h2>Candidats</h2>
          <p className="panel__note">
            Classés par score décroissant sous la pondération en vigueur. L’ordre est celui renvoyé
            par le serveur.
          </p>
          <div className="candidates">
            {run.data.candidates.map((candidate, index) => (
              <CandidateCard
                key={candidate.id}
                candidate={candidate}
                rank={index + 1}
                catalogue={catalogue}
                weights={run.data.weights}
              />
            ))}
          </div>
        </section>
      )}
    </>
  )
}

function StateBadge({ state }: { state: RunState }) {
  const modifier =
    state === 'COMPLETED'
      ? 'done'
      : state === 'FAILED' || state === 'INFEASIBLE'
        ? 'bad'
        : 'running'
  return <span className={`state state--${modifier}`}>{state}</span>
}
