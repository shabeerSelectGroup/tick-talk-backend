<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import BingoCardGrid from '@/components/participant/BingoCardGrid.vue'
import BingoSelfieModal from '@/components/participant/BingoSelfieModal.vue'
import GameInstructionsModal from '@/components/participant/GameInstructionsModal.vue'
import EventModeBadge from '@/components/EventModeBadge.vue'
import type { ParticipantTask } from '@/types'
import { useEventMode } from '@/composables/useEventMode'
import { useEventStore } from '@/stores/event'
import { useTasksStore } from '@/stores/tasks'
import { buildBingoSections, isBingoEvent, mergeBingoTasks } from '@/utils/bingoTasks'
import { buildMeetSections, isIntroTask, isMeetSeriesTask } from '@/utils/taskDisplay'
import { countCompletedTasks, isTaskCompleted } from '@/utils/taskStatus'
import { getErrorMessage } from '@/utils/errors'
import { prewarmCamera } from '@/utils/cameraPrewarm'

const emit = defineEmits<{ 'open-profile': []; 'open-leaderboard': [] }>()
const router = useRouter()
const tasksStore = useTasksStore()
const eventStore = useEventStore()
const { canCompleteTasks, showTaskPoints, isCompetition } = useEventMode()
const error = ref('')
const loading = ref(true)
const bingoModalOpen = ref(false)
const activeSelfieTask = ref<ParticipantTask | null>(null)
const showInstructionsModal = ref(false)

const eventMode = computed(() => eventStore.event?.mode)
const showBingoUI = computed(() => isBingoEvent(tasksStore.tasks, eventMode.value))

const displayTasks = computed(() =>
  showBingoUI.value ? mergeBingoTasks(tasksStore.tasks) : tasksStore.tasks
)

const bingoSections = computed(() => buildBingoSections(displayTasks.value))
const bingoCompletedCount = computed(() => countCompletedTasks(displayTasks.value))
const meetSections = computed(() => buildMeetSections(tasksStore.tasks))
const otherTasks = computed(() =>
  tasksStore.tasks.filter((t) => !isMeetSeriesTask(t) && !isIntroTask(t))
)
const showMeetChecklist = computed(() => !showBingoUI.value && meetSections.value.length > 0)
const meetProgress = computed(() => {
  const total = meetSections.value.reduce((n, s) => n + s.tasks.length, 0)
  const done = meetSections.value.reduce((n, s) => n + s.completed, 0)
  return { done, total }
})

const canToggle = canCompleteTasks

const allTasksCompleted = computed(
  () => eventStore.participant?.all_tasks_completed ?? bingoCompletedCount.value >= displayTasks.value.length
)
const leaderboardAvailable = computed(
  () => eventStore.participant?.leaderboard_available ?? false
)

const pageTitle = computed(() =>
  showBingoUI.value ? 'Networking Bingo' : 'Your tasks'
)

onMounted(async () => {
  loading.value = true
  try {
    if (!eventStore.event) await eventStore.fetchMe()
    await tasksStore.fetchTasks()
    if (showBingoUI.value && !tasksStore.tasks.some((t) => (t.bingo || t.slug?.startsWith('bingo-')) && t.id > 0)) {
      await tasksStore.fetchTasks()
    }
    if (showBingoUI.value) void prewarmCamera()

    if (eventStore.event) {
      const key = `hasSeenInstructions_${eventStore.event.id}`
      if (!localStorage.getItem(key)) {
        showInstructionsModal.value = true
      }
    }
  } finally {
    loading.value = false
  }
})

function closeInstructions() {
  if (eventStore.event) {
    const key = `hasSeenInstructions_${eventStore.event.id}`
    localStorage.setItem(key, 'true')
  }
  showInstructionsModal.value = false
}

watch(showBingoUI, (bingo) => {
  if (bingo) void prewarmCamera()
})

watch(bingoModalOpen, (open) => {
  if (!open) void prewarmCamera()
})

function canStartTask(task: ParticipantTask) {
  if (isTaskCompleted(task.status)) return false
  return task.type === 'scan' || task.type === 'selfie' || (task.type === 'manual' && !task.bingo)
}

