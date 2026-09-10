import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAdminStore } from '@/stores/admin'

export interface AdminNavItem {
  name: string
  label: string
  icon: string
  params?: Record<string, number>
}

export function useAdminNav() {
  const route = useRoute()
  const admin = useAdminStore()

  const eventId = computed(() => {
    const raw = route.params.id
    const id = typeof raw === 'string' ? Number(raw) : Number(raw?.[0])
    return Number.isFinite(id) && id > 0 ? id : null
  })

  const isEventRoute = computed(() => {
    const name = String(route.name ?? '')
    return name.startsWith('admin-event-') && eventId.value !== null
  })

  const mainNav = computed<AdminNavItem[]>(() => [
    { name: 'admin-dashboard', label: 'Dashboard', icon: 'home' },
    { name: 'admin-events', label: 'Events', icon: 'calendar' },
    { name: 'admin-events-create', label: 'Create event', icon: 'plus' },
  ])

  const eventNav = computed<AdminNavItem[]>(() => {
    if (!eventId.value) return []
    const id = eventId.value
    const items: AdminNavItem[] = [
      { name: 'admin-event-detail', label: 'Overview', icon: 'layout', params: { id } },
      { name: 'admin-event-tasks', label: 'Tasks', icon: 'list', params: { id } },
      { name: 'admin-event-participants', label: 'Participants', icon: 'users', params: { id } },
      { name: 'admin-event-gallery', label: 'Gallery', icon: 'image', params: { id } },
    ]
    if (admin.currentEvent?.mode === 'competition') {
      items.push({ name: 'admin-event-leaderboard', label: 'Leaderboard', icon: 'trophy', params: { id } })
    }
    items.push({ name: 'admin-event-reports', label: 'Reports', icon: 'chart', params: { id } })
    return items
  })

  const breadcrumbs = computed(() => {
    const crumbs: { label: string; to?: { name: string; params?: Record<string, number> } }[] = [
      { label: 'Home', to: { name: 'admin-dashboard' } },
    ]
    const name = String(route.name ?? '')

    if (name === 'admin-dashboard') return crumbs

    crumbs.push({ label: 'Events', to: { name: 'admin-events' } })

    if (name === 'admin-events') return crumbs
    if (name === 'admin-events-create') {
      crumbs.push({ label: 'Create event' })
      return crumbs
    }

    if (isEventRoute.value && eventId.value) {
      const evName = admin.currentEvent?.name ?? `Event #${eventId.value}`
      crumbs.push({
        label: evName,
        to: { name: 'admin-event-detail', params: { id: eventId.value } },
      })
      const current = eventNav.value.find((i) => i.name === name)
      if (current && name !== 'admin-event-detail') {
        crumbs.push({ label: current.label })
      }
    }

    return crumbs
  })

  function isActive(item: AdminNavItem) {
    return route.name === item.name
  }

  return {
    eventId,
    isEventRoute,
    mainNav,
    eventNav,
    breadcrumbs,
    isActive,
  }
}
