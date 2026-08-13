import { useState } from 'react'

import { signIn } from '@/api/client'
import { userMessage } from '@/api/errors'
import { BrandMark } from '@/shell/icons'

/**
 * FR-11 — signing in.
 *
 * ⚠️ **The message is the same whether the username is unknown or the password
 * is wrong**, because the API answers the same for both: telling them apart
 * tells an attacker which accounts exist. Do not "improve" this by splitting
 * the two cases; the server does not supply the distinction to display.
 *
 * ⚠️ **The role buttons below PREFILL A USERNAME AND NOTHING ELSE.** They grant
 * no permission, carry no password, and set no client-side role. The signed-in
 * identity comes from the token the server issues, and every endpoint checks
 * the role for itself (FR-11) — so a user who prefills "responsable" and then
 * signs in as a teacher gets a teacher's rights, because the server decides.
 * They exist because a demonstration should not begin with the presenter
 * trying to remember which of four accounts is which.
 *
 * Accounts come from the seed command (C-18) — there is no registration here
 * and none is planned.
 */

/** The seeded accounts, from `services/seed.py`. Usernames only. */
const ROLES = [
  {
    username: 'responsable',
    label: 'Timetable Officer',
    blurb: 'Loads data, generates and publishes timetables',
  },
  {
    username: 'administrateur',
    label: 'Administrator',
    blurb: 'Manages the academic calendar and accounts',
  },
  { username: 't001', label: 'Teacher', blurb: 'Declares availability, reads their timetable' },
  { username: 'etudiant', label: 'Student', blurb: 'Reads their group’s published timetable' },
] as const

/** What the product does, in the order it does it. */
const CAPABILITIES = [
  'Conflict-free timetables under twelve hard rules, proven by constraint solving',
  'Several ranked candidates, compared criterion by criterion',
  'Recommendations you approve, then regenerate from',
  'Examination sessions alongside the weekly timetable',
] as const

export function LoginScreen({
  onSignedIn,
  expired = false,
}: {
  onSignedIn: () => void
  /** A stored token the API refused. Says why the user is here rather than leaving them to guess. */
  expired?: boolean
}) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await signIn(username, password)
      onSignedIn()
    } catch (cause) {
      setError(userMessage(cause, 'sign-in'))
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="signin">
      {/* ⚠️ The left half is the product's only chance to say what it is. The
          field behind it is the subject itself — a week of slots, most empty,
          a couple filled — drawn in CSS rather than shipped as an image. */}
      <section className="signin__pitch">
        <div className="signin__inner">
          <div className="signin__brandline">
            <BrandMark size={38} />
            <div>
              <h1 className="signin__brand">OptiEDT</h1>
              <p className="signin__tagline">Intelligent Educational Timetabling</p>
            </div>
          </div>

          <p className="signin__lead">
            Constraint solving places every session. An exact weighted score ranks the results. A
            language model explains them — and can invent nothing.
          </p>

          <ul className="signin__points">
            {CAPABILITIES.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="signin__form" aria-labelledby="signin-heading">
        <div className="signin__form-inner">
          {expired && (
            <p className="warning" role="alert">
              Your session has expired. Sign in again to continue.
            </p>
          )}

          <h2 id="signin-heading">Sign in</h2>
          <p className="panel__note">
            Accounts are created by the setup command — there is no self-registration.
          </p>

          <fieldset className="signin__roles">
            <legend>Sign in as</legend>
            {/* ⚠️ Prefill only — see the module docstring. No permission is
                granted here and no role is stored client-side. */}
            {ROLES.map((role) => (
              <button
                key={role.username}
                type="button"
                className={`signin__role${username === role.username ? ' signin__role--picked' : ''}`}
                onClick={() => setUsername(role.username)}
                disabled={pending}
              >
                <strong>{role.label}</strong>
                <small>{role.blurb}</small>
              </button>
            ))}
          </fieldset>
          <p className="hint signin__hint">
            Choosing a role fills in its username. Your permissions come from the account you sign
            in with, not from this choice.
          </p>

          <form onSubmit={submit} className="signin__fields">
            <div className="field">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                value={username}
                autoComplete="username"
                onChange={(e) => setUsername(e.target.value)}
                disabled={pending}
              />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                autoComplete="current-password"
                onChange={(e) => setPassword(e.target.value)}
                disabled={pending}
              />
            </div>
            <button type="submit" disabled={pending || !username || !password}>
              {pending ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          {error && (
            <p className="error signin__error" role="alert">
              {error}
            </p>
          )}
        </div>
      </section>
    </div>
  )
}
