import { useState } from 'react'

import type { Account, Group, Teacher, UserRole } from '@/types/domain'

const ROLES: UserRole[] = ['PERSON_IN_CHARGE', 'TEACHER', 'STUDENT', 'ADMINISTRATOR']

/**
 * FR-11 — the administrator manages the accounts (SRS Table 2).
 *
 * ⚠️ **This is what C-18 recorded as owed.** Phase 5 provisioned the first
 * accounts with a seed command and said plainly that the administrator's Table
 * 2 right stayed unimplemented; this is the screen that closes it.
 *
 * ⚠️ **The link fields follow the role, and the API decides.** A TEACHER must
 * name a teacher and a STUDENT a group — otherwise the account cannot say
 * whose grid or whose timetable it owns, and `routers/availability` and
 * `routers/student` refuse it. Hiding the wrong field here is a courtesy; the
 * refusal is the API's, and its message is displayed rather than paraphrased.
 *
 * ⚠️ **No password is ever displayed back.** It is typed once and goes to the
 * API; nothing in the account payload can carry it, because `domain.User` has
 * no field for it.
 */
export function AccountsPanel({
  accounts,
  teachers,
  groups,
  onCreate,
  onDelete,
  creating,
  error,
  currentUsername,
}: {
  accounts: Account[]
  teachers: Teacher[]
  groups: Group[]
  onCreate: (body: {
    username: string
    password: string
    role: UserRole
    teacher?: string | null
    group?: string | null
  }) => void
  onDelete: (username: string) => void
  creating: boolean
  error: string | null
  currentUsername: string | undefined
}) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>('TEACHER')
  const [teacher, setTeacher] = useState('')
  const [group, setGroup] = useState('')

  function submit() {
    onCreate({
      username: username.trim(),
      password,
      role,
      teacher: role === 'TEACHER' ? teacher || null : null,
      group: role === 'STUDENT' ? group || null : null,
    })
    setUsername('')
    setPassword('')
  }

  return (
    <>
      <section className="section">
        <h2>Comptes</h2>
        <p className="panel__note">
          Roles follow SRS Table 2. A teacher sees only their own availability; a student sees the
          published timetable of their own group.
        </p>

        <div className="form-row">
          <div className="field">
            <label htmlFor="account-username">Username</label>
            <input
              id="account-username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="account-password">Password</label>
            <input
              id="account-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="account-role">Role</label>
            <select
              id="account-role"
              value={role}
              onChange={(e) => setRole(e.target.value as UserRole)}
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>

          {role === 'TEACHER' && (
            <div className="field">
              <label htmlFor="account-teacher">Teacher</label>
              <select
                id="account-teacher"
                value={teacher}
                onChange={(e) => setTeacher(e.target.value)}
              >
                <option value="">—</option>
                {teachers.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.id} — {t.rank}
                  </option>
                ))}
              </select>
            </div>
          )}

          {role === 'STUDENT' && (
            <div className="field">
              <label htmlFor="account-group">Group</label>
              <select id="account-group" value={group} onChange={(e) => setGroup(e.target.value)}>
                <option value="">—</option>
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.label} ({g.level})
                  </option>
                ))}
              </select>
            </div>
          )}

          <button onClick={submit} disabled={creating || !username.trim() || !password}>
            {creating ? 'Creating…' : 'Create account'}
          </button>
        </div>

        {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      </section>

      <section className="section">
        {accounts.length === 0 ? (
          <p className="empty">No accounts yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Role</th>
                <th>Rattachement</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {accounts.map((account) => (
                <tr key={account.username}>
                  <td>{account.username}</td>
                  <td>{account.role}</td>
                  <td>{account.teacher ?? account.group ?? '—'}</td>
                  <td>
                    {/* ⚠️ Hidden for one's own account because the API refuses
                        it: removing the last administrator would leave nobody
                        able to manage accounts or the calendar, and no screen
                        creates one. Hiding is the courtesy; the refusal is the
                        protection. */}
                    {account.username === currentUsername ? (
                      <span className="meta__item">your account</span>
                    ) : (
                      <button
                        className="link"
                        aria-label={`Remove ${account.username}`}
                        onClick={() => onDelete(account.username)}
                      >
                        Remove
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="meta">
          <span>
            Comptes <b>{accounts.length}</b>
          </span>
        </div>
      </section>
    </>
  )
}
