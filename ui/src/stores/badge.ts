import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, unwrap } from '@/api/client'
import type { BadgeValidation, ParticipantBadge } from '@/types/badge'

export const useBadgeStore = defineStore('badge', () => {
  const badge = ref<ParticipantBadge | null>(null)
  const loading = ref(false)
  const validating = ref(false)
  const lastValidation = ref<BadgeValidation | null>(null)

  async function fetchBadge() {
    loading.value = true
    try {
      badge.value = await unwrap<ParticipantBadge>(await api.get('/participant/badge'))
      return badge.value
    } finally {
      loading.value = false
    }
  }

  async function validatePayload(qrPayload: string) {
    validating.value = true
    try {
      lastValidation.value = await unwrap<BadgeValidation>(
        await api.post('/participant/badge/validate', { qr_payload: qrPayload })
      )
      return lastValidation.value
    } finally {
      validating.value = false
    }
  }

  async function downloadBadgePng(): Promise<Blob> {
    const response = await api.get('/participant/badge/download', { responseType: 'blob' })
    return response.data as Blob
  }

  function setFromJoin(data: {
    participant_id: number
    event_id: number
    event_code: string
    qr_code: string
    qr_payload: string
    qr_code_data_url: string
    participant: { display_name: string; company?: string | null }
  }) {
    badge.value = {
      participant_id: data.participant_id,
      event_id: data.event_id,
      event_code: data.event_code,
      display_name: data.participant.display_name,
      company: data.participant.company ?? null,
      secure_token: data.qr_code,
      qr_token: data.qr_code,
      qr_payload: data.qr_payload,
      qr_code_data_url: data.qr_code_data_url,
      version: 'v1',
    }
  }

  return {
    badge,
    loading,
    validating,
    lastValidation,
    fetchBadge,
    validatePayload,
    downloadBadgePng,
    setFromJoin,
  }
})
