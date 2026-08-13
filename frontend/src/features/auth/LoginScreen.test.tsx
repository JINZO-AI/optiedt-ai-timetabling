/**
 * The sign-in screen — FR-11's surface.
 *
 * ⚠️ **The security property under test is the one a role selector invites you
 * to break.** The four buttons prefill a username and do nothing else: they set
 * no role, carry no password, and grant no permission. Authorisation comes from
 * the token the server issues, and every endpoint checks the role for itself.
 * A test that only checked "clicking Teacher fills the box" would miss the
 * thing worth guaranteeing, so the assertions below also pin what must NOT
 * happen.
 */

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { LoginScreen } from '@/features/auth/LoginScreen'

const signIn = vi.hoisted(() => vi.fn())

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client')
  return { ...actual, signIn }
})

beforeEach(() => {
  signIn.mockReset()
  vi.spyOn(console, 'error').mockImplementation(() => {})
})
afterEach(cleanup)

describe('product identity', () => {
  it('names the product and what it does', () => {
    render(<LoginScreen onSignedIn={() => {}} />)

    expect(screen.getByText('OptiEDT')).toBeTruthy()
    expect(screen.getByText('Intelligent Educational Timetabling')).toBeTruthy()
  })

  it('says accounts are provisioned, so nobody hunts for a sign-up link', () => {
    // C-18: accounts come from the seed command and there is no registration.
    // A first-time user looked for one (finding U4), so the screen says so.
    render(<LoginScreen onSignedIn={() => {}} />)

    expect(screen.getByText(/no self-registration/i)).toBeTruthy()
  })
})

describe('the four roles', () => {
  it('offers all four, and does not merge the officer into the administrator', () => {
    // ⚠️ SRS Table 2 gives the person in charge every piece of data and every
    // run, and limits the administrator to accounts and the calendar (C-8).
    // Presenting them as one would hide the actor who produces a timetable.
    render(<LoginScreen onSignedIn={() => {}} />)

    for (const label of ['Timetable Officer', 'Administrator', 'Teacher', 'Student']) {
      expect(screen.getByRole('button', { name: new RegExp(label) })).toBeTruthy()
    }
  })

  it('prefills the username and nothing else', () => {
    render(<LoginScreen onSignedIn={() => {}} />)

    fireEvent.click(screen.getByRole('button', { name: /Timetable Officer/ }))

    expect((screen.getByLabelText('Username') as HTMLInputElement).value).toBe('responsable')
    // No password is ever supplied by the interface.
    expect((screen.getByLabelText('Password') as HTMLInputElement).value).toBe('')
  })

  it('sends only what the user typed — the chosen role reaches no request', async () => {
    // ⚠️ The heart of it. If the selection travelled with the credentials, the
    // client would be asserting an identity instead of proving one.
    render(<LoginScreen onSignedIn={() => {}} />)

    fireEvent.click(screen.getByRole('button', { name: /Administrator/ }))
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => expect(signIn).toHaveBeenCalled())
    expect(signIn).toHaveBeenCalledWith('administrateur', 'secret')
    expect(signIn).toHaveBeenCalledTimes(1)
    // Two arguments exactly: no third carrying a role.
    expect(signIn.mock.calls[0]).toHaveLength(2)
  })

  it('says in as many words that the choice does not grant permission', () => {
    render(<LoginScreen onSignedIn={() => {}} />)

    expect(screen.getByText(/permissions come from the account you sign in with/i)).toBeTruthy()
  })
})

describe('failure', () => {
  it('reports a refused sign-in without leaking the status or the class', async () => {
    const { ApiError } = await import('@/api/client')
    signIn.mockRejectedValue(new ApiError(401, 'Incorrect username or password'))
    render(<LoginScreen onSignedIn={() => {}} />)

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'x' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'y' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toBe('Incorrect username or password.')
    expect(alert.textContent).not.toContain('401')
    expect(alert.textContent).not.toContain('ApiError')
  })

  it('does not report the sign-in as successful when it failed', async () => {
    const { ApiError } = await import('@/api/client')
    signIn.mockRejectedValue(new ApiError(401, 'nope'))
    const onSignedIn = vi.fn()
    render(<LoginScreen onSignedIn={onSignedIn} />)

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'x' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'y' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    await screen.findByRole('alert')
    expect(onSignedIn).not.toHaveBeenCalled()
  })

  it('cannot be submitted with an empty field', () => {
    render(<LoginScreen onSignedIn={() => {}} />)

    expect(screen.getByRole('button', { name: 'Sign in' })).toHaveProperty('disabled', true)
  })
})
