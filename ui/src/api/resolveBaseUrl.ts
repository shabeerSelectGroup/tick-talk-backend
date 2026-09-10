/**
 * Dev: use Vite's `/api` → `127.0.0.1:8000` proxy (same origin, no CORS, works on LAN URLs).
 * Prod: relative `/api/v1` behind nginx, or set VITE_API_BASE_URL to a full URL.
 */
export function resolveApiBaseUrl(): string {
  const env = import.meta.env.VITE_API_BASE_URL as string | undefined
  if (env?.startsWith('http')) return env.replace(/\/$/, '')

  if (import.meta.env.DEV) return '/api/v1'

  const base = env || '/api/v1'
  return base.endsWith('/') ? base.slice(0, -1) : base
}
