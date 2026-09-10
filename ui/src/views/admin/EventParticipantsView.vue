<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import AdminPageHeader from '@/components/admin/AdminPageHeader.vue'
import { useAdminStore } from '@/stores/admin'
import { getErrorMessage } from '@/utils/errors'
import type { ApiResponse } from '@/types'

type RosterRow = {
  id: number
  display_name: string
  email?: string | null
  company?: string | null
  score?: number
  signed_in?: boolean
}

const route = useRoute()
const admin = useAdminStore()
const eventId = computed(() => Number(route.params.id))
const participants = ref<RosterRow[]>([])
const rosterTotal = ref(0)
const loading = ref(false)
const error = ref('')

const joinHint = computed(() => {
  const ev = admin.currentEvent
  if (!ev || ev.id !== eventId.value || !ev.code) return ''
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  return `${origin}/join/${ev.code}`
})

function isValidEventId(): boolean {
  return Number.isFinite(eventId.value) && eventId.value > 0
}

async function loadRoster() {
  if (!isValidEventId()) {
    error.value = 'Invalid event.'
    participants.value = []
    rosterTotal.value = 0
    return
  }

  loading.value = true
  error.value = ''
  const all: RosterRow[] = []
  let page = 1
  const perPage = 100
  try {
    while (true) {
      const response = await api.get<ApiResponse<RosterRow[]>>(
        `/admin/events/${eventId.value}/participants`,
        { params: { page, per_page: perPage } }
      )
      const body = response.data
      if (!body.success || body.data === null) {
        throw new Error(body.error?.message ?? 'Could not load roster')
      }
      all.push(...body.data)
      const total = body.meta?.total ?? all.length
      rosterTotal.value = total
      if (all.length >= total || body.data.length < perPage) break
      page += 1
    }
    participants.value = all
  } catch (e) {
    error.value = getErrorMessage(e)
  } finally {
    loading.value = false
  }
}

async function refreshPage() {
  if (!isValidEventId()) return
  try {
    await admin.fetchEvent(eventId.value)
  } catch (e) {
    error.value = getErrorMessage(e)
  }
  await loadRoster()
}

onMounted(() => refreshPage())
watch(eventId, () => refreshPage())
</script>

<template>
  <div>
    <AdminPageHeader
      title="Participants"
      subtitle="Everyone who joins this event on their phone appears here automatically."
    >
      <template #actions>
        <button type="button" class="admin-btn-secondary" :disabled="loading" @click="loadRoster">
          {{ loading ? 'Loading…' : 'Refresh' }}
        </button>
      </template>
    </AdminPageHeader>

    <p v-if="joinHint" class="admin-alert admin-alert--info mb-4 font-mono text-xs">{{ joinHint }}</p>
    <p v-if="error" class="admin-alert admin-alert--error mb-4" role="alert">{{ error }}</p>

    <div class="admin-panel">
      <div class="admin-panel-header">
        <h2 class="admin-panel-title">Roster ({{ rosterTotal || participants.length }})</h2>
      </div>
      <div class="admin-table-wrap border-0 shadow-none">
        <table class="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Company</th>
              <th>Status</th>
              <th class="text-right">Score</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in participants" :key="p.id">
              <td class="font-semibold">{{ p.display_name }}</td>
              <td class="text-slate-500">{{ p.company || '—' }}</td>
              <td>
                <span
                  class="admin-badge"
                  :class="p.signed_in ? 'admin-badge--live' : 'admin-badge--draft'"
                >
                  {{ p.signed_in ? 'Signed in' : 'Offline' }}
                </span>
              </td>
              <td class="text-right font-semibold">
                {{ p.score != null && p.score > 0 ? `${p.score} pts` : '—' }}
              </td>
            </tr>
            <tr v-if="!participants.length && !loading">
              <td colspan="4" class="admin-empty">
                No one on the roster yet. Share the join link from the event overview.
              </td>
            </tr>
            <tr v-if="loading && !participants.length">
              <td colspan="4" class="admin-empty">Loading roster…</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
