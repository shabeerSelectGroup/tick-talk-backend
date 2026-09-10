import { resolveApiBaseUrl } from '@/api/resolveBaseUrl'

function extractMediaPath(url: string): string | null {
  const trimmed = url.trim()
  if (trimmed.startsWith('/api/v1/media')) {
    return trimmed
  }
  const match = trimmed.match(/\/api\/v1\/media\/[^\s?#]*/)
  return match ? match[0] : null
}

/**
 * Resolve selfie/media URLs for the current deployment.
 * Dev: same-origin `/api/v1/media/...` (Vite proxy).
 * Prod split host: `https://ticktalk-api.../api/v1/media/...` when VITE_API_BASE_URL is absolute.
 */
export function resolveMediaUrl(url: string | null | undefined): string {
  if (!url?.trim()) return ''
  const trimmed = url.trim()

  const mediaPath = extractMediaPath(trimmed)
  if (mediaPath) {
    const apiBase = resolveApiBaseUrl()
    if (apiBase.startsWith('http')) {
      return `${new URL(apiBase).origin}${mediaPath}`
    }
    return mediaPath
  }

  if (/^https?:\/\//i.test(trimmed)) return trimmed
  return trimmed
}
