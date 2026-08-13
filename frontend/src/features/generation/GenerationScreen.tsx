import { useState } from 'react'

import {
  isTerminal,
  useCreateRun,
  useInstance,
  usePublishCandidate,
  useRun,
  useRuns,
} from '@/api/queries'
import { userMessage } from '@/api/errors'
import { ConflictReport } from '@/features/conflicts/ConflictReport'
import { runStateLabel, runStateTone } from '@/labels'
import { CandidateRank } from '@/features/generation/CandidateRank'
import { PreAnalysisReport } from '@/features/generation/PreAnalysisReport'
import { RunPipeline } from '@/features/generation/RunPipeline'
import { Page } from '@/shell/Page'
import type { ConstraintDefinition } from '@/types/domain'

/**
 * FR-13, FR-5, FR-6 — launch a generation and read what came back.
 *
 * The launch returns a run id immediately and the screen polls; a solve takes
 * minutes and no request is held open for it (`docs/architecture.md`).
 *
 * ⚠️ The budget is **deterministic time, not seconds** (ADR-011). It is offered
 * as three named efforts rather than as a number, because the underlying
 * parameter is a unit of WORK and cannot honestly be relabelled "seconds" —
 * U2's finding was that users did not understand the raw control, and the fix
 * is naming the choice, not renaming the unit.
 *
 * ⚠️ **The parameters live in the page bar with the action they belong to.**
 * They used to sit in the first of five stacked panels, which put the only
 * button that does anything on this screen above four panels of results and
 * below nothing — so it scrolled away the moment a run produced output.
 */
