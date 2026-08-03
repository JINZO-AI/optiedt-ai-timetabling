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
    headers: { Accept: 'application/json' },
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
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) await parseError(response)
  return (await response.json()) as T
}
