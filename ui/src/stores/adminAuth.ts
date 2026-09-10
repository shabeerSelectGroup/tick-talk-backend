import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, setAdminToken, unwrap } from '@/api/client'
import type { AdminLoginResponse, AdminRefreshResponse, AdminUser } from '@/types/admin'

const ACCESS_KEY = 'ticktalk_admin_access'
const REFRESH_KEY = 'ticktalk_admin_refresh'
const ADMIN_USER_KEY = 'ticktalk_admin_user'

let refreshPromise: Promise<boolean> | null = null

export const useAdminAuthStore = defineStore('adminAuth', () => {
  const accessToken = ref<string | null>(localStorage.getItem(ACCESS_KEY))
  const refreshToken = ref<string | null>(localStorage.getItem(REFRESH_KEY))
  const admin = ref<AdminUser | null>(_loadAdmin())

  const isAuthenticated = computed(() => !!accessToken.value)
  const roleLabel = computed(() => 'Admin')

  function _loadAdmin(): AdminUser | null {
    try {
      const raw = localStorage.getItem(ADMIN_USER_KEY)
      return raw ? (JSON.parse(raw) as AdminUser) : null
    } catch {
      return null
    }
  }

  function _persist() {
    if (accessToken.value) {
      localStorage.setItem(ACCESS_KEY, accessToken.value)
      setAdminToken(accessToken.value)
    } else {
      localStorage.removeItem(ACCESS_KEY)
      setAdminToken(null)
    }
    if (refreshToken.value) {
      localStorage.setItem(REFRESH_KEY, refreshToken.value)
    } else {
      localStorage.removeItem(REFRESH_KEY)
    }
    if (admin.value) {
      localStorage.setItem(ADMIN_USER_KEY, JSON.stringify(admin.value))
    } else {
      localStorage.removeItem(ADMIN_USER_KEY)
    }
  }

  function setSession(data: { access_token: string; refresh_token: string; admin?: AdminUser }) {
    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token
    if (data.admin) admin.value = data.admin
    _persist()
  }

  async function loginWithSecurityCode(securityCode: string) {
    const data = await unwrap<AdminLoginResponse>(
      await api.post('/admin/auth/login', { security_code: securityCode })
    )
    setSession(data)
    return data
  }

  async function fetchMe() {
    const data = await unwrap<{ admin: AdminUser }>(await api.get('/admin/auth/me'))
    admin.value = data.admin
    _persist()
    return data.admin
  }

  async function refreshAccessToken(): Promise<boolean> {
    if (!refreshToken.value) return false
    if (refreshPromise) return refreshPromise

    refreshPromise = (async () => {
      try {
        const data = await unwrap<AdminRefreshResponse>(
          await api.post('/admin/auth/refresh', { refresh_token: refreshToken.value })
        )
        accessToken.value = data.access_token
        refreshToken.value = data.refresh_token
        _persist()
        return true
      } catch {
        clearSession()
        return false
      } finally {
        refreshPromise = null
      }
    })()

    return refreshPromise
  }

  async function logout() {
    try {
      if (accessToken.value && refreshToken.value) {
        await api.post('/admin/auth/logout', { refresh_token: refreshToken.value })
      }
    } catch {
      /* proceed with local cleanup */
    }
    clearSession()
  }

  function clearSession() {
    accessToken.value = null
    refreshToken.value = null
    admin.value = null
    _persist()
  }

  function hasRole(...roles: AdminUser['role'][]) {
    return admin.value ? roles.includes(admin.value.role) : false
  }

  // Bootstrap axios header on load
  if (accessToken.value) {
    setAdminToken(accessToken.value)
  }

  return {
    accessToken,
    refreshToken,
    admin,
    isAuthenticated,
    roleLabel,
    loginWithSecurityCode,
    logout,
    fetchMe,
    refreshAccessToken,
    clearSession,
    hasRole,
  }
})
