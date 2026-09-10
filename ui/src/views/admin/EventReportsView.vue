<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, unwrap } from '@/api/client'
import { createExportJob, downloadExportFile, listExportJobs } from '@/api/exports'
import AdminPageHeader from '@/components/admin/AdminPageHeader.vue'
import { useAdminStore } from '@/stores/admin'
import { EXPORT_OPTIONS, type ExportJob, type ExportType } from '@/types/reports'
import { getErrorMessage } from '@/utils/errors'

const route = useRoute()
const admin = useAdminStore()
const eventId = computed(() => Number(route.params.id))
const summary = ref<Record<string, unknown> | null>(null)
const jobs = ref<ExportJob[]>([])
const starting = ref<ExportType | null>(null)
const error = ref('')

type TopTaskRow = { title: string; completions: number }
type LeaderboardRow = {
  rank: number
  participant_id: number
  display_name: string
  score: number
  tasks_completed?: number
}

const isNetworking = computed(() => summary.value?.mode === 'networking')
const isCompetition = computed(() => admin.currentEvent?.mode === 'competition')

const topTasks = computed((): TopTaskRow[] => {
  const raw = summary.value?.top_tasks
  return Array.isArray(raw) ? (raw as TopTaskRow[]) : []
})

const exportOptions = computed(() =>
  EXPORT_OPTIONS.filter((o) => !o.competitionOnly || isCompetition.value)
)

let pollTimer: ReturnType<typeof setInterval> | null = null

