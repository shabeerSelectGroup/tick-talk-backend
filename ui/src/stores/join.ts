import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, unwrap } from '@/api/client'
import { postParticipantJoin } from '@/api/participantJoin'
import type { JoinPreview, JoinResult } from '@/types/join'

export interface JoinFormData {
  display_name: string
  email?: string
  company?: string
}

export const useJoinStore = defineStore('join', () => {
  const preview = ref<JoinPreview | null>(null)
  const lastJoinResult = ref<JoinResult | null>(null)
  const loading = ref(false)

  async function fetchPreview(eventCode: string) {
    loading.value = true
    try {
      preview.value = await unwrap<JoinPreview>(
        await api.get(`/participant/events/${eventCode}/join-preview`)
      )
      return preview.value
    } finally {
      loading.value = false
    }
  }

  async function join(eventCode: string, form: JoinFormData) {
    const result = await postParticipantJoin({
      event_code: eventCode,
      display_name: form.display_name,
      email: form.email,
      company: form.company,
    })
    lastJoinResult.value = result
    return result
  }

  return { preview, lastJoinResult, loading, fetchPreview, join }
})
