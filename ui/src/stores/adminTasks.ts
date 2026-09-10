import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, unwrap } from '@/api/client'
import type { BulkImportResult, EventTask, TaskCreatePayload } from '@/types/task'

export const useAdminTasksStore = defineStore('adminTasks', () => {
  const tasks = ref<EventTask[]>([])
  const loading = ref(false)

  async function fetchTasks(eventId: number, includeInactive = false) {
    loading.value = true
    try {
      tasks.value = await unwrap<EventTask[]>(
        await api.get(`/admin/events/${eventId}/tasks`, {
          params: { include_inactive: includeInactive },
        })
      )
      tasks.value.sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
    } finally {
      loading.value = false
    }
    return tasks.value
  }

  async function createTask(eventId: number, payload: TaskCreatePayload) {
    const created = await unwrap<EventTask>(
      await api.post(`/admin/events/${eventId}/tasks`, payload)
    )
    tasks.value.push(created)
    tasks.value.sort((a, b) => a.sort_order - b.sort_order)
    return created
  }

  async function updateTask(eventId: number, taskId: number, payload: Partial<TaskCreatePayload>) {
    const updated = await unwrap<EventTask>(
      await api.patch(`/admin/events/${eventId}/tasks/${taskId}`, payload)
    )
    const idx = tasks.value.findIndex((t) => t.id === taskId)
    if (idx >= 0) tasks.value[idx] = updated
    return updated
  }

  async function deleteTask(eventId: number, taskId: number) {
    await unwrap(await api.delete(`/admin/events/${eventId}/tasks/${taskId}`))
    tasks.value = tasks.value.filter((t) => t.id !== taskId)
  }

  async function deleteTasks(eventId: number, taskIds: number[]) {
    for (const taskId of taskIds) {
      await unwrap(await api.delete(`/admin/events/${eventId}/tasks/${taskId}`))
    }
    const remove = new Set(taskIds)
    tasks.value = tasks.value.filter((t) => !remove.has(t.id))
  }

  async function reorderTasks(eventId: number, taskIds: number[]) {
    const reordered = await unwrap<EventTask[]>(
      await api.put(`/admin/events/${eventId}/tasks/reorder`, { task_ids: taskIds })
    )
    tasks.value = reordered
    return reordered
  }

  async function bulkImport(eventId: number, text: string) {
    const result = await unwrap<BulkImportResult>(
      await api.post(`/admin/events/${eventId}/tasks/bulk-import`, { text })
    )
    await fetchTasks(eventId)
    return result
  }

  function moveTask(taskId: number, direction: 'up' | 'down') {
    const ids = tasks.value.map((t) => t.id)
    const idx = ids.indexOf(taskId)
    if (idx < 0) return null
    const swap = direction === 'up' ? idx - 1 : idx + 1
    if (swap < 0 || swap >= ids.length) return null
    ;[ids[idx], ids[swap]] = [ids[swap], ids[idx]]
    return ids
  }

  return {
    tasks,
    loading,
    fetchTasks,
    createTask,
    updateTask,
    deleteTask,
    deleteTasks,
    reorderTasks,
    bulkImport,
    moveTask,
  }
})
