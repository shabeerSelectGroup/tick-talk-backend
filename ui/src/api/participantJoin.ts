import type { ApiResponse } from '@/types'
import type { JoinResult } from '@/types/join'
import { resolveApiBaseUrl } from '@/api/resolveBaseUrl'

const JOIN_TIMEOUT_MS = 15_000

export interface JoinFormPayload {
  event_code: string
  display_name: string
  email?: string
  company?: string
}

/**
 * Join via fetch (not axios) so the request is not affected by admin interceptors
 * or stale axios defaults. Uses the Vite /api proxy in development.
 */
export async function postParticipantJoin(form: JoinFormPayload): Promise<JoinResult> {
  const base = resolveApiBaseUrl()
  const url = `${base}/participant/join`

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({
      event_code: form.event_code,
      display_name: form.display_name,
      email: form.email || undefined,
      company: form.company || undefined,
    }),
    credentials: 'include',
    cache: 'no-store',
    signal: AbortSignal.timeout(JOIN_TIMEOUT_MS),
  })

  let body: ApiResponse<JoinResult>
  try {
    body = (await res.json()) as ApiResponse<JoinResult>
  } catch {
    throw new Error(
      res.ok
        ? 'Invalid server response'
        : `Server error (${res.status}). Is the backend running on port 8000?`
    )
  }

  if (!res.ok || !body.success || body.data === null) {
    const detail = (body as unknown as { detail?: { message?: string } }).detail
    const msg = body.error?.message ?? detail?.message ?? `Join failed (${res.status})`
    throw new Error(msg)
  }

  return body.data
}
