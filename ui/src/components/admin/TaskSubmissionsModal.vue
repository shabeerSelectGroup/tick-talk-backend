<script setup lang="ts">
import { ref, watch } from 'vue'
import { api, unwrap } from '@/api/client'
import type { EventTask } from '@/types/task'
import { getErrorMessage } from '@/utils/errors'
import { resolveMediaUrl } from '@/utils/mediaUrl'
import { selfieDisplayUrl } from '@/utils/selfieMedia'

export interface TaskSubmission {
  id: number
  participant_id: number
  display_name: string
  company: string | null
  image_url: string
  thumbnail_url: string
  status: string
  uploaded_at: string | null
  partner_name?: string | null
  partner_sign?: string | null
}

const props = defineProps<{
  open: boolean
  eventId: number
  task: EventTask | null
}>()

const emit = defineEmits<{
  close: []
}>()

const loading = ref(false)
const error = ref('')
const submissions = ref<TaskSubmission[]>([])

watch(
  () => [props.open, props.task?.id] as const,
  async ([open, taskId]) => {
    if (!open || !taskId || !props.task) return
    loading.value = true
    error.value = ''
    submissions.value = []
    try {
      const data = await unwrap<{
        submissions: TaskSubmission[]
        submission_count: number
      }>(await api.get(`/admin/events/${props.eventId}/tasks/${taskId}/submissions`))
      submissions.value = data.submissions
    } catch (e) {
      error.value = getErrorMessage(e)
    } finally {
      loading.value = false
    }
  }
)
</script>

<template>
  <Teleport to="body">
    <div v-if="open && task" class="admin-shell">
      <div class="admin-modal-backdrop" @click.self="emit('close')">
        <div class="admin-modal max-w-3xl p-0" role="dialog" aria-modal="true">
          <header class="flex items-start justify-between gap-3 border-b border-slate-200 p-5">
            <div class="min-w-0">
              <p class="text-xs font-bold uppercase tracking-wide text-indigo-600">Task selfies</p>
              <h2 class="text-lg font-bold">{{ task.title }}</h2>
              <p v-if="task.description" class="mt-1 text-sm text-slate-500">{{ task.description }}</p>
            </div>
            <button
              type="button"
              class="admin-btn-secondary !min-h-9 !px-3"
              aria-label="Close"
              @click="emit('close')"
            >
              ✕
            </button>
          </header>

          <div class="max-h-[70vh] overflow-y-auto p-5">
            <p v-if="loading" class="admin-empty">Loading selfies…</p>
            <p v-else-if="error" class="admin-alert admin-alert--error">{{ error }}</p>
            <p v-else-if="!submissions.length" class="admin-empty">No selfies uploaded for this task yet.</p>
            <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <article
                v-for="s in submissions"
                :key="s.id"
                class="admin-panel overflow-hidden !p-0"
              >
                <a
                  :href="resolveMediaUrl(s.image_url)"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="block aspect-square"
                >
                  <img
                    :src="selfieDisplayUrl(s)"
                    :alt="`Selfie by ${s.display_name}`"
                    class="h-full w-full object-cover"
                    loading="lazy"
                  />
                </a>
                <div class="px-3 py-2">
                  <p class="truncate text-sm font-semibold">{{ s.display_name }}</p>
                  <p v-if="s.partner_name" class="truncate text-xs text-slate-600">
                    with {{ s.partner_name }}
                  </p>
                  <p v-if="s.company" class="truncate text-xs text-slate-500">{{ s.company }}</p>
                </div>
              </article>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