async function startTaskAction(task: ParticipantTask) {
  if (task.id < 0 || !canToggle.value) return
  error.value = ''

  if (task.type === 'manual' && !task.bingo) {
    try {
      await tasksStore.toggleBingoTask(task.id)
      await eventStore.fetchMe()
    } catch (e) {
      error.value = getErrorMessage(e)
    }
    return
  }

  if (task.type === 'scan' || task.type === 'selfie') {
    await router.push({ name: 'task-flow', params: { participantTaskId: String(task.id) } })
  }
}

const selfieStartMode = ref<'choose' | 'photo' | 'name'>('choose')
const selfieEmblem = ref<string | undefined>()

function openSelfieChallenge(
  task: ParticipantTask,
  mode: 'photo' | 'name' | 'choose' = 'choose',
  emblem?: string,
) {
  if (!canToggle.value) return
  if (task.id < 0) {
    error.value = 'Syncing challenges… refresh in a moment or re-open this page.'
    void tasksStore.fetchTasks()
    return
  }
  if (isTaskCompleted(task.status)) return
  void prewarmCamera()
  selfieStartMode.value = mode
  selfieEmblem.value = emblem
  activeSelfieTask.value = task
  bingoModalOpen.value = true
}

function closeSelfieModal() {
  bingoModalOpen.value = false
  activeSelfieTask.value = null
  selfieStartMode.value = 'choose'
  selfieEmblem.value = undefined
}

async function onSelfieChallengeCompleted(payload: {
  taskId: number
  imageUrl: string
  thumbnailUrl: string | null
}) {
  error.value = ''
  tasksStore.patchTaskSelfie(payload.taskId, {
    status: 'completed',
    ...(payload.imageUrl
      ? {
          selfie_image_url: payload.imageUrl,
          selfie_thumbnail_url: payload.thumbnailUrl,
        }
      : {}),
  })
  // Refresh in background so the card keeps the photo immediately
  void tasksStore.fetchTasks().then(() => eventStore.fetchMe()).catch((e) => {
    error.value = getErrorMessage(e)
  })
}
</script>

