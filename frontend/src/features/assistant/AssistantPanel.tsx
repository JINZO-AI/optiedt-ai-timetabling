import { useState } from 'react'

import { useAskAssistant, useExplanation, useRunReport } from '@/api/queries'
import { userMessage } from '@/api/errors'
import type { AssistantAnswer } from '@/types/domain'

/**
 * FR-22 and FR-24 on screen — "Ask OptiEDT AI".
 *
 * ⚠️ **The one thing this panel must never do is let generated text pass for
 * computed text.** Every answer is labelled, and the label is not a badge in a
 * corner — a reader deciding whether to trust a sentence needs to know who
 * wrote it before they read it, so it goes above.
 *
 * ⚠️ **The panel sits BESIDE the figures it explains, never instead of them.**
 * It used to be section five of seven on a stack of panels, which is how a
 * capability comes to read as an afterthought. Docked next to the ledger, the
 * explanation and the arithmetic it describes are on screen together — and the
 * visual hierarchy says which one is the source.
 *
 * The computed form is the HONEST one: its figures come straight from the
 * analysis layer. So the labelling runs in the direction that protects the
 * reader — the computed answer is presented as a normal, complete answer
 * rather than as a degraded one, because that is what it is (invariant 5:
 * only text disappears).
 *
 * ⚠️ **`fallbackReason` is shown, not swallowed.** Of the reasons it can carry,
 * one matters more than the rest: *the answer contained a figure absent from
 * the context and was discarded*. A reader who never learns that happened
 * cannot know the service is unreliable on their data, and an operator cannot
 * know either. Hiding it would make a broken model look like a model nobody
 * switched on.
 *
 * ⚠️ **No text on this screen is invented by the interface.** Every answer
 * comes from `/api/assistant/*`; when the service is off, what is shown is the
 * server's own computed form, not a placeholder written here. There is no
 * fabricated confidence score, no invented citation and no simulated typing.
 */

/** Questions worth asking, offered so a first-time user has somewhere to start.
 *
 * ⚠️ Short and contextual. V1 offered four full sentences as wrapped pills of
 * ragged widths, which read as an advertisement for a chatbot rather than as
 * things you can ask about the run in front of you. */
const SUGGESTIONS = [
  'Why is this candidate ranked first?',
  'What trade-offs does it make?',
  'Where is it weakest?',
  'Explain the score in plain terms.',
]

