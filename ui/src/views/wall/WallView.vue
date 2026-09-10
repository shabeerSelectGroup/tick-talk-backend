<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, unwrap } from '@/api/client'
import WallLeaderboard from '@/components/wall/WallLeaderboard.vue'
import WallSelfieFeed from '@/components/wall/WallSelfieFeed.vue'
import WallTaskFilter from '@/components/wall/WallTaskFilter.vue'
import WallStatsBar from '@/components/wall/WallStatsBar.vue'
import WallTimer from '@/components/wall/WallTimer.vue'
import TickTalkLogo from '@/components/TickTalkLogo.vue'
import { useEventLive } from '@/composables/useEventLive'
import { useWallProjector } from '@/composables/useWallProjector'
import type { EventPublic, LeaderboardEntry } from '@/types'
import type { WallSelfie, WallStats, WallTask, WallTimer as WallTimerType } from '@/types/wall'
import type { WsLeaderboardUpdated, WsSelfieUploaded } from '@/types/ws'
import { resolveMediaUrl } from '@/utils/mediaUrl'

const route = useRoute()
const eventCode = computed(() => String(route.params.eventCode || '').toUpperCase())

const loading = ref(true)
const error = ref('')
const event = ref<EventPublic | null>(null)
const timer = ref<WallTimerType | null>(null)
const stats = ref<WallStats | null>(null)
const selfies = ref<WallSelfie[]>([])
const wallTasks = ref<WallTask[]>([])
const selectedTaskId = ref<number | null>(null)
const leaderboard = ref<LeaderboardEntry[]>([])

const eventId = computed(() => event.value?.id ?? null)
const isCompetition = computed(() => event.value?.mode === 'competition')
const showLeaderboard = computed(
  () =>
    isCompetition.value &&
    (stats.value?.leaderboard_visible ?? stats.value?.leaderboard_enabled ?? false)
)
const showScores = computed(() => stats.value?.show_scores ?? false)

const { projectorMode, toggleProjector } = useWallProjector()

let statsRefreshTimer: ReturnType<typeof setTimeout> | null = null

function scheduleStatsRefresh() {
  if (statsRefreshTimer) clearTimeout(statsRefreshTimer)
  statsRefreshTimer = setTimeout(() => void refreshStats(), 800)
}

function prependSelfie(payload: WsSelfieUploaded) {
  if (!payload.selfie_id) return
  if (!payload.image_url && !payload.thumbnail_url) return
  const existing = selfies.value.find((s) => s.id === payload.selfie_id)
  if (existing) return
  if (selectedTaskId.value !== null && payload.task_id !== selectedTaskId.value) return
  const full = resolveMediaUrl(payload.image_url)
  const thumb = resolveMediaUrl(payload.thumbnail_url)
  const item: WallSelfie = {
    id: payload.selfie_id,
    participant_id: payload.participant_id,
    display_name: payload.display_name || 'Participant',
    company: null,
    task_id: payload.task_id ?? null,
    task_title: payload.task_title ?? null,
    image_url: full || thumb,
    thumbnail_url: thumb || full,
    uploaded_at: new Date().toISOString(),
    status: 'pending',
  }
  selfies.value = [item, ...selfies.value].slice(0, 48)
  if (payload.task_id && wallTasks.value.length) {
    const t = wallTasks.value.find((x) => x.id === payload.task_id)
    if (t) t.selfie_count += 1
  }
  if (stats.value) stats.value = { ...stats.value, selfies: stats.value.selfies + 1 }
}

async function refreshStats() {
  if (!eventCode.value) return
  try {
    stats.value = await unwrap<WallStats>(await api.get(`/wall/${eventCode.value}/stats`))
  } catch {
    /* non-fatal */
  }
}

async function refreshTimer() {
  if (!eventCode.value) return
  try {
    timer.value = await unwrap<WallTimerType>(await api.get(`/wall/${eventCode.value}/timer`))
  } catch {
    /* non-fatal */
  }
}

async function loadSelfies() {
  if (!eventCode.value) return
  const params: { limit: number; task_id?: number } = { limit: 48 }
  if (selectedTaskId.value !== null) params.task_id = selectedTaskId.value
  selfies.value = await unwrap<WallSelfie[]>(
    await api.get(`/wall/${eventCode.value}/selfies`, { params })
  )
}

async function onTaskFilterSelect(taskId: number | null) {
  selectedTaskId.value = taskId
  await loadSelfies()
}