export function GenerationScreen() {
  const [runId, setRunId] = useState<string | null>(null)
  const [seed, setSeed] = useState('42')
  const [budget, setBudget] = useState('90')

  const instance = useInstance()
  const createRun = useCreateRun()
  const previous = useRuns()

  // ⚠️ **Fall back to the most recent run on the server.** `runId` is component
  // state, so navigating to Compare and back lost a run the server still had,
  // and a solve left in flight came back as "no run yet" — the reader's own
  // work, apparently discarded. Found by driving the application, not by a
  // test. This is the same defect and the same fix as the examination screen's;
  // the list endpoint returns newest first.
  const latest = previous.data?.[0]?.id ?? null
  const shown = runId ?? latest
  const run = useRun(shown)
  const publish = usePublishCandidate(shown)

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
    <Page
      title="Generate a timetable"
      subtitle="Three weighting profiles solved in sequence, then ranked under one set of weights"
      status={
        run.data && (
          <span className={`badge badge--${runStateTone(run.data.state)}`}>
            {runStateLabel(run.data.state)}
          </span>
        )
      }
      actions={
        <>
          <label className="bar-field">
            <span>Effort</span>
            <select
              aria-label="Search effort"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              disabled={launching}
            >
              <option value="30">Quick</option>
              <option value="90">Standard</option>
              <option value="180">Thorough</option>
            </select>
          </label>
          <label className="bar-field">
            <span>Seed</span>
            <input
              aria-label="Random seed"
              className="bar-field__seed"
              value={seed}
              inputMode="numeric"
              onChange={(e) => setSeed(e.target.value)}
              disabled={launching}
            />
          </label>
          <button onClick={launch} disabled={launching}>
            {launching ? 'Generating…' : 'Generate timetable'}
          </button>
        </>
      }
    >
      {createRun.isError && (
        <p className="error" role="alert">
          {userMessage(createRun.error, 'generate')}
        </p>
      )}

      {/* ⚠️ The pipeline is shown BEFORE any run exists, because it is also the
          explanation of what pressing the button does. U3: a page that does not
          say what it is for leaves the reader to infer it from the controls. */}
      <section className="section">
        <RunPipeline state={run.data?.state ?? 'PENDING'} />
        <p className="hint pipeline__caption">
          A longer search improves the quality criteria. It never changes whether the mandatory
          rules are respected — those hold in every result. With the same data and weights, the
          same seed reproduces exactly the same timetable.
        </p>
      </section>

      {/* ⚠️ **The empty state is where the workflow is taught, because it is
          the only screen state guaranteed to be seen first.** The four steps
          are numbered because they genuinely are a sequence — you cannot
          compare candidates you have not generated, or publish one you have
          not chosen — and not because numbering looks structured. */}
      {run.data === undefined && !createRun.isPending && (
        <section className="section onboard">
          <div className="section__head">
            <h2 className="section__title">No run yet</h2>
            <button onClick={launch} disabled={launching}>
              Generate timetable
            </button>
          </div>
          <ol className="onboard__steps">
            <li>
              <b>Generate</b> a run. Three weighting profiles are solved one after another, on this
              screen.
            </li>
            <li>
              <b>Read the ranking.</b> Each candidate shows its score out of 100 and a fingerprint
              of its seven quality criteria, so you can see where two closely scored timetables
              differ.
            </li>
            <li>
              <b>Compare</b> any two on the Compare screen, where the difference in score is broken
              down criterion by criterion — and explained.
            </li>
            <li>
              <b>Publish</b> the one the department adopts. It then appears to students and on the
              Published screen with its full provenance.
            </li>
          </ol>
        </section>
      )}

      {run.data && (
        <div className="runstrip">
          <div className="runstrip__id">
            <span className="stat__label">Run</span>
            <span className="runstrip__uuid">{run.data.id}</span>
          </div>
          <div className="runstrip__vitals">
            <Vital label="Seed" value={String(run.data.seed)} />
            <Vital label="Budget" value={String(run.data.deterministicBudget)} />
            <Vital label="Used" value={run.data.deterministicTimeUsed.toFixed(2)} />
            <Vital label="Elapsed" value={`${run.data.wallClockSeconds.toFixed(1)} s`} />
            <Vital label="Model" value={run.data.modelVersion} />
          </div>
        </div>
      )}

      {run.data?.duplicatesRemoved && run.data.duplicatesRemoved.length > 0 && (
        <p className="note">
          <b>Duplicates removed:</b> {run.data.duplicatesRemoved.join(', ')}. These profiles
          produced a timetable identical to one already obtained, so they are not offered twice.
        </p>
      )}

      {run.data?.error && (
        <p className="error" role="alert">
          {run.data.error}
        </p>
      )}

      {run.data && run.data.candidates.length > 0 && (
        <section className="section">
          <div className="section__head">
            <h2 className="section__title">
              Candidates<span className="section__code">FR-6</span>
            </h2>
            <p className="hint">
              Ranked by decreasing score under the weights in force — the order the server returned
            </p>
          </div>

          <CandidateRank
            candidates={run.data.candidates}
            catalogue={catalogue}
            weights={run.data.weights}
            onPublish={(id) => publish.mutate(id)}
            publishing={publish.isPending ? (publish.variables ?? null) : null}
            publishedId={publish.isSuccess ? (publish.variables ?? null) : null}
          />

          {publish.isSuccess && (
            <p className="success">
              Published. Its provenance — run, seed, weights and model version — is on the Published
              screen.
            </p>
          )}
          {publish.isError && (
            <p className="error" role="alert">
              {userMessage(publish.error, 'publish')}
            </p>
          )}
        </section>
      )}

      {run.data?.diagnosis && (
        <section className="section">
          <div className="section__head">
            <h2 className="section__title">
              Which rules conflict<span className="section__code">FR-16</span>
            </h2>
          </div>
          <p className="panel__note">
            Run only when the optimisation concludes that no timetable exists. Each rule is
            withdrawn in turn and the model re-solved, so the rules named here are the ones actually
            responsible.
          </p>
          <ConflictReport diagnosis={run.data.diagnosis} catalogue={catalogue} />
        </section>
      )}

      {run.data && (
        <section className="section">
          <div className="section__head">
            <h2 className="section__title">
              Data checks<span className="section__code">FR-12</span>
            </h2>
          </div>
          <p className="panel__note">
            Five arithmetic checks, run before any solving and without the solver. They tell an
            instance that genuinely has no solution apart from a modelling error — two situations
            the solver reports in the same way.
          </p>
          <PreAnalysisReport checks={run.data.preAnalysis} />
        </section>
      )}
    </Page>
  )
}

function Vital({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span className="stat__label">{label}</span>
      <span className="stat__value">{value}</span>
    </div>
  )
}