export function AssistantPanel({
  runId,
  candidateId,
}: {
  runId: string
  candidateId: string | null
}) {
  const explanation = useExplanation(runId, candidateId)
  const ask = useAskAssistant(runId)
  const [question, setQuestion] = useState('')
  const [asked, setAsked] = useState<string | null>(null)
  const [wantsReport, setWantsReport] = useState(false)

  // Whether a provider actually wrote anything. Read from the answer the server
  // returned rather than from configuration, which the browser cannot see.
  const serviceOff = explanation.data?.generated === false

  function submit(text: string) {
    const trimmed = text.trim()
    if (trimmed === '') return
    setAsked(trimmed)
    ask.mutate(trimmed)
  }

  return (
    <section className="ai" aria-labelledby="ai-heading">
      <header className="ai__head">
        <SparkIcon />
        <span className="ai__title" id="ai-heading">
          OptiEDT AI
        </span>
        <span className="ai__state">
          {explanation.isLoading ? 'Loading' : serviceOff ? 'Computed' : 'Grounded'}
        </span>
      </header>

      <div className="ai__body">
        {/* ⚠️ **One line.** V1 opened with eleven lines of preamble — a
            guarantee paragraph and a configuration notice — before a reader
            reached a single answer. The division of labour still has to be
            stated, because everything below depends on believing it, but it
            says it once and gets out of the way. The full contract is on the
            answer label itself, where a reader is actually deciding whether to
            trust a sentence. */}
        <p className="ai__guarantee">
          Explains figures OptiEDT computed. It <b>computes no score and decides no ranking</b>, and{' '}
          <b>cannot invent a number</b>.
        </p>

        {serviceOff && (
          <p className="ai-off">
            <b>AI writing is currently switched off.</b> What follows is the application’s own
            computed answer — complete, just not written in prose. Set{' '}
            <code>OPTIEDT_ASSISTANT_ENABLED=true</code> to enable written answers.
          </p>
        )}

        <h3>Why this candidate scores as it does</h3>
        {explanation.isLoading && <ThinkingLine label="Reading the run" />}
        {candidateId === null && (
          <p className="empty empty--inline">Select a candidate to see its explanation.</p>
        )}
        {explanation.isError && (
          <p className="error" role="alert">
            {userMessage(explanation.error, 'ask')}
          </p>
        )}
        {explanation.data && <Answer answer={explanation.data} />}

        <h3>Ask OptiEDT AI</h3>

        <div className="ai-suggestions">
          {SUGGESTIONS.map((text) => (
            <button
              key={text}
              type="button"
              className="secondary ai-suggestion"
              disabled={ask.isPending}
              onClick={() => {
                setQuestion(text)
                submit(text)
              }}
            >
              {text}
            </button>
          ))}
        </div>

        <form
          className="ai-form"
          onSubmit={(event) => {
            event.preventDefault()
            submit(question)
          }}
        >
          <div className="field ai-ask">
            <label htmlFor="assistant-question">Your question</label>
            <input
              id="assistant-question"
              type="text"
              value={question}
              placeholder="Why is this candidate ranked first?"
              onChange={(e) => setQuestion(e.target.value)}
            />
          </div>
          <button type="submit" disabled={ask.isPending || question.trim() === ''}>
            {ask.isPending ? 'Asking…' : 'Ask'}
          </button>
        </form>

        {ask.isError && (
          <p className="error" role="alert">
            {userMessage(ask.error, 'ask')}
          </p>
        )}

        {ask.isPending && <ThinkingLine label="Composing an answer from the context" />}

        {asked !== null && !ask.isPending && ask.data && (
          <>
            <p className="ai__asked">
              You asked: <i>{asked}</i>
            </p>
            <Answer answer={ask.data} />
          </>
        )}

        <h3>Run report</h3>
        <p className="ai__guarantee">
          Parameters, every candidate with its score, and the published one.
        </p>
        {/* ⚠️ Requested on demand rather than loaded with the page. The report is
            the FIRST thing cut under time pressure (PPM §8.3), so it must not be
            something every visit to this screen pays for. */}
        {!wantsReport ? (
          <button type="button" className="secondary" onClick={() => setWantsReport(true)}>
            Produce the report
          </button>
        ) : (
          <ReportSection runId={runId} />
        )}
      </div>
    </section>
  )
}

function ReportSection({ runId }: { runId: string }) {
  const report = useRunReport(runId)
  if (report.isLoading) return <ThinkingLine label="Writing the report" />
  if (report.isError)
    return (
      <p className="error" role="alert">
        {userMessage(report.error, 'ask')}
      </p>
    )
  if (!report.data) return <p className="empty empty--inline">No report available.</p>
  return <Answer answer={report.data} />
}

/**
 * One answer, labelled by origin.
 *
 * ⚠️ The label comes FIRST. A reader who reaches the end of a paragraph before
 * learning a language model wrote it has already read it as fact.
 */
export function Answer({ answer }: { answer: AssistantAnswer }) {
  return (
    <>
      <p
        className={
          answer.generated ? 'assistant__origin assistant__origin--generated' : 'assistant__origin'
        }
      >
        {answer.generated ? (
          <>
            <b>Written by the language service.</b> Every number in it was checked against the
            context the application supplied.
          </>
        ) : (
          <>
            <b>Computed by the application.</b> No text was written; the figures below come straight
            from the analysis layer.
          </>
        )}
      </p>

      <pre className="assistant__answer">{answer.text}</pre>

      {answer.fallbackReason !== null && (
        <p className="ai__reason">Reason: {answer.fallbackReason}</p>
      )}
    </>
  )
}

/**
 * The waiting state.
 *
 * ⚠️ **It says what is being waited for, and it does not fake a stream.** The
 * API returns a whole answer in one response; animating characters into place
 * would be an invented capability, and this project's rule is that the
 * interface never implies something the system does not do.
 */
function ThinkingLine({ label }: { label: string }) {
  return (
    <p className="ai__thinking" role="status">
      <span className="ai__thinking-dots" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      {label}…
    </p>
  )
}

function SparkIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M8 1.5 9.6 6.4 14.5 8 9.6 9.6 8 14.5 6.4 9.6 1.5 8l4.9-1.6z" />
    </svg>
  )
}
