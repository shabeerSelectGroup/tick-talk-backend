<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, unwrap } from '@/api/client'
import AdminIcon from '@/components/admin/AdminIcon.vue'
import BulkImportModal from '@/components/admin/BulkImportModal.vue'
import EventEditModal from '@/components/admin/EventEditModal.vue'
import AdminPageHeader from '@/components/admin/AdminPageHeader.vue'
import AdminStatusBadge from '@/components/admin/AdminStatusBadge.vue'
import CopyableField from '@/components/admin/CopyableField.vue'
import type { EventUpdatePayload } from '@/types/event'
import QrDisplay from '@/components/QrDisplay.vue'
import { useAdminStore } from '@/stores/admin'
import { useAdminTasksStore } from '@/stores/adminTasks'
import { getErrorMessage } from '@/utils/errors'

const route = useRoute()
const router = useRouter()
const admin = useAdminStore()
const tasksStore = useAdminTasksStore()
const eventId = computed(() => Number(route.params.id))
const actionError = ref('')
const clearSuccess = ref('')
const clearing = ref(false)
const editOpen = ref(false)
const editSuccess = ref('')
const savingEdit = ref(false)
const bulkOpen = ref(false)
const bulkSuccess = ref('')

const ev = computed(() => admin.currentEvent)

const quickLinks = computed(() => {
  const base = [
    { name: 'admin-event-tasks', label: 'Tasks', desc: 'Manage challenges', icon: 'list' },
    { name: 'admin-event-participants', label: 'Participants', desc: 'View roster', icon: 'users' },
    { name: 'admin-event-gallery', label: 'Gallery', desc: 'Selfie wall', icon: 'image' },
    { name: 'admin-event-reports', label: 'Reports', desc: 'Exports & analytics', icon: 'chart' },
  ]
  if (ev.value?.mode === 'competition') {
    base.splice(3, 0, {
      name: 'admin-event-leaderboard',
      label: 'Leaderboard',
      desc: 'Rankings & awards',
      icon: 'trophy',
    })
  }
  return base
})

onMounted(() => admin.fetchEvent(eventId.value))

async function handleBulkImport(importText: string) {
  actionError.value = ''
  bulkSuccess.value = ''
  try {
    const result = await tasksStore.bulkImport(eventId.value, importText)
    bulkOpen.value = false
    bulkSuccess.value = `Imported ${result.created} task(s)${
      result.skipped_duplicates ? ` (${result.skipped_duplicates} duplicates skipped)` : ''
    }.`
    if (result.errors.length) {
      actionError.value = result.errors.join('; ')
    }
    await admin.fetchEvent(eventId.value)
  } catch (e) {
    actionError.value = getErrorMessage(e)
  }
}

async function handleEditSave(payload: EventUpdatePayload) {
  savingEdit.value = true
  actionError.value = ''
  editSuccess.value = ''
  try {
    await admin.updateEvent(eventId.value, payload)
    editOpen.value = false
    editSuccess.value = 'Event updated.'
  } catch (e) {
    actionError.value = getErrorMessage(e)
  } finally {
    savingEdit.value = false
  }
}

async function clearEventData() {
  if (!ev.value) return
  const message =
    `Clear all players and submissions for "${ev.value.name}"?\n\n` +
    'This permanently removes all participants, selfies, scans, scores, and activity logs. ' +
    'Tasks and event settings are kept.'
  if (!confirm(message)) return

  actionError.value = ''
  clearSuccess.value = ''
  clearing.value = true
  try {
    const result = await unwrap<{
      participants_removed: number
      selfies_removed: number
      matches_removed: number
      activity_logs_removed: number
    }>(await api.post(`/admin/events/${eventId.value}/clear-data`, { confirm: true }))
    await admin.fetchEvent(eventId.value)
    clearSuccess.value =
      `Cleared ${result.participants_removed} player(s), ` +
      `${result.selfies_removed} selfie(s), ` +
      `${result.matches_removed} scan(s), ` +
      `${result.activity_logs_removed} activity log(s).`
  } catch (e) {
    actionError.value = getErrorMessage(e)
  } finally {
    clearing.value = false
  }
}

async function endEvent() {
  actionError.value = ''
  clearSuccess.value = ''
  try {
    const result = await unwrap<{
      winner: { display_name: string; score: number } | null
      podium: { rank: number; display_name: string; score: number }[]
    }>(await api.post(`/admin/events/${eventId.value}/end`))
    await admin.fetchEvent(eventId.value)
    if (result.podium?.length) {
      const lines = result.podium.map((p) => `#${p.rank} ${p.display_name} (${p.score} pts)`)
      alert(`Event ended\n\nPodium:\n${lines.join('\n')}`)
    } else if (result.winner) {
      alert(`Winner: ${result.winner.display_name} (${result.winner.score} pts)`)
    }
  } catch (e) {
    actionError.value = getErrorMessage(e)
  }
}

function onCopyError() {
  actionError.value = 'Could not copy to clipboard'
}
</script>