<template>
  <div
    class="flex flex-1 flex-col"
    :class="showBingoUI ? 'gap-2 px-1 pb-4 pt-1' : 'gap-4 px-3 pb-6 pt-2'"
  >
    <div
      v-if="!showBingoUI"
      class="flex items-center justify-between"
    >
      <h1 class="game-heading text-2xl">{{ pageTitle }}</h1>
      <div class="flex items-center gap-3">
        <button
          type="button"
          class="flex items-center justify-center rounded-full bg-slate-100 p-2 text-slate-500 hover:bg-slate-200"
          @click="emit('open-leaderboard')"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path><path d="M4 22h16"></path><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"></path><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"></path><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"></path></svg>
        </button>
        <EventModeBadge />
      </div>
    </div>

    <p v-if="!showBingoUI" class="game-muted text-sm">
      {{ tasksStore.pendingCount }} remaining
    </p>

    <p v-if="showBingoUI && !canToggle" class="game-alert px-3 py-2 text-sm">
      <template v-if="eventStore.event?.status === 'draft'">
        Event is in draft — the host must start the game before you can check off challenges.
      </template>
      <template v-else-if="eventStore.event?.status === 'ended'">
        This event has ended.
      </template>
      <template v-else>
        You can preview the list below. Selfie check-offs unlock when the event is live.
      </template>
    </p>

    <div v-if="allTasksCompleted && leaderboardAvailable" class="card px-4 py-3">
      <p class="font-black text-amber-900">All challenges complete!</p>
      <p class="mt-1 text-sm opacity-80">
        Your score includes speed bonuses for fast completions. Check the leaderboard.
      </p>
      <button
        type="button"
        class="btn-primary mt-3 min-h-11 w-full"
        @click="router.push({ name: 'leaderboard' })"
      >
        View leaderboard
      </button>
    </div>

    <p v-if="error" class="game-error px-3 py-2 text-sm">{{ error }}</p>

    <p v-if="loading" class="game-muted text-center text-sm">Loading challenges…</p>

    <!-- Human bingo card -->
    <BingoCardGrid
      v-else-if="showBingoUI && bingoSections.length"
      :sections="bingoSections"
      :completed-count="bingoCompletedCount"
      :total-count="displayTasks.length"
      :can-toggle="canToggle"
      :show-points="showTaskPoints && isCompetition"
      :show-leaderboard="eventStore.showLeaderboard"
      @select="openSelfieChallenge"
      @completed="onSelfieChallengeCompleted"
      @nav-rank="emit('open-leaderboard')"
      @nav-you="emit('open-profile')"
    />

    <!-- Competition: meet-new-people uses the same tap → selfie flow as networking -->
    <template v-else-if="!showBingoUI">
      <div v-if="showMeetChecklist" class="game-progress-card">
        <p class="game-stat text-lg">
          {{ meetProgress.done }} / {{ meetProgress.total }}
        </p>
        <p class="game-stat-label">people met (selfies)</p>
      </div>

      <p v-if="showMeetChecklist" class="game-muted text-sm">
        Tap each row when you’ve taken a selfie with someone new.
      </p>

      <section
        v-for="section in meetSections"
        :key="section.key"
        class="space-y-2"
      >
        <div class="game-section-sticky">
          <h2 class="game-section-title">Meet new people</h2>
          <p class="game-muted text-xs">
            {{ section.completed }} / {{ section.tasks.length }} completed
          </p>
          <p v-if="section.summary" class="game-muted mt-1 text-xs leading-snug">
            {{ section.summary }}
          </p>
        </div>

        <ul class="space-y-2">
          <li v-for="task in section.tasks" :key="task.id">
            <button
              type="button"
              class="game-task-row"
              :class="{ 'game-task-row--done': isTaskCompleted(task.status) }"
              :disabled="!canToggle || isTaskCompleted(task.status)"
              @click="openSelfieChallenge(task)"
            >
              <span
                class="game-task-check"
                :class="{ 'game-task-check--done': isTaskCompleted(task.status) }"
                aria-hidden="true"
              >
                ✓
              </span>
              <span class="min-w-0 flex-1">
                <span
                  class="game-task-title"
                  :class="{ 'game-task-title--done': isTaskCompleted(task.status) }"
                >
                  {{ task.title }}
                </span>
              </span>
            </button>
          </li>
        </ul>
      </section>

      <section v-if="otherTasks.length" class="space-y-2">
        <h2 class="game-muted text-sm font-semibold">Other challenges</h2>
        <ul class="space-y-2">
          <li
            v-for="task in otherTasks"
            :key="task.id"
            class="card flex items-center gap-3"
          >
            <div class="min-w-0 flex-1">
              <p
                class="font-medium leading-snug"
                :class="isTaskCompleted(task.status) ? 'opacity-70 line-through' : ''"
              >
                {{ task.title }}
              </p>
            </div>
            <button
              v-if="canStartTask(task)"
              type="button"
              class="btn-primary shrink-0 px-4 py-2 text-sm"
              :disabled="!canToggle || tasksStore.togglingId === task.id"
              @click="startTaskAction(task)"
            >
              {{ tasksStore.togglingId === task.id ? '…' : 'Start' }}
            </button>
            <span v-else class="game-badge-done">Done ✓</span>
          </li>
        </ul>
      </section>

      <p v-if="!tasksStore.tasks.length" class="game-muted text-sm">
        No tasks yet. Ask the host to add challenges or start the game.
      </p>
    </template>

    <p v-else-if="showBingoUI && !bingoSections.length" class="game-muted text-sm">
      Could not load challenges. Pull to refresh or rejoin the event.
    </p>

    <BingoSelfieModal
      :open="bingoModalOpen"
      :task="activeSelfieTask"
      :start-mode="selfieStartMode"
      :emblem="selfieEmblem"
      @close="closeSelfieModal"
      @completed="onSelfieChallengeCompleted"
    />

    <GameInstructionsModal
      :open="showInstructionsModal"
      :is-competition="isCompetition"
      @close="closeInstructions"
      @start="closeInstructions"
    />
  </div>
</template>
