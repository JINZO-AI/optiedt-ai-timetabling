/**
 * Technical failures, turned into something a user can act on.
 *
 * ⚠️ **This exists because a screenshot caught a real defect.** A teacher who
 * reached the regeneration control was shown, verbatim:
 *
 *     ApiError: 403: role TEACHER may not do this; requires one of PERSON_IN_CHARGE
 *
 * Three things are wrong with that and only one of them is cosmetic. It names
 * internal role constants, it reads as a crash rather than as a rule, and it
 * appears at all — the control should not have been offered to a role that
 * cannot use it (see `RegenerationPanel`).
 *
 * ⚠️ **Hiding a control is NOT the authorisation.** Every endpoint checks the
 * role for itself (FR-11), and this module changes nothing about that. What it
 * changes is what a person reads when the server refuses.
 *
 * The technical detail is preserved on the `ApiError` instance and logged to
 * the console, so a developer keeps it while a user does not have to read it.
 */

import { ApiError } from '@/api/client'

/** What the failed request was trying to do, so the message can say so. */
export type Action =
  | 'sign-in'
  | 'load'
  | 'save'
  | 'generate'
  | 'regenerate'
  | 'publish'
  | 'import'
  | 'delete'
  | 'ask'

const BY_ACTION: Record<Action, string> = {
  'sign-in': 'Sign-in failed.',
  load: 'This information could not be loaded.',
  save: 'Your changes could not be saved.',
  generate: 'The timetable could not be generated.',
  regenerate: 'The new run could not be started.',
  publish: 'The timetable could not be published.',
  import: 'The dataset could not be imported.',
  delete: 'This item could not be removed.',
  ask: 'The assistant could not answer.',
}

/**
 * A message to show the user, and nothing else.
 *
 * Deliberately does not return the server's `detail` for 4xx: those strings are
 * written for a developer reading a log, not for the person in front of the
 * screen.
 */
export function userMessage(cause: unknown, action: Action): string {
  // Kept for whoever is debugging; never rendered.
  if (typeof console !== 'undefined') console.error(`[${action}]`, cause)

  if (!(cause instanceof ApiError)) {
    return `${BY_ACTION[action]} The server could not be reached. Check your connection and try again.`
  }

  switch (cause.status) {
    case 401:
      return action === 'sign-in'
        ? 'Incorrect username or password.'
        : 'Your session has expired. Please sign in again.'
    case 403:
      return 'You do not have permission to perform this action.'
    case 404:
      return `${BY_ACTION[action]} The item was not found — it may have been removed.`
    case 409:
      return `${BY_ACTION[action]} It conflicts with something that changed in the meantime. Reload and try again.`
    case 413:
      return `${BY_ACTION[action]} The files are too large.`
    case 422:
      return `${BY_ACTION[action]} Some of the values supplied are not valid.`
    case 503:
      return `${BY_ACTION[action]} The service is temporarily unavailable.`
    default:
      return cause.status >= 500
        ? `${BY_ACTION[action]} The server reported an unexpected problem. Please try again.`
        : BY_ACTION[action]
  }
}

/** True when the failure is the caller lacking the right, not a fault. */
export function isForbidden(cause: unknown): boolean {
  return cause instanceof ApiError && cause.status === 403
}