<template>
  <div v-if="ev">
    <AdminPageHeader :title="ev.name" :subtitle="ev.description || undefined">
      <template #actions>
        <AdminStatusBadge :status="ev.status" />
        <AdminStatusBadge :status="ev.mode" type="mode" />
        <button type="button" class="admin-btn-secondary" @click="bulkOpen = true">
          Bulk upload tasks
        </button>
        <button type="button" class="admin-btn-secondary" @click="editOpen = true">
          Edit event
        </button>
        <button
          v-if="ev.status !== 'ended'"
          type="button"
          class="admin-btn-primary"
          @click="endEvent"
        >
          Finish event
        </button>
      </template>
    </AdminPageHeader>

    <div class="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div class="admin-stat-card text-center">
        <p class="admin-stat-value">{{ ev.participant_count ?? 0 }}</p>
        <p class="admin-stat-label">Participants</p>
      </div>
      <div class="admin-stat-card text-center">
        <p class="admin-stat-value">{{ ev.tasks_count ?? ev.task_count }}</p>
        <p class="admin-stat-label">Tasks</p>
      </div>
      <div class="admin-stat-card text-center">
        <p class="admin-stat-value font-mono text-xl">{{ ev.code }}</p>
        <p class="admin-stat-label">Event code</p>
      </div>
      <div class="admin-stat-card text-center">
        <p class="admin-stat-value text-lg capitalize">{{ ev.status }}</p>
        <p class="admin-stat-label">Status</p>
      </div>
    </div>

    <div class="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <button
        v-for="link in quickLinks"
        :key="link.name"
        type="button"
        class="admin-nav-card"
        @click="router.push({ name: link.name, params: { id: eventId } })"
      >
        <span class="admin-nav-card__icon"><AdminIcon :name="link.icon" /></span>
        <div>
          <p class="font-semibold">{{ link.label }}</p>
          <p class="text-xs text-slate-500">{{ link.desc }}</p>
        </div>
      </button>
    </div>

    <section class="admin-panel mb-6">
      <div class="admin-panel-header">
        <h2 class="admin-panel-title">Join &amp; QR code</h2>
      </div>
      <div class="admin-panel-body">
        <p class="admin-muted mb-4">
          Share the room code or link — each person opens it and enters their own name.
        </p>
        <div class="grid gap-6 lg:grid-cols-2">
          <div class="flex items-center justify-center rounded-xl border border-slate-200 bg-slate-50 p-6">
            <img
              v-if="ev.qr_code_data_url"
              :src="ev.qr_code_data_url"
              alt="Event join QR code"
              class="h-44 w-44 rounded-lg"
            />
            <QrDisplay v-else-if="ev.join_url" :payload="ev.join_url" :size="176" variant="gold" />
          </div>
          <div class="space-y-4">
            <div v-if="ev.code">
              <p class="admin-label">Event code</p>
              <CopyableField :text="ev.code" label="Copy event code" mono large @error="onCopyError" />
            </div>
            <div v-if="ev.join_url">
              <p class="admin-label">Join URL</p>
              <CopyableField :text="ev.join_url" label="Copy join URL" mono @error="onCopyError" />
            </div>
            <a
              v-if="ev.settings?.enable_public_wall"
              :href="`/wall/${ev.code}`"
              target="_blank"
              class="admin-btn-primary block w-full text-center"
            >
              Open public wall
            </a>
          </div>
        </div>
      </div>
    </section>

    <section v-if="ev.settings" class="admin-panel mb-6">
      <div class="admin-panel-header">
        <h2 class="admin-panel-title">Settings</h2>
      </div>
      <div class="admin-panel-body">
        <dl class="grid gap-3 text-sm sm:grid-cols-2">
          <div class="flex justify-between border-b border-slate-100 py-2">
            <dt class="text-slate-500">Duration</dt>
            <dd class="font-medium">{{ ev.settings.duration_minutes }} min</dd>
          </div>
          <div v-if="ev.mode === 'competition'" class="flex justify-between border-b border-slate-100 py-2">
            <dt class="text-slate-500">Task points</dt>
            <dd class="font-medium">{{ ev.settings.task_completion_points ?? 100 }}</dd>
          </div>
          <div class="flex justify-between border-b border-slate-100 py-2">
            <dt class="text-slate-500">Selfie verification</dt>
            <dd class="font-medium">{{ ev.settings.enable_selfie_verification ? 'On' : 'Off' }}</dd>
          </div>
          <div class="flex justify-between border-b border-slate-100 py-2">
            <dt class="text-slate-500">Public wall</dt>
            <dd class="font-medium">{{ ev.settings.enable_public_wall ? 'On' : 'Off' }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <p v-if="actionError" class="admin-alert admin-alert--error mb-4">{{ actionError }}</p>
    <p v-if="editSuccess" class="admin-alert admin-alert--success mb-4">{{ editSuccess }}</p>
    <p v-if="bulkSuccess" class="admin-alert admin-alert--success mb-4">{{ bulkSuccess }}</p>
    <p v-if="clearSuccess" class="admin-alert admin-alert--success mb-4">{{ clearSuccess }}</p>

    <BulkImportModal
      :open="bulkOpen"
      @close="bulkOpen = false"
      @import="handleBulkImport"
    />
    <EventEditModal
      :open="editOpen"
      :event="ev"
      :saving="savingEdit"
      @close="editOpen = false"
      @save="handleEditSave"
    />

    <section
      v-if="(ev.participant_count ?? 0) > 0"
      class="admin-panel border-red-200"
    >
      <div class="admin-panel-header">
        <h2 class="admin-panel-title text-red-700">Danger zone</h2>
      </div>
      <div class="admin-panel-body">
        <p class="admin-muted mb-4">
          Remove every player and all submissions. Tasks, join link, and settings stay intact.
        </p>
        <button type="button" class="admin-btn-danger" :disabled="clearing" @click="clearEventData">
          {{ clearing ? 'Clearing…' : 'Clear all players & submissions' }}
        </button>
      </div>
    </section>
  </div>
  <p v-else class="admin-muted">Loading event…</p>
</template>
