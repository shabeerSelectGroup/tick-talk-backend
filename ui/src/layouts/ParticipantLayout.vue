<script setup lang="ts">
import { RouterView, useRoute, useRouter } from 'vue-router'
import { computed, onMounted, onUnmounted, provide, ref } from 'vue'
import { api, unwrap } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useEventStore } from '@/stores/event'
import { useEventMode } from '@/composables/useEventMode'
import type { LeaderboardEntry } from '@/types'
import { getErrorMessage } from '@/utils/errors'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const eventStore = useEventStore()
const { showScores } = useEventMode()

const profileOpen = ref(false)
const leaderboardOpen = ref(false)
const lbEntries = ref<LeaderboardEntry[]>([])
const lbError = ref('')
const lbLoading = ref(false)

provide('openProfile', () => { profileOpen.value = true })
provide('openLeaderboard', () => { openLeaderboard() })

const showNav = computed(() => route.meta.requiresSession === true)
const isJoinRoute = computed(() => route.meta.guest === true)
const isTasksRoute = computed(() => route.name === 'tasks')
const isImmersiveRoute = computed(() => route.name === 'task-flow')

const myId = computed(() => eventStore.participant?.id)

function medal(rank: number) {
  if (rank === 1) return '🥇'
  if (rank === 2) return '🥈'
  if (rank === 3) return '🥉'
  return null
}

async function openLeaderboard() {
  leaderboardOpen.value = true
  lbLoading.value = true
  lbError.value = ''
  try {
    lbEntries.value = await unwrap<LeaderboardEntry[]>(await api.get('/participant/leaderboard'))
  } catch (e) {
    lbError.value = getErrorMessage(e)
  } finally {
    lbLoading.value = false
  }
}

onMounted(async () => {
  document.documentElement.classList.add('mobile-app')

  if (auth.isParticipant && !eventStore.event && !eventStore.participant) {
    try {
      await eventStore.fetchMe()
    } catch {
      /* session invalid — guard will redirect */
    }
  }
  if (showNav.value) {
    void eventStore.fetchTimer()
  }
})

onUnmounted(() => {
  document.documentElement.classList.remove('mobile-app')
})

function leaveEvent() {
  profileOpen.value = false
  auth.clearSession()
  router.replace({ name: 'join' })
}
</script>

<template>
  <div
    class="game-theme"
    :class="[
      showNav ? 'participant-shell' : isJoinRoute ? 'join-layout' : 'page-container',
      showNav && !isJoinRoute ? '' : 'game-theme--decor',
    ]"
  >
    <div v-if="showNav" class="flex h-dvh flex-1 flex-col overflow-hidden">

      <main
        class="participant-main flex-1"
        :class="[
          isTasksRoute ? '!px-1.5 !pt-1' : '',
          isImmersiveRoute ? 'mobile-app-main--immersive !px-0 !pt-0' : '',
        ]"
      >
        <RouterView v-slot="{ Component }">
          <Transition name="tt-page" mode="out-in">
            <component
              :is="Component"
              @open-profile="profileOpen = true"
              @open-leaderboard="openLeaderboard"
            />
          </Transition>
        </RouterView>
      </main>

    </div>

    <RouterView v-else v-slot="{ Component }">
      <Transition name="tt-page" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>

    <Teleport to="body">
      <!-- Shared backdrop -->
      <Transition name="join-backdrop">
        <button
          v-if="profileOpen || leaderboardOpen"
          type="button"
          class="fixed inset-0 z-[60] border-0 bg-black/30 backdrop-blur-[2px]"
          aria-label="Close"
          @click="profileOpen = false; leaderboardOpen = false"
        />
      </Transition>

      <!-- Profile sheet -->
      <Transition name="join-sheet">
        <aside
          v-if="profileOpen"
          class="mobile-bottom-sheet"
          role="dialog"
          aria-label="Your profile"
        >
          <div class="mobile-bottom-sheet__handle" aria-hidden="true" />
          <h2 class="text-lg font-extrabold text-slate-800">Your profile</h2>
          <div class="mt-4 space-y-4">
            <div>
              <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Name</p>
              <p class="text-lg font-bold text-slate-800">
                {{ eventStore.participant?.display_name }}
              </p>
            </div>
            <div>
              <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Event</p>
              <p class="text-sm text-slate-700">
                {{ eventStore.event?.name }}
                <span v-if="eventStore.event?.code" class="font-mono font-bold">
                  ({{ eventStore.event.code }})
                </span>
              </p>
            </div>
            <div>
              <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Participant ID</p>
              <p class="font-mono text-base font-bold text-slate-800">#{{ auth.participantId }}</p>
            </div>
          </div>
          <button
            type="button"
            class="btn-secondary mt-6 w-full min-h-12 border-slate-300 bg-slate-100 text-slate-800"
            @click="leaveEvent"
          >
            Leave event
          </button>
        </aside>
      </Transition>

      <!-- Leaderboard sheet -->
      <Transition name="join-sheet">
        <aside
          v-if="leaderboardOpen"
          class="mobile-bottom-sheet"
          role="dialog"
          aria-label="Leaderboard"
        >
          <div class="mobile-bottom-sheet__handle" aria-hidden="true" />
          <h2 class="text-lg font-extrabold text-slate-800">
            {{ eventStore.isCompetition ? 'Leaderboard' : 'Participants' }}
          </h2>
          <p v-if="eventStore.isCompetition" class="mt-1 text-xs text-slate-400">Ranked by score, then tasks, then finish time</p>
          <p v-else class="mt-1 text-xs text-slate-400">Players who have joined this event</p>

          <div class="mt-4">
            <p v-if="lbLoading" class="text-center text-sm text-slate-400 py-4">Loading…</p>
            <p v-else-if="lbError" class="text-sm text-red-500 py-2">{{ lbError }}</p>
            <p v-else-if="!lbEntries.length" class="text-sm text-slate-400 py-4 text-center">
              No players yet.
            </p>
            <ol v-else class="space-y-2">
              <li
                v-for="(entry, index) in lbEntries"
                :key="entry.participant_id"
                class="flex items-center gap-3 rounded-xl px-3 py-3"
                :class="entry.participant_id === myId
                  ? 'bg-amber-50 ring-2 ring-amber-300'
                  : 'bg-slate-50'"
              >
                <!-- Position badge -->
                <span v-if="eventStore.isCompetition" class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-base font-black shadow-sm">
                  <span v-if="index < 3">{{ medal(index + 1) }}</span>
                  <span v-else class="text-slate-600">{{ index + 1 }}</span>
                </span>
                <!-- Name & tasks -->
                <div class="min-w-0 flex-1">
                  <p class="truncate font-bold text-slate-800">{{ entry.display_name }}</p>
                  <p class="text-xs text-slate-400">{{ entry.tasks_completed ?? 0 }} tasks</p>
                </div>
                <!-- Score -->
                <span v-if="showScores" class="text-lg font-black text-amber-600">{{ entry.score }}</span>
              </li>
            </ol>
          </div>
        </aside>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.join-backdrop-enter-active,
.join-backdrop-leave-active {
  transition: opacity 0.25s ease;
}

.join-backdrop-enter-from,
.join-backdrop-leave-to {
  opacity: 0;
}

.join-sheet-enter-active {
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}

.join-sheet-leave-active {
  transition: transform 0.22s ease;
}

.join-sheet-enter-from,
.join-sheet-leave-to {
  transform: translateY(100%);
}
</style>
