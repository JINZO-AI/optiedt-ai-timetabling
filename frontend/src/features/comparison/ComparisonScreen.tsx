import { useMemo, useState } from 'react'

import {
  useComparison,
  useDominance,
  useInstance,
  useRecommendation,
  useRegenerate,
  useRun,
  useRuns,
} from '@/api/queries'
import { AssistantPanel } from '@/features/assistant/AssistantPanel'
import { ContributionsTable } from '@/features/comparison/ContributionsTable'
import { DominanceNotice } from '@/features/comparison/DominanceNotice'
import { RegenerationPanel } from '@/features/comparison/RegenerationPanel'
import type { Candidate, ConstraintDefinition } from '@/types/domain'

/**
 * FR-14 and FR-15 — two candidates side by side, and why they differ.
 *
 * Both candidates are priced by the run's **weights in force**, one vector for
 * the whole portfolio. A candidate's `profileName` is provenance — how it was
 * obtained — never its own scoring weight: the exact-decomposition identity
 * only holds when the same w_i prices both sides.
 *
 * **The dominance signal landed in Phase 6 M1**, once **C-14** was resolved.
 * Phase 4 shipped none at all, deliberately: under the strict reading then in
 * force the only signal both specification documents described — "a dominated
 * *top* candidate" — is provably unreachable, and a control that never fires
 * teaches the reader it means "no problem found". What is displayed now is
 * dominance *anywhere in the portfolio*, under the standard Pareto rule.
 *
 * ⚠️ **The screen does not claim what a profile "favours", and the reason
 * changed on 2026-08-07 while the rule did not.** This comment used to cite
 * **C-15** as open — "the objective weights raw violation counts of
 * incomparable scale, so teacher-favouring measurably improves S5 and not S3".
 * **C-15 was resolved by refuting exactly that diagnosis**: the objective
 * formulation is sound and unchanged, and what was wrong was which criteria the
 * profile raised (S5 is an admitted proxy — C-12). `teacher-favouring` now
 * raises S3 and S4, and S3 went 29 → 0.
 *
 * The rule stands for a better reason. A favouring profile promises the best
 * value of its **headline** criterion, not a win across its constituency — the
 * teacher criteria genuinely conflict, and solving S3 alone drives S5 to 113.
 * So a caption reading "favours teachers" would still overstate what the
 * screen can show. The measured sub-scores are displayed instead, and they
 * speak for themselves.
 */
/**
 * One precision for every figure on this screen.
 *
 * ⚠️ Scores and the difference **must** be shown at the same precision, or the
 * screen contradicts itself in front of the one reader it is built for. Two
 * candidates scoring 79.8163 and 79.7943 display as "79.82" and "79.79" at two
 * decimals; a head of department subtracts those and gets 0.03, while the
 * decomposition correctly totals 0.02 — the true difference is 0.022. Nothing
 * is wrong with either figure, and the page still looks like it cannot add up.
 * At three decimals the same pair reads 79.816, 79.794 and +0.022, and the
 * subtraction works by hand.
 */
const COMPARISON_DIGITS = 3

