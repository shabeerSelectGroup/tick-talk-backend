import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, unwrap } from '@/api/client'
import type {
  AdminEventDetail,
  EventCreatePayload,
  EventCreateResult,
  EventUpdatePayload,
} from '@/types/event'

export const useAdminStore = defineStore('admin', () => {
  const events = ref<AdminEventDetail[]>([])
  const currentEvent = ref<AdminEventDetail | null>(null)
  const activity = ref<Array<{ id: number; type: string; payload: unknown; created_at: string }>>([])

  async function fetchEvents() {
    events.value = await unwrap<AdminEventDetail[]>(await api.get('/admin/events'))
  }

  async function fetchEvent(id: number) {
    currentEvent.value = await unwrap<AdminEventDetail>(await api.get(`/admin/events/${id}`))
    return currentEvent.value
  }

  async function createEvent(payload: EventCreatePayload) {
    const result = await unwrap<EventCreateResult>(
      await api.post('/admin/events', payload)
    )
    const detail: AdminEventDetail = {
      ...result.event,
      settings: result.settings,
      join_url: result.join_url,
      qr_code_data_url: result.qr_code_data_url,
      tasks_count: result.tasks_created,
    }
    events.value.unshift(detail)
    currentEvent.value = detail
    return result
  }

  async function fetchActivity(eventId: number) {
    activity.value = await unwrap(await api.get(`/admin/events/${eventId}/activity`))
  }

  async function updateEvent(id: number, payload: EventUpdatePayload) {
    const detail = await unwrap<AdminEventDetail>(await api.patch(`/admin/events/${id}`, payload))
    currentEvent.value = detail
    const idx = events.value.findIndex((e) => e.id === id)
    if (idx >= 0) {
      events.value[idx] = { ...events.value[idx], ...detail }
    }
    return detail
  }

  return {
    events,
    currentEvent,
    activity,
    fetchEvents,
    fetchEvent,
    createEvent,
    updateEvent,
    fetchActivity,
  }
})
