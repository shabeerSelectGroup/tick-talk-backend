<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api, unwrap } from '@/api/client'
import { useEventLive } from '@/composables/useEventLive'
import { useEventMode } from '@/composables/useEventMode'
import type { LeaderboardEntry } from '@/types'
import { useEventStore } from '@/stores/event'
import { getErrorMessage } from '@/utils/errors'

const eventStore = useEventStore()
const { showScores } = useEventMode()
const entries = ref<LeaderboardEntry[]>([])
const error = ref('')

const eventId = computed(() => eventStore.event?.id ?? null)
const myId = computed(() => eventStore.participant?.id)

function medal(rank: number) {
  if (rank === 1) return '🥇'
  if (rank === 2) return '🥈'
  if (rank === 3) return '🥉'
  return null
}

function formatFinish(iso: string | null | undefined) {
  if (!iso) return null
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return null
  }
}

async function load() {
  try {
    entries.value = await unwrap<LeaderboardEntry[]>(await api.get('/participant/leaderboard'))
    error.value = ''
  } catch (e) {
    error.value = getErrorMessage(e)
  }
}

const { connect, disconnect } = useEventLive(eventId, 'leaderboard', {
  onLeaderboardUpdated(p) {
    if (p.top?.length) {
      entries.value = p.top as LeaderboardEntry[]
    } else {
      load()
    }
  },
})

onMounted(async () => {
  await eventStore.fetchMe()
  await load()
  connect()
})
onUnmounted(disconnect)
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-4 px-3 pb-4 pt-2 tt-animate-fade-in">
    <div>
      <h1 class="game-heading text-2xl">
        {{ eventStore.isCompetition ? 'Leaderboard' : 'Participants' }}
      </h1>
    </div>
    <p v-if="eventStore.isCompetition" class="game-muted text-xs">
      Ranked by score, then tasks completed, then finish time
    </p>
    <p v-else class="game-muted text-xs">
      Players who have joined this event
    </p>
    <p v-if="error" class="game-error px-3 py-2 text-sm" role="alert">
      {{ error }}
    </p>
    <p v-else-if="!entries.length" class="game-muted text-sm">
      No scores yet. Complete challenges to appear on the board.
    </p>
    <ol v-else class="tt-stagger space-y-2">
      <li
        v-for="entry in entries"
        :key="entry.participant_id"
        class="game-leaderboard-row flex items-center gap-3 p-4"
        :class="entry.participant_id === myId ? 'game-leaderboard-row--me' : ''"
      >
        <span v-if="eventStore.isCompetition" class="game-leaderboard-rank shrink-0">
          <span v-if="medal(entry.rank)">{{ medal(entry.rank) }}</span>
          <span v-else>{{ entry.rank }}</span>
        </span>
        <div class="min-w-0 flex-1">
          <p class="truncate font-bold">{{ entry.display_name }}</p>
          <p v-if="entry.company" class="truncate text-sm opacity-75">{{ entry.company }}</p>
          <p class="mt-0.5 text-xs opacity-70">
            {{ entry.tasks_completed ?? 0 }} tasks
            <span v-if="entry.is_finished && formatFinish(entry.finished_at)">
              · finished {{ formatFinish(entry.finished_at) }}
            </span>
          </p>
        </div>
        <span v-if="showScores" class="text-lg font-black text-amber-700">{{ entry.score }}</span>
      </li>
    </ol>
  </div>
</template>