async function load() {
  loading.value = true
  error.value = ''
  const code = eventCode.value
  try {
    const [ev, t, st, taskList, selfieList] = await Promise.all([
      unwrap<EventPublic>(await api.get(`/wall/${code}`)),
      unwrap<WallTimerType>(await api.get(`/wall/${code}/timer`)),
      unwrap<WallStats>(await api.get(`/wall/${code}/stats`)),
      unwrap<WallTask[]>(await api.get(`/wall/${code}/tasks`)),
      unwrap<WallSelfie[]>(await api.get(`/wall/${code}/selfies`, { params: { limit: 48 } })),
    ])
    event.value = ev
    timer.value = t
    stats.value = st
    wallTasks.value = taskList
    selfies.value = selfieList
    try {
      leaderboard.value = await unwrap<LeaderboardEntry[]>(
        await api.get(`/wall/${code}/leaderboard`)
      )
    } catch {
      leaderboard.value = []
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unable to load live wall'
  } finally {
    loading.value = false
  }
}

const { connect, disconnect, connected } = useEventLive(eventId, 'wall', {
  onSelfieUploaded(payload, _msg) {
    prependSelfie(payload)
    scheduleStatsRefresh()
  },
  onLeaderboardUpdated(payload: WsLeaderboardUpdated) {
    if (payload.top?.length) leaderboard.value = payload.top as LeaderboardEntry[]
  },
  onParticipantJoined() {
    scheduleStatsRefresh()
  },
  onTaskCompleted() {
    scheduleStatsRefresh()
    void reloadLeaderboard()
  },
  onEventStarted() {
    void refreshTimer()
    scheduleStatsRefresh()
  },
  onEventPaused() {
    void refreshTimer()
  },
  onEventEnded() {
    void refreshTimer()
    scheduleStatsRefresh()
    void reloadLeaderboard()
  },
})

async function reloadLeaderboard() {
  if (!showLeaderboard.value || !eventCode.value) return
  try {
    leaderboard.value = await unwrap<LeaderboardEntry[]>(
      await api.get(`/wall/${eventCode.value}/leaderboard`)
    )
  } catch {
    /* hidden until event end etc. */
  }
}

onMounted(async () => {
  await load()
  connect()
})

onUnmounted(() => {
  disconnect()
  if (statsRefreshTimer) clearTimeout(statsRefreshTimer)
})
</script>

<template>
  <div
    class="game-theme game-theme--decor wall-root min-h-dvh tt-animate-fade-in"
    :class="{ 'wall-projector': projectorMode }"
  >
    <div class="game-wall-ambient pointer-events-none fixed inset-0" aria-hidden="true" />

    <div class="relative mx-auto flex min-h-dvh max-w-[1600px] flex-col px-3 py-4 sm:px-6 sm:py-6">
      <header class="mb-4 flex flex-wrap items-start justify-between gap-3 sm:mb-6">
        <div class="min-w-0 flex-1">
          <TickTalkLogo class="mb-2 text-[0.8em] sm:text-[1em]" />
          <h1
            class="game-heading truncate"
            :class="projectorMode ? 'text-3xl sm:text-5xl' : 'text-2xl sm:text-4xl'"
          >
            {{ event?.name ?? 'Live Wall' }}
          </h1>
          <p class="game-muted mt-1 font-mono text-sm">{{ eventCode }}</p>
        </div>

        <div class="flex shrink-0 flex-wrap items-center gap-2">
          <span
            class="game-live-badge inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium"
            :class="connected ? '' : 'game-live-badge--off'"
          >
            <span
              class="h-2 w-2 rounded-full"
              :class="connected ? 'animate-pulse bg-emerald-400' : 'bg-amber-700/60'"
            />
            {{ connected ? 'Live' : 'Connecting…' }}
          </span>
          <button
            type="button"
            class="game-wall-btn px-3 py-2 text-sm"
            :title="projectorMode ? 'Exit projector mode' : 'Full-screen projector mode'"
            @click="toggleProjector"
          >
            {{ projectorMode ? 'Exit projector' : 'Projector' }}
          </button>
        </div>
      </header>

      <div v-if="loading" class="flex flex-1 items-center justify-center py-24">
        <div class="game-spinner h-12 w-12 animate-spin rounded-full border-2 border-t-transparent" />
      </div>

      <div
        v-else-if="error"
        class="flex flex-1 flex-col items-center justify-center gap-4 py-24 text-center"
      >
        <p class="text-4xl">🚫</p>
        <p class="game-muted max-w-md">{{ error }}</p>
      </div>

      <template v-else-if="event && stats && timer">
        <div
          class="mb-6 grid gap-4"
          :class="
            projectorMode
              ? 'lg:grid-cols-[minmax(200px,280px)_1fr]'
              : 'md:grid-cols-[minmax(160px,220px)_1fr]'
          "
        >
          <WallTimer
            :remaining-seconds="timer.remaining_seconds"
            :status="timer.status"
            :large="projectorMode"
          />
          <WallStatsBar :stats="stats" :large="projectorMode" />
        </div>

        <div
          class="grid flex-1 gap-6"
          :class="
            showLeaderboard
              ? projectorMode
                ? 'lg:grid-cols-[1fr_minmax(280px,360px)]'
                : 'lg:grid-cols-[1fr_minmax(240px,320px)]'
              : ''
          "
        >
          <section>
            <h2
              class="game-section-title mb-3"
              :class="projectorMode ? 'text-xl' : ''"
            >
              Live selfies
            </h2>
            <WallTaskFilter
              v-if="wallTasks.length"
              class="mb-4"
              :tasks="wallTasks"
              :selected-task-id="selectedTaskId"
              :large="projectorMode"
              @select="onTaskFilterSelect"
            />
            <WallSelfieFeed :selfies="selfies" :large="projectorMode" />
          </section>

          <aside v-if="showLeaderboard" class="lg:sticky lg:top-6 lg:self-start">
            <h2
              class="game-section-title mb-3"
              :class="projectorMode ? 'text-xl' : ''"
            >
              Leaderboard
            </h2>
            <WallLeaderboard
              :entries="leaderboard"
              :show-scores="showScores"
              :large="projectorMode"
            />
          </aside>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.wall-root {
  color-scheme: dark;
  background: #ff6769 !important;
}

.wall-projector {
  font-size: 1.125rem;
}

.wall-projector :deep(.card),
.wall-projector :deep(.game-wall-stat),
.wall-projector :deep(.game-leaderboard-row) {
  border-radius: 1rem;
}
</style>
