import axios from 'axios'

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as {
      error?: { message?: string }
      detail?: string | { message?: string; code?: string }
    } | undefined

    if (data?.error?.message) return data.error.message

    const detail = data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0] as { msg?: string; loc?: (string | number)[] }
      const field = first.loc?.filter((x) => x !== 'body').pop()
      const msg = first.msg ?? 'Invalid value'
      return field ? `${field}: ${msg}` : msg
    }
    if (detail && typeof detail === 'object' && 'code' in detail && detail.code === 'EVENT_ENDED') {
      return 'This event has been finished by the admin.'
    }
    if (detail && typeof detail === 'object' && 'message' in detail && detail.message) {
      return String(detail.message)
    }

    if (error.response?.status === 422) return 'Please check the form for errors'
    if (error.response?.status === 401) return 'Session expired. Please sign in again'
    if (error.response?.status === 403) {
      if (typeof detail === 'string' && detail) return detail
      if (detail && typeof detail === 'object' && 'message' in detail && detail.message) {
        return String(detail.message)
      }
      return 'You do not have permission for this action'
    }
    if (error.response?.status === 409 && detail && typeof detail === 'object' && 'message' in detail) {
      return String(detail.message)
    }
    if (error.response?.status === 500) {
      return 'Something went wrong on our end. Please try again.'
    }
    if (error.response?.status === 503) {
      if (typeof detail === 'string') return detail
      return 'Service temporarily unavailable. Please try again shortly.'
    }
  }
  if (error instanceof Error) {
    if (error.name === 'AbortError' || error.name === 'TimeoutError' || error.message.includes('aborted')) {
      return 'Request timed out. Please check your connection and try again.'
    }
    if (error.message === 'Network Error' || error.message.includes('Failed to fetch')) {
      return 'Unable to connect. Please check your internet connection and try again.'
    }
    return error.message
  }
  return 'Something went wrong. Please try again'
}