function formatBytes(n: number | null) {
  if (n == null) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function exportStatusClass(status: string) {
  if (status === 'completed') return 'admin-badge admin-badge--live'
  if (status === 'failed') return 'admin-badge admin-badge--draft'
  if (status === 'processing') return 'admin-badge admin-badge--scheduled'
  return 'admin-badge admin-badge--ended'
}

function formatBadgeClass(format: string) {
  if (format === 'PDF') return 'admin-badge admin-badge--draft'
  if (format === 'ZIP') return 'admin-badge admin-badge--networking'
  return 'admin-badge admin-badge--competition'
}

async function loadSummary() {
  summary.value = await unwrap(await api.get(`/admin/events/${eventId.value}/reports/summary`))
}

async function loadJobs() {
  jobs.value = await listExportJobs(eventId.value)
}

async function refresh() {
  await admin.fetchEvent(eventId.value)
  await Promise.all([loadSummary(), loadJobs()])
}

async function startExport(type: ExportType) {
  starting.value = type
  error.value = ''
  try {
    const job = await createExportJob(eventId.value, type)
    jobs.value = [job, ...jobs.value.filter((j) => j.id !== job.id)]
    startPolling()
  } catch (e) {
    error.value = getErrorMessage(e)
  } finally {
    starting.value = null
  }
}

async function pollJobs() {
  const active = jobs.value.some((j) => j.status === 'pending' || j.status === 'processing')
  if (!active) {
    stopPolling()
    return
  }
  try {
    jobs.value = await listExportJobs(eventId.value)
  } catch {
    /* ignore poll errors */
  }
}

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(pollJobs, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function onDownload(job: ExportJob) {
  error.value = ''
  try {
    await downloadExportFile(eventId.value, job)
  } catch (e) {
    error.value = getErrorMessage(e)
  }
}

onMounted(async () => {
  try {
    await refresh()
    if (jobs.value.some((j) => j.status === 'pending' || j.status === 'processing')) {
      startPolling()
    }
  } catch (e) {
    error.value = getErrorMessage(e)
  }
})

onUnmounted(stopPolling)
</script>

<template>
  <div>
    <AdminPageHeader
      title="Reports & exports"
      subtitle="Analytics for this event and downloadable exports (generated in the background)."
    />

    <p v-if="error" class="admin-alert admin-alert--error mb-4" role="alert">{{ error }}</p>

    <section class="admin-panel mb-6">
      <div class="admin-panel-header">
        <h2 class="admin-panel-title">Generate export</h2>
      </div>
      <div class="admin-panel-body">
        <p class="admin-muted mb-4">Files are built asynchronously — check status below.</p>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <button
            v-for="opt in exportOptions"
            :key="opt.type"
            type="button"
            class="admin-export-card flex flex-col p-4 text-left disabled:opacity-50"
            :disabled="starting === opt.type"
            @click="startExport(opt.type)"
          >
            <span :class="formatBadgeClass(opt.format)">{{ opt.format }}</span>
            <span class="mt-2 font-semibold">{{ opt.label }}</span>
            <span class="admin-muted mt-1">{{ opt.description }}</span>
            <span v-if="starting === opt.type" class="mt-2 text-xs font-semibold text-indigo-600">
              Starting…
            </span>
          </button>
        </div>
      </div>
    </section>

    <section class="admin-panel mb-6">
      <div class="admin-panel-header">
        <h2 class="admin-panel-title">Export history</h2>
      </div>
      <div class="admin-panel-body">
        <ul v-if="jobs.length" class="space-y-2">
          <li
            v-for="job in jobs"
            :key="job.id"
            class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 px-4 py-3 text-sm"
          >
            <div class="min-w-0">
              <p class="font-semibold">{{ job.export_label }}</p>
              <p class="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span :class="exportStatusClass(job.status)">{{ job.status }}</span>
                <span v-if="job.file_size_bytes">{{ formatBytes(job.file_size_bytes) }}</span>
                <span v-if="job.error_message" class="text-red-600">{{ job.error_message }}</span>
              </p>
            </div>
            <button
              v-if="job.status === 'completed'"
              type="button"
              class="admin-btn-primary shrink-0 !min-h-9 !px-3 !text-xs"
              @click="onDownload(job)"
            >
              Download
            </button>
            <span
              v-else-if="job.status === 'pending' || job.status === 'processing'"
              class="text-xs font-semibold text-indigo-600"
            >
              Processing…
            </span>
          </li>
        </ul>
        <p v-else class="admin-empty">No exports yet — generate one above.</p>
      </div>
    </section>

    <section v-if="summary && isNetworking">
      <h2 class="admin-page-title mb-4 text-lg">Event analytics</h2>
      <div class="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div class="admin-stat-card text-center">
          <p class="admin-stat-value">{{ summary.participants_active }}</p>
          <p class="admin-stat-label">Active participants</p>
        </div>
        <div class="admin-stat-card text-center">
          <p class="admin-stat-value">{{ summary.total_connections }}</p>
          <p class="admin-stat-label">Connections</p>
        </div>
        <div class="admin-stat-card text-center">
          <p class="admin-stat-value">{{ summary.tasks_completed }}</p>
          <p class="admin-stat-label">Tasks completed</p>
        </div>
        <div class="admin-stat-card text-center">
          <p class="admin-stat-value">{{ summary.selfies_uploaded }}</p>
          <p class="admin-stat-label">Selfies</p>
        </div>
      </div>

      <section v-if="topTasks.length" class="admin-panel">
        <div class="admin-panel-header">
          <h3 class="admin-panel-title">Top completed tasks</h3>
        </div>
        <div class="admin-panel-body space-y-2">
          <div
            v-for="(t, i) in topTasks"
            :key="i"
            class="flex justify-between border-b border-slate-100 py-2 text-sm last:border-0"
          >
            <span class="font-medium">{{ t.title }}</span>
            <span class="font-semibold text-indigo-600">{{ t.completions }}</span>
          </div>
        </div>
      </section>
    </section>

    <section v-else-if="summary">
      <h2 class="admin-page-title mb-4 text-lg">Event analytics</h2>
      <div class="mb-6 grid gap-4 sm:grid-cols-3">
        <div class="admin-stat-card text-center">
          <p class="admin-stat-value">{{ summary.participant_count }}</p>
          <p class="admin-stat-label">Participants</p>
        </div>
        <div class="admin-stat-card text-center">
          <p class="admin-stat-value">{{ summary.total_matches }}</p>
          <p class="admin-stat-label">Scans</p>
        </div>
        <div class="admin-stat-card text-center">
          <p class="admin-stat-value">{{ summary.total_tasks_completed }}</p>
          <p class="admin-stat-label">Tasks completed</p>
        </div>
      </div>

      <section v-if="(summary.leaderboard_top as LeaderboardRow[])?.length" class="admin-panel">
        <div class="admin-panel-header">
          <h3 class="admin-panel-title">Leaderboard top 5</h3>
        </div>
        <div class="admin-table-wrap border-0 shadow-none">
          <table class="admin-table">
            <tbody>
              <tr v-for="row in (summary.leaderboard_top as LeaderboardRow[])" :key="row.participant_id">
                <td class="w-12 font-bold">{{ row.rank }}</td>
                <td class="font-semibold">{{ row.display_name }}</td>
                <td class="text-right font-semibold text-indigo-600">
                  {{ row.score }} · {{ row.tasks_completed ?? 0 }} tasks
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </section>
  </div>
</template>
