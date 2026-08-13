/**
 * Technical failures, turned into something a user can act on.
 *
 * ⚠️ **These exist because a screenshot caught a real defect.** A teacher who
 * reached the regeneration control was shown, verbatim:
 *
 *     ApiError: 403: role TEACHER may not do this; requires one of PERSON_IN_CHARGE
 *
 * The endpoint was right to refuse. What was wrong was printing an internal
 * message at a user — and, separately, offering the control to a role that
 * cannot use it (see the gate in `ComparisonScreen`).
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { isForbidden, userMessage } from '@/api/errors'

beforeEach(() => {
  // The helper logs the technical detail for a developer; silence it here so a
  // passing run is not full of expected noise.
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

describe('what a user is told', () => {
  it('never leaks the server detail, the status code or the class name', () => {
    const raw = 'role TEACHER may not do this; requires one of PERSON_IN_CHARGE'
    const message = userMessage(new ApiError(403, raw), 'regenerate')

    expect(message).toBe('You do not have permission to perform this action.')
    // The three things the screenshot showed, none of which may reach a user.
    expect(message).not.toContain('403')
    expect(message).not.toContain('ApiError')
    expect(message).not.toContain('PERSON_IN_CHARGE')
    expect(message).not.toContain(raw)
  })

  it('keeps the technical detail for whoever is debugging', () => {
    // Hiding it from the user must not mean losing it.
    const cause = new ApiError(403, 'role TEACHER may not do this')
    userMessage(cause, 'regenerate')

    expect(console.error).toHaveBeenCalledWith('[regenerate]', cause)
  })

  it('distinguishes a lapsed session from a refused sign-in', () => {
    // Both are 401. Telling a signed-in user "incorrect password" would send
    // them looking for a mistake they did not make.
    expect(userMessage(new ApiError(401, 'x'), 'sign-in')).toBe('Incorrect username or password.')
    expect(userMessage(new ApiError(401, 'x'), 'load')).toMatch(/session has expired/i)
  })

  it('says what failed, so one message is not reused for everything', () => {
    expect(userMessage(new ApiError(500, 'boom'), 'generate')).toMatch(/timetable could not be generated/i)
    expect(userMessage(new ApiError(500, 'boom'), 'publish')).toMatch(/could not be published/i)
    expect(userMessage(new ApiError(500, 'boom'), 'import')).toMatch(/dataset could not be imported/i)
  })

  it('treats a network failure as unreachable rather than as a server fault', () => {
    // A TypeError from fetch is not an ApiError and has no status to read.
    const message = userMessage(new TypeError('Failed to fetch'), 'load')

    expect(message).toMatch(/could not be reached/i)
    expect(message).not.toContain('TypeError')
  })

  it('is a complete sentence in every case, never an empty string', () => {
    const actions = ['sign-in', 'load', 'save', 'generate', 'regenerate', 'publish', 'import', 'delete', 'ask'] as const
    for (const action of actions) {
      for (const status of [400, 401, 403, 404, 409, 413, 422, 500, 503]) {
        const message = userMessage(new ApiError(status, 'detail'), action)
        expect(message.length).toBeGreaterThan(10)
        expect(message.endsWith('.')).toBe(true)
      }
    }
  })
})

describe('isForbidden', () => {
  it('is true only for a 403', () => {
    expect(isForbidden(new ApiError(403, 'x'))).toBe(true)
    expect(isForbidden(new ApiError(401, 'x'))).toBe(false)
    expect(isForbidden(new TypeError('offline'))).toBe(false)
  })
})
