import type { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { api } from '@/api/client'
import { useAdminAuthStore } from '@/stores/adminAuth'

const AUTH_PATHS = ['/admin/auth/login', '/admin/auth/refresh']

function isAuthEndpoint(url?: string) {
  if (!url) return false
  return AUTH_PATHS.some((p) => url.includes(p))
}

function isParticipantEndpoint(url?: string) {
  if (!url) return false
  return url.includes('/participant/')
}

export function setupAdminInterceptors() {
  api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const config = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
      if (
        error.response?.status !== 401 ||
        !config ||
        config._retry ||
        isAuthEndpoint(config.url) ||
        isParticipantEndpoint(config.url)
      ) {
        return Promise.reject(error)
      }

      const adminAuth = useAdminAuthStore()
      config._retry = true
      const refreshed = await adminAuth.refreshAccessToken()
      if (refreshed && adminAuth.accessToken) {
        config.headers.Authorization = `Bearer ${adminAuth.accessToken}`
        return api.request(config)
      }

      adminAuth.clearSession()
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/admin/login')) {
        window.location.href = `/admin/login?redirect=${encodeURIComponent(window.location.pathname)}`
      }
      return Promise.reject(error)
    }
  )
}
