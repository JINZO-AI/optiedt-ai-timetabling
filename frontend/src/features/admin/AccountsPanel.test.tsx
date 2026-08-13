import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AccountsPanel } from '@/features/admin/AccountsPanel'
import type { Account, Group, Teacher } from '@/types/domain'

/**
 * FR-11 — account management's display half (SRS Table 2).
 *
 * ⚠️ **The rules themselves are the API's**, verified against real tokens in
 * `acceptance/test_fr11.py`: who may manage accounts, which link a role
 * requires, and what may not be removed. What only a rendering test can
 * establish is that this screen does not *ask* for something the API will
 * refuse, and does not display something it must never hold.
 */

const TEACHERS: Teacher[] = [{ id: 'T001', department: 'D', rank: 'Assistant', maxHoursPerWeek: 18 }]
const GROUPS: Group[] = [
  { id: '3', promotion: '1', parentGroup: '2', level: 'TP', label: 'INFO-L1-G1.1', size: 15 },
]

function accounts(): Account[] {
  return [
    { id: 'a1', username: 'administrateur', role: 'ADMINISTRATOR', teacher: null, group: null },
    { id: 't1', username: 't001', role: 'TEACHER', teacher: 'T001', group: null },
    { id: 'e1', username: 'etudiant', role: 'STUDENT', teacher: null, group: '3' },
  ]
}

function renderPanel(overrides: Partial<Parameters<typeof AccountsPanel>[0]> = {}) {
  const onCreate = vi.fn()
  const onDelete = vi.fn()
  render(
    <AccountsPanel
      accounts={accounts()}
      teachers={TEACHERS}
      groups={GROUPS}
      onCreate={onCreate}
      onDelete={onDelete}
      creating={false}
      error={null}
      currentUsername="administrateur"
      {...overrides}
    />,
  )
  return { onCreate, onDelete }
}

afterEach(cleanup)

describe('the list of accounts', () => {
  it('shows each account with its role and its link', () => {
    renderPanel()

    const rows = screen.getAllByRole('row')
    const teacherRow = rows.find((row) => within(row).queryByText('t001'))
    const studentRow = rows.find((row) => within(row).queryByText('etudiant'))

    expect(teacherRow).toBeTruthy()
    expect(within(teacherRow!).getByText('TEACHER')).toBeTruthy()
    expect(within(teacherRow!).getByText('T001')).toBeTruthy()
    expect(within(studentRow!).getByText('STUDENT')).toBeTruthy()
    expect(within(studentRow!).getByText('3')).toBeTruthy()
  })

  it('never renders a credential, because the payload cannot carry one', () => {
    // `domain.User` has no password field, so this asserts a design rather than
    // a filter. It would fail the day somebody added one to the account schema.
    const { container } = render(
      <AccountsPanel
        accounts={accounts()}
        teachers={TEACHERS}
        groups={GROUPS}
        onCreate={vi.fn()}
        onDelete={vi.fn()}
        creating={false}
        error={null}
        currentUsername="administrateur"
      />,
    )

    expect(container.querySelectorAll('input[type="password"]')).toHaveLength(1)
    expect(container.textContent).not.toMatch(/mot de passe\s*:/i)
  })
})

describe('removal', () => {
  it('removes the account the button names', () => {
    const { onDelete } = renderPanel()

    fireEvent.click(screen.getByLabelText('Remove t001'))

    expect(onDelete).toHaveBeenCalledWith('t001')
  })

  it('offers no removal for the signed-in account', () => {
    // ⚠️ Hiding is the courtesy; the refusal is the API's. Removing your own
    // administrator account would leave nobody able to manage the accounts or
    // the calendar, and no screen creates one (C-18).
    renderPanel()

    expect(screen.queryByLabelText('Supprimer administrateur')).toBeNull()
    expect(screen.getByText('your account')).toBeTruthy()
  })
})

describe('creating an account', () => {
  it('asks for a teacher when the role is TEACHER and sends it', () => {
    const { onCreate } = renderPanel()

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'nouveau' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'assez-long-1234' } })
    fireEvent.change(screen.getByLabelText('Role'), { target: { value: 'TEACHER' } })
    fireEvent.change(screen.getByLabelText('Teacher'), { target: { value: 'T001' } })
    fireEvent.click(screen.getByText('Create account'))

    expect(onCreate).toHaveBeenCalledWith({
      username: 'nouveau',
      password: 'assez-long-1234',
      role: 'TEACHER',
      teacher: 'T001',
      group: null,
    })
  })

  it('asks for a group when the role is STUDENT and sends it', () => {
    // SRS Table 2's other scoped role: without the link the account cannot say
    // whose timetable it owns, and `/me/timetable` refuses it.
    const { onCreate } = renderPanel()

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'etudiant2' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'assez-long-1234' } })
    fireEvent.change(screen.getByLabelText('Role'), { target: { value: 'STUDENT' } })
    fireEvent.change(screen.getByLabelText('Group'), { target: { value: '3' } })
    fireEvent.click(screen.getByText('Create account'))

    expect(onCreate).toHaveBeenCalledWith({
      username: 'etudiant2',
      password: 'assez-long-1234',
      role: 'STUDENT',
      teacher: null,
      group: '3',
    })
  })

  it('offers no link field for a role that carries none', () => {
    // The API refuses a teacher link on an administrator rather than dropping
    // it silently; asking for one here would invite that refusal.
    renderPanel()

    fireEvent.change(screen.getByLabelText('Role'), { target: { value: 'ADMINISTRATOR' } })

    expect(screen.queryByLabelText('Teacher')).toBeNull()
    expect(screen.queryByLabelText('Group')).toBeNull()
  })

  it('surfaces the API refusal rather than paraphrasing it', () => {
    // The rule lives in one place. A screen that invented its own wording would
    // be a second, weaker copy of the API's validation.
    renderPanel({ error: '422: A TEACHER account requires a teacher' })

    expect(screen.getByText(/requires a teacher/)).toBeTruthy()
  })
})
