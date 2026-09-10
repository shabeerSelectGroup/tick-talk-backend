import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import type { ApiResponse } from '@/types'
import { resolveApiBaseUrl } from '@/api/resolveBaseUrl'

export const api: AxiosInstance = axios.create({
  baseURL: resolveApiBaseUrl(),
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
  timeout: 20_000,
})

/** Participant routes must not send admin JWT (avoids 401 refresh redirect during join). */
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const url = config.url ?? ''
  if (url.includes('/participant/')) {
    delete config.headers.Authorization
  }
  return config
})

export function unwrap<T>(response: { data: ApiResponse<T> }): T {
  const body = response.data
  if (!body.success || body.data === null) {
    throw new Error(body.error?.message ?? 'Request failed')
  }
  return body.data
}

export function setAdminToken(token: string | null) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common.Authorization
  }
}

export function setSessionToken(token: string | null) {
  if (token) {
    api.defaults.headers.common['X-Session-Token'] = token
  } else {
    delete api.defaults.headers.common['X-Session-Token']
  }
}
