<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, unwrap } from '@/api/client'
import AdminPageHeader from '@/components/admin/AdminPageHeader.vue'
import type { AwardEntry, LeaderboardEntry } from '@/types'
import { useAdminStore } from '@/stores/admin'

const route = useRoute()
const admin = useAdminStore()
const eventId = computed(() => Number(route.params.id))
const board = ref<LeaderboardEntry[]>([])
const awards = ref<AwardEntry[]>([])

function medal(rank: number) {
  if (rank === 1) return '🥇'
  if (rank === 2) return '🥈'
  if (rank === 3) return '🥉'
  return null
}

onMounted(async () => {
  await admin.fetchEvent(eventId.value)
  board.value = await unwrap<LeaderboardEntry[]>(
    await api.get(`/admin/events/${eventId.value}/leaderboard`, { params: { limit: 50 } })
  )
  try {
    awards.value = await unwrap<AwardEntry[]>(await api.get(`/admin/events/${eventId.value}/awards`))
  } catch {
    awards.value = []
  }
})
</script>

<template>
  <div>
    <AdminPageHeader
      title="Leaderboard"
      subtitle="Total score → tasks completed → earliest finish time"
    />

    <div class="admin-panel mb-6">
      <div class="admin-table-wrap border-0 shadow-none">
        <table class="admin-table">
          <thead>
            <tr>
              <th class="w-16">Rank</th>
              <th>Participant</th>
              <th>Tasks</th>
              <th class="text-right">Score</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in board" :key="entry.participant_id">
              <td class="text-lg font-bold">
                <span v-if="medal(entry.rank)">{{ medal(entry.rank) }}</span>
                <span v-else>{{ entry.rank }}</span>
              </td>
              <td>
                <p class="font-semibold">{{ entry.display_name }}</p>
                <p v-if="entry.is_finished" class="text-xs text-slate-500">Finished</p>
              </td>
              <td class="text-slate-600">{{ entry.tasks_completed ?? 0 }}</td>
              <td class="text-right text-lg font-bold text-indigo-600">{{ entry.score }}</td>
            </tr>
            <tr v-if="!board.length">
              <td colspan="4" class="admin-empty">No scores yet.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <section v-if="awards.length" class="admin-panel">
      <div class="admin-panel-header">
        <h2 class="admin-panel-title">Awards</h2>
      </div>
      <div class="admin-panel-body">
        <ul class="space-y-2">
          <li
            v-for="a in awards"
            :key="a.id"
            class="flex items-center justify-between rounded-lg border border-slate-100 px-4 py-3"
          >
            <span class="font-semibold">#{{ a.place }} {{ a.award_type }}</span>
            <span class="text-slate-600">{{ a.score }} pts · {{ a.tasks_completed }} tasks</span>
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>
