<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AdminPageHeader from '@/components/admin/AdminPageHeader.vue'
import BulkImportModal from '@/components/admin/BulkImportModal.vue'
import TaskFormModal from '@/components/admin/TaskFormModal.vue'
import TaskSubmissionsModal from '@/components/admin/TaskSubmissionsModal.vue'
import { useAdminStore } from '@/stores/admin'
import { useAdminTasksStore } from '@/stores/adminTasks'
import type { EventTask, TaskCreatePayload } from '@/types/task'
import { getErrorMessage } from '@/utils/errors'

const route = useRoute()
const admin = useAdminStore()
const tasksStore = useAdminTasksStore()

const eventId = computed(() => Number(route.params.id))
const error = ref('')
const success = ref('')
const formOpen = ref(false)
const bulkOpen = ref(false)
const editingTask = ref<EventTask | null>(null)
const submissionsTask = ref<EventTask | null>(null)
const submissionsOpen = ref(false)
const saving = ref(false)
const selectedIds = ref<Set<number>>(new Set())
const draggingId = ref<number | null>(null)
const dropTargetId = ref<number | null>(null)
const reordering = ref(false)
const deletingSelected = ref(false)

const isCompetition = computed(() => admin.currentEvent?.mode === 'competition')
const selectedCount = computed(() => selectedIds.value.size)
const allSelected = computed(
  () =>
    tasksStore.tasks.length > 0 && selectedIds.value.size === tasksStore.tasks.length
)

onMounted(async () => {
  await admin.fetchEvent(eventId.value)
  await tasksStore.fetchTasks(eventId.value)
})

function openCreate() {
  editingTask.value = null
  formOpen.value = true
}

function openEdit(task: EventTask) {
  editingTask.value = task
  formOpen.value = true
}

function openSubmissions(task: EventTask) {
  submissionsTask.value = task
  submissionsOpen.value = true
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value = new Set()
    return
  }
  selectedIds.value = new Set(tasksStore.tasks.map((t) => t.id))
}

function toggleSelect(taskId: number, checked: boolean) {
  const next = new Set(selectedIds.value)
  if (checked) next.add(taskId)
  else next.delete(taskId)
  selectedIds.value = next
}

function clearSelection() {
  selectedIds.value = new Set()
}

async function handleSave(payload: TaskCreatePayload) {
  saving.value = true
  error.value = ''
  try {
    if (editingTask.value) {
      await tasksStore.updateTask(eventId.value, editingTask.value.id, payload)
      success.value = 'Task updated'
    } else {
      await tasksStore.createTask(eventId.value, payload)
      success.value = 'Task added and assigned to all participants'
    }
    formOpen.value = false
  } catch (e) {
    error.value = getErrorMessage(e)
  } finally {
    saving.value = false
  }
}

async function handleDelete(task: EventTask) {
  if (!confirm(`Delete "${task.title}"?`)) return
  error.value = ''
  try {
    await tasksStore.deleteTask(eventId.value, task.id)
    const next = new Set(selectedIds.value)
    next.delete(task.id)
    selectedIds.value = next
    success.value = 'Task deleted'
  } catch (e) {
    error.value = getErrorMessage(e)
  }
}

async function deleteSelected() {
  const ids = [...selectedIds.value]
  if (!ids.length) return
  if (!confirm(`Delete ${ids.length} selected task(s)?`)) return

  deletingSelected.value = true
  error.value = ''
  try {
    await tasksStore.deleteTasks(eventId.value, ids)
    clearSelection()
    success.value = `Deleted ${ids.length} task(s)`
  } catch (e) {
    error.value = getErrorMessage(e)
  } finally {
    deletingSelected.value = false
  }
}

function onDragStart(taskId: number) {
  draggingId.value = taskId
}

function onDragEnd() {
  draggingId.value = null
  dropTargetId.value = null
}

function onDragOver(taskId: number, event: DragEvent) {
  event.preventDefault()
  if (draggingId.value !== null && draggingId.value !== taskId) {
    dropTargetId.value = taskId
  }
}

function onDragLeave(taskId: number) {
  if (dropTargetId.value === taskId) {
    dropTargetId.value = null
  }
}

async function onDrop(targetTaskId: number) {
  const sourceId = draggingId.value
  draggingId.value = null
  dropTargetId.value = null
  if (sourceId === null || sourceId === targetTaskId || reordering.value) return

  const list = [...tasksStore.tasks]
  const fromIdx = list.findIndex((t) => t.id === sourceId)
  const toIdx = list.findIndex((t) => t.id === targetTaskId)
  if (fromIdx < 0 || toIdx < 0) return

  const [moved] = list.splice(fromIdx, 1)
  list.splice(toIdx, 0, moved)
  const ids = list.map((t) => t.id)

  reordering.value = true
  error.value = ''
  try {
    await tasksStore.reorderTasks(eventId.value, ids)
  } catch (e) {
    error.value = getErrorMessage(e)
  } finally {
    reordering.value = false
  }
}

