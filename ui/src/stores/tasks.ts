import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, unwrap } from '@/api/client'
import type { ParticipantTask } from '@/types'

export const useTasksStore = defineStore('participantTasks', () => {
  const tasks = ref<ParticipantTask[]>([])
  const togglingId = ref<number | null>(null)

  const completedCount = computed(() => tasks.value.filter((t) => t.status === 'completed').length)
  const pendingCount = computed(() => tasks.value.filter((t) => t.status !== 'completed').length)

  async function fetchTasks() {
    const previous = new Map(tasks.value.map((t) => [t.id, t]))
    const next = await unwrap<ParticipantTask[]>(await api.get('/participant/tasks'))
    tasks.value = next.map((task) => {
      const old = previous.get(task.id)
      if (old?.selfie_image_url && !task.selfie_image_url) {
        return {
          ...task,
          selfie_image_url: old.selfie_image_url,
          selfie_thumbnail_url: old.selfie_thumbnail_url ?? task.selfie_thumbnail_url,
        }
      }
      return task
    })
  }

  async function toggleBingoTask(participantTaskId: number) {
    togglingId.value = participantTaskId
    try {
      const result = await unwrap<{ participant_task_id: number; status: string; completed: boolean }>(
        await api.post(`/participant/tasks/${participantTaskId}/toggle`)
      )
      const row = tasks.value.find((t) => t.id === result.participant_task_id)
      if (row) row.status = result.status
      return result
    } finally {
      togglingId.value = null
    }
  }

  function patchTaskSelfie(
    participantTaskId: number,
    patch: {
      status?: string
      selfie_image_url?: string | null
      selfie_thumbnail_url?: string | null
    }
  ) {
    const row = tasks.value.find((t) => t.id === participantTaskId)
    if (row) Object.assign(row, patch)
  }

  return { tasks, completedCount, pendingCount, togglingId, fetchTasks, toggleBingoTask, patchTaskSelfie }
})
