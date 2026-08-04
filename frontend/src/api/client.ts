/**
 * The HTTP client. One place that knows the API is at /api.
 *
 * Vite proxies /api to the FastAPI process in development (vite.config.ts), so
 * requests are same-origin and no base URL is configured here.
 *
 * This module reads the API and nothing else. It performs no arithmetic on a
 * score, a contribution or a rank — docs/architecture.md gives the
 * presentation layer leave to "display, filter, print, ask" and forbids it to
 * "compute a score, decide an order". Every figure the interface shows arrives
 * already computed.
 */

const BASE = '/api'

const TOKEN_KEY = 'optiedt.token'

/**
 * The bearer token, in `sessionStorage` rather than `localStorage`.
 *
 * ⚠️ Neither is safe against script injection — any script on the page reads
 * both — so this is a choice between two imperfect options, not a defence.
 * `sessionStorage` is scoped to the tab and cleared when it closes, so a shared
 * machine does not leave a signed-in session behind for the next person, which
 * is the realistic risk in a faculty office. A cookie with `HttpOnly` would be
 * the stronger answer and needs the API to set it; recorded rather than
 * pretended otherwise.
 */
export function storedToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function storeToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY)
}

function authHeaders(): Record<string, string> {
  const token = storedToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(`${status}: ${detail}`)
    this.name = 'ApiError'
  }
}

async function parseError(response: Response): Promise<never> {
  let detail = response.statusText
  try {
    const body: unknown = await response.json()
    if (body && typeof body === 'object' && 'detail' in body) {
      detail = String((body as { detail: unknown }).detail)
    }
  } catch {
    // A non-JSON error body is not itself an error worth reporting over the
    // status it accompanied.
  }
  throw new ApiError(response.status, detail)
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { Accept: 'application/json', ...authHeaders() },
  })
  if (!response.ok) await parseError(response)
  return (await response.json()) as T
}

export async function apiSend<T>(
  method: 'POST' | 'PUT',
  path: string,
  body: unknown,
): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(body),
  })
  if (!response.ok) await parseError(response)
  return (await response.json()) as T
}

/**
 * Sign in — FR-11.
 *
 * ⚠️ Form-encoded, not JSON, and the response fields are snake_case. Both are
 * the OAuth2 password flow's shape, which the API follows so that FastAPI's own
 * `/api/docs` can sign in too. `TokenOut` in `api/schemas.py` disables the
 * camelCase alias generator for exactly this.
 */
export async function signIn(username: string, password: string): Promise<string> {
  const response = await fetch(`${BASE}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password }),
  })
  if (!response.ok) await parseError(response)
  const body = (await response.json()) as { access_token: string }
  storeToken(body.access_token)
  return body.access_token
}