async function handleBulkImport(text: string) {
  error.value = ''
  try {
    const result = await tasksStore.bulkImport(eventId.value, text)
    bulkOpen.value = false
    clearSelection()
    success.value = `Imported ${result.created} tasks (${result.skipped_duplicates} duplicates skipped)`
    if (result.errors.length) {
      error.value = result.errors.join('; ')
    }
  } catch (e) {
    error.value = getErrorMessage(e)
  }
}
</script>

<template>
  <div>
    <AdminPageHeader
      title="Tasks"
      :subtitle="`Shared list for all participants · ${tasksStore.tasks.length} tasks`"
    >
      <template #actions>
        <button
          v-if="selectedCount > 0"
          type="button"
          class="admin-btn-danger"
          :disabled="deletingSelected"
          @click="deleteSelected"
        >
          {{ deletingSelected ? 'Deleting…' : `Delete selected (${selectedCount})` }}
        </button>
        <button type="button" class="admin-btn-secondary" @click="bulkOpen = true">
          Bulk upload
        </button>
        <button type="button" class="admin-btn-primary" @click="openCreate">Add task</button>
      </template>
    </AdminPageHeader>

    <p v-if="success" class="admin-alert admin-alert--success mb-4">{{ success }}</p>
    <p v-if="error" class="admin-alert admin-alert--error mb-4">{{ error }}</p>

    <div class="admin-panel">
      <div v-if="tasksStore.loading" class="admin-empty">Loading tasks…</div>
      <div v-else-if="!tasksStore.tasks.length" class="admin-empty">
        No tasks yet. Add networking prompts like “Find someone who works in HR”.
      </div>
      <div v-else class="admin-table-wrap border-0 shadow-none">
        <p class="admin-muted border-b border-slate-100 px-4 py-2 text-xs">
          Drag the handle to reorder. Numbering matches participant task order.
        </p>
        <table class="admin-table">
          <thead>
            <tr>
              <th class="w-10">
                <input
                  type="checkbox"
                  class="admin-table-checkbox"
                  :checked="allSelected"
                  aria-label="Select all tasks"
                  @change="toggleSelectAll"
                />
              </th>
              <th class="w-12 text-center">#</th>
              <th class="w-12" />
              <th>Task</th>
              <th>Type</th>
              <th>Progress</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(task, index) in tasksStore.tasks"
              :key="task.id"
              :class="{
                'admin-table-row--dragging': draggingId === task.id,
                'admin-table-row--drop-target': dropTargetId === task.id,
              }"
              @dragover="onDragOver(task.id, $event)"
              @dragleave="onDragLeave(task.id)"
              @drop="onDrop(task.id)"
            >
              <td>
                <input
                  type="checkbox"
                  class="admin-table-checkbox"
                  :checked="selectedIds.has(task.id)"
                  :aria-label="`Select ${task.title}`"
                  @change="toggleSelect(task.id, ($event.target as HTMLInputElement).checked)"
                />
              </td>
              <td class="text-center font-semibold text-slate-500">{{ index + 1 }}</td>
              <td>
                <span
                  class="admin-drag-handle"
                  draggable="true"
                  title="Drag to reorder"
                  aria-label="Drag to reorder"
                  @dragstart="onDragStart(task.id)"
                  @dragend="onDragEnd"
                >
                  ⋮⋮
                </span>
              </td>
              <td>
                <button type="button" class="text-left" @click="openSubmissions(task)">
                  <p class="font-semibold text-indigo-600 hover:text-indigo-800">{{ task.title }}</p>
                  <p v-if="task.description" class="text-xs text-slate-500">{{ task.description }}</p>
                </button>
              </td>
              <td class="capitalize text-slate-600">
                {{ task.type }}
                <span v-if="isCompetition && task.points" class="text-slate-400"> · {{ task.points }} pts</span>
              </td>
              <td class="text-slate-600">
                {{ task.completed_count }}/{{ task.assigned_count }} done
                · {{ task.selfie_count ?? 0 }} selfies
              </td>
              <td class="text-right">
                <div class="flex justify-end gap-1">
                  <button type="button" class="admin-btn-ghost" @click="openSubmissions(task)">Selfies</button>
                  <button type="button" class="admin-btn-ghost" @click="openEdit(task)">Edit</button>
                  <button type="button" class="admin-btn-ghost !text-red-600" @click="handleDelete(task)">
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <TaskFormModal
      :open="formOpen"
      :task="editingTask"
      :is-competition="isCompetition"
      @close="formOpen = false"
      @save="handleSave"
    />
    <BulkImportModal :open="bulkOpen" @close="bulkOpen = false" @import="handleBulkImport" />
    <TaskSubmissionsModal
      :open="submissionsOpen"
      :event-id="eventId"
      :task="submissionsTask"
      @close="submissionsOpen = false"
    />
  </div>
</template>
