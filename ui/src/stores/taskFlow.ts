import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, unwrap } from '@/api/client'
import type {
  ScanResult,
  ScanValidation,
  SelfieUploadInfo,
  TaskCompleteResult,
  TaskFlowState,
} from '@/types/taskFlow'

export const useTaskFlowStore = defineStore('taskFlow', () => {
  const state = ref<TaskFlowState | null>(null)
  const loading = ref(false)
  const lastScan = ref<ScanResult | null>(null)

  async function fetchState(participantTaskId: number) {
    loading.value = true
    try {
      state.value = await unwrap<TaskFlowState>(
        await api.get(`/participant/tasks/${participantTaskId}/flow`)
      )
      return state.value
    } finally {
      loading.value = false
    }
  }

  async function validateScan(participantTaskId: number, qrPayload: string) {
    return unwrap<ScanValidation>(
      await api.post(`/participant/tasks/${participantTaskId}/flow/validate-scan`, {
        qr_payload: qrPayload,
      })
    )
  }

  async function recordScan(participantTaskId: number, qrPayload: string) {
    const result = await unwrap<ScanResult>(
      await api.post(`/participant/tasks/${participantTaskId}/flow/scan`, {
        qr_payload: qrPayload,
      })
    )
    lastScan.value = result
    return result
  }

  /** Process, compress, store on R2/local, link match — single multipart request. */
  async function uploadSelfie(participantTaskId: number, blob: Blob) {
    const form = new FormData()
    form.append('file', blob, 'selfie.jpg')
    const response = await api.post(
      `/participant/tasks/${participantTaskId}/flow/selfie/upload`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    return unwrap<SelfieUploadInfo>(response)
  }

  async function completeTask(
    participantTaskId: number,
    payload: { selfie_id?: number; partner_name?: string; partner_sign?: string },
  ) {
    return unwrap<TaskCompleteResult>(
      await api.post(`/participant/tasks/${participantTaskId}/flow/complete`, payload)
    )
  }

  function reset() {
    state.value = null
    lastScan.value = null
  }

  return {
    state,
    loading,
    lastScan,
    fetchState,
    validateScan,
    recordScan,
    uploadSelfie,
    completeTask,
    reset,
  }
})
