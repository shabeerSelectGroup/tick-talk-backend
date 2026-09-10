import type { RouteLocationNormalized } from 'vue-router'
import { useAdminAuthStore } from '@/stores/adminAuth'
import { useAuthStore } from '@/stores/auth'
import type { AdminRole } from '@/types/admin'

export async function adminAuthGuard(to: RouteLocationNormalized) {
  const adminAuth = useAdminAuthStore()

  if (to.meta.guestAdmin && adminAuth.isAuthenticated) {
    return { name: 'admin-dashboard' }
  }

  if (!to.meta.requiresAdmin) return true

  if (!adminAuth.isAuthenticated) {
    return { name: 'admin-login', query: { redirect: to.fullPath } }
  }

  if (!adminAuth.admin) {
    try {
      await adminAuth.fetchMe()
    } catch {
      adminAuth.clearSession()
      return { name: 'admin-login', query: { redirect: to.fullPath } }
    }
  }

  const requiredRoles = to.meta.roles as AdminRole[] | undefined
  if (requiredRoles?.length && !adminAuth.hasRole(...requiredRoles)) {
    return { name: 'admin-dashboard' }
  }

  return true
}

export async function participantAuthGuard(to: RouteLocationNormalized) {
  const auth = useAuthStore()

  if (to.meta.requiresSession && !auth.isParticipant) {
    const code = to.params.eventCode as string | undefined
    if (code) {
      return { name: 'join', params: { eventCode: code } }
    }
    return { name: 'join' }
  }

  if (to.name === 'leaderboard') {
    const { useEventStore } = await import('@/stores/event')
    const eventStore = useEventStore()
    if (!eventStore.event) {
      try {
        await eventStore.fetchMe()
      } catch {
        return { name: 'tasks' }
      }
    }
    if (!eventStore.showLeaderboard) {
      return { name: 'tasks' }
    }
  }

  return true
}