export function ComparisonScreen() {
  const runs = useRuns()
  const instance = useInstance()

  const withCandidates = (runs.data ?? []).filter((r) => r.candidateCount >= 2)
  const [runId, setRunId] = useState<string | null>(null)
  const selectedRunId = runId ?? withCandidates[0]?.id ?? null
  const run = useRun(selectedRunId)
  const recommendation = useRecommendation(selectedRunId)

  const candidates = run.data?.candidates ?? []
  const [aId, setAId] = useState<string | null>(null)
  const [bId, setBId] = useState<string | null>(null)
  const a = candidates.find((c) => c.id === aId) ?? candidates[0]
  const b = candidates.find((c) => c.id === bId) ?? candidates[1]

  const comparison = useComparison(selectedRunId, a?.id ?? null, b?.id ?? null)
  const dominance = useDominance(selectedRunId)
  const regenerate = useRegenerate(selectedRunId)
  const [launched, setLaunched] = useState<string | null>(null)

  const catalogue = useMemo(
    () =>
      new Map<string, ConstraintDefinition>(
        (instance.data?.constraints ?? []).map((c) => [c.code, c]),
      ),
    [instance.data],
  )

  if (runs.isLoading) return <p className="empty">Chargement…</p>
  if (withCandidates.length === 0)
    return (
      <p className="empty">
        Aucune exécution ne comporte deux candidats à comparer. Lancez une génération d’abord.
      </p>
    )

  return (
    <>
      <section className="panel">
        <h1>Comparer deux candidats</h1>

        <div className="form-row">
          <div className="field">
            <label htmlFor="run">Exécution</label>
            <select
              id="run"
              value={selectedRunId ?? ''}
              onChange={(e) => {
                setRunId(e.target.value)
                setAId(null)
                setBId(null)
              }}
            >
              {withCandidates.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.id} — {r.candidateCount} candidat(s)
                </option>
              ))}
            </select>
          </div>

          <CandidatePicker
            id="candidate-a"
            label="Candidat A"
            candidates={candidates}
            value={a?.id ?? ''}
            onChange={setAId}
          />
          <CandidatePicker
            id="candidate-b"
            label="Candidat B"
            candidates={candidates}
            value={b?.id ?? ''}
            onChange={setBId}
          />
        </div>

        {recommendation.data && (
          <p className="panel__note">
            Recommandation : <b>{recommendation.data.candidate}</b> — {recommendation.data.rule}
          </p>
        )}
      </section>

      {a && b && a.id === b.id && (
        <p className="warning">Choisissez deux candidats différents.</p>
      )}

      {a && b && a.id !== b.id && (
        <>
          <section className="panel">
            <h2>Vue d’ensemble</h2>
            <div className="compare">
              <CandidateSummary candidate={a} side="A" />
              <CandidateSummary candidate={b} side="B" />
            </div>
          </section>

          <section className="panel">
            <h2>Décomposition de la différence</h2>
            <p className="panel__note">
              La contribution d’un critère vaut 100 × poids × (n(A) − n(B)). Leur somme est
              exactement la différence des scores : ce tableau est le calcul du score lu terme à
              terme, et non un résumé.
            </p>
            {comparison.isLoading && <p className="empty">Calcul…</p>}
            {comparison.data && (
              <ContributionsTable
                decomposition={comparison.data}
                catalogue={catalogue}
                digits={COMPARISON_DIGITS}
              />
            )}
          </section>

          <section className="panel">
            <h2>Dominance</h2>
            {dominance.isLoading && <p className="empty">Vérification…</p>}
            {dominance.data && (
              <DominanceNotice
                verdicts={dominance.data}
                candidates={candidates}
                compared={[a.id, b.id]}
              />
            )}
          </section>

          <section className="panel">
            <h2>Assistant</h2>
            {/* ⚠️ Rendered whether or not a language service is configured.
                Hiding it when the service is off would make a working
                application look incomplete: the panel then shows the computed
                form, which is a complete answer (invariant 5). */}
            <AssistantPanel runId={selectedRunId as string} candidateId={a.id} />
          </section>

          {run.data && (
            <section className="panel">
              <h2>Régénérer à partir du candidat A</h2>
              <RegenerationPanel
                run={run.data}
                candidate={a}
                catalogue={catalogue}
                pending={regenerate.isPending}
                error={regenerate.error === null ? null : String(regenerate.error)}
                launched={launched}
                onAccept={(action) => {
                  regenerate.mutate(
                    { candidateId: a.id, action },
                    // The new run is announced by ID rather than switched to.
                    // Replacing what is on screen would read as this candidate
                    // having changed, which is the one thing regeneration must
                    // never look like.
                    { onSuccess: (created) => setLaunched(created.runId) },
                  )
                }}
              />
            </section>
          )}
        </>
      )}
    </>
  )
}

function CandidatePicker({
  id,
  label,
  candidates,
  value,
  onChange,
}: {
  id: string
  label: string
  candidates: Candidate[]
  value: string
  onChange: (id: string) => void
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        {candidates.map((c, index) => (
          <option key={c.id} value={c.id}>
            Rang {index + 1} — {c.profileName} — {c.score.toFixed(2)}/100
          </option>
        ))}
      </select>
    </div>
  )
}

function CandidateSummary({ candidate, side }: { candidate: Candidate; side: string }) {
  return (
    <div className="candidate">
      <div className="candidate__head">
        <div>
          <div className="candidate__rank">Candidat {side}</div>
          <div className="candidate__profile">{candidate.profileName}</div>
        </div>
        <div className="candidate__score">
          {candidate.score.toFixed(COMPARISON_DIGITS)}
          <span> /100</span>
        </div>
      </div>
      <table className="subscores">
        <tbody>
          {candidate.subScores.map((s) => (
            <tr key={s.criterion}>
              <td>{s.criterion}</td>
              <td>{Number.isInteger(s.rawValue) ? s.rawValue : s.rawValue.toFixed(2)}</td>
              <td>{s.normalised.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
