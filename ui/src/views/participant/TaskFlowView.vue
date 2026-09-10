<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SelfieCamera from '@/components/participant/SelfieCamera.vue'
import SignaturePad from '@/components/participant/SignaturePad.vue'
import { useEventMode } from '@/composables/useEventMode'
import { useEventStore } from '@/stores/event'
import { useTaskFlowStore } from '@/stores/taskFlow'
import { useTasksStore } from '@/stores/tasks'
import type { TaskFlowStep } from '@/types/taskFlow'
import type { ParticipantTask } from '@/types'
import { getErrorMessage } from '@/utils/errors'

const route = useRoute()
const router = useRouter()
const eventStore = useEventStore()
const { showTaskPoints, canCompleteTasks } = useEventMode()
const tasksStore = useTasksStore()
const flowStore = useTaskFlowStore()

const participantTaskId = computed(() => Number(route.params.participantTaskId))
const task = ref<ParticipantTask | null>(null)
const step = ref<TaskFlowStep>('camera')
const inputMode = ref<'choose' | 'photo' | 'name'>('choose')
const partnerName = ref('')
const signPadRef = ref<InstanceType<typeof SignaturePad> | null>(null)
const error = ref('')
const completionSummary = ref<{ points: number; speedBonus: number } | null>(null)

const isBingoChallenge = computed(() => Boolean(task.value?.bingo))
const canSubmitName = computed(() => partnerName.value.trim().length >= 2)

const usesSelfieFlow = computed(
  () =>
    task.value?.type === 'scan' ||
    task.value?.type === 'selfie' ||
    Boolean(task.value?.bingo)
)

const meetProgressLabel = computed(() => {
  const m = task.value?.slug?.match(/^meet-person-(\d+)-of-(\d+)$/)
  if (m) return `${m[1]} of ${m[2]}`
  return null
})

const headerTitle = computed(() => {
  if (meetProgressLabel.value) return `Selfie · ${meetProgressLabel.value}`
  if (isBingoChallenge.value) return 'Selfie challenge'
  return 'Take a selfie'
})

function syncProgressFromTask(t: ParticipantTask) {
  task.value = { ...t }
}

onMounted(async () => {
  await tasksStore.fetchTasks()
  const found =
    tasksStore.tasks.find((t) => t.id === participantTaskId.value) ?? null
  if (!found) {
    error.value = 'Task not found'
    step.value = 'error'
    return
  }
  syncProgressFromTask(found)

  if (task.value!.status === 'completed') {
    step.value = 'complete'
    return
  }
  if (!canCompleteTasks.value) {
    const s = eventStore.event?.status
    error.value =
      s === 'ended'
        ? 'This event has ended.'
        : 'This event is not open yet. Ask the host to go live.'
    step.value = 'error'
    return
  }

  const remote = await flowStore.fetchState(participantTaskId.value)
  if (remote.status === 'completed') {
    step.value = 'complete'
    return
  }
  if (remote.progress_count != null && task.value) {
    task.value = {
      ...task.value,
      progress_count: remote.progress_count,
      target_count: remote.target_count ?? task.value.target_count,
    }
  }
  if (usesSelfieFlow.value) {
    step.value = 'camera'
  } else {
    step.value = 'select'
  }
})

onUnmounted(() => {
  flowStore.reset()
})

function goBack() {
  if (step.value === 'camera' && inputMode.value !== 'choose') {
    inputMode.value = 'choose'
    return
  }
  router.push({ name: 'tasks' })
}

async function finishFromResult(result: import('@/types/taskFlow').TaskCompleteResult) {
  if (result.task_finished === false && result.target_count && result.target_count > 1) {
    await tasksStore.fetchTasks()
    router.push({ name: 'tasks' })
    return
  }

  completionSummary.value = {
    points: result.points_awarded,
    speedBonus: result.speed_bonus ?? 0,
  }
  await tasksStore.fetchTasks()
  await eventStore.fetchMe()
  step.value = 'complete'
}

async function onSelfieCapture(blob: Blob) {
  step.value = 'uploading'
  error.value = ''
  try {
    const uploadInfo = await flowStore.uploadSelfie(participantTaskId.value, blob)
    const result = await flowStore.completeTask(participantTaskId.value, {
      selfie_id: uploadInfo.selfie_id,
    })
    await finishFromResult(result)
  } catch (e) {
    error.value = getErrorMessage(e)
    step.value = 'camera'
    inputMode.value = 'photo'
  }
}

async function submitName() {
  if (!canSubmitName.value) return
  step.value = 'uploading'
  error.value = ''
  try {
    const result = await flowStore.completeTask(participantTaskId.value, {
      partner_name: partnerName.value.trim(),
      partner_sign: signPadRef.value?.toDataURL() || undefined,
    })
    await finishFromResult(result)
  } catch (e) {
    error.value = getErrorMessage(e)
    step.value = 'camera'
    inputMode.value = 'name'
  }
}
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col px-3 pb-4 pt-2">
    <header class="mb-4 flex items-center gap-3">
      <button type="button" class="game-back-btn" aria-label="Back" @click="goBack">←</button>
      <h1 class="game-heading min-w-0 flex-1 truncate text-lg">{{ headerTitle }}</h1>
    </header>

    <p v-if="error" class="game-error mb-4 px-3 py-2 text-sm" role="alert">
      {{ error }}
    </p>

    <!-- Camera / name (selfie tasks) -->
    <div v-if="step === 'camera'" class="flex flex-1 flex-col gap-4">
      <div v-if="inputMode === 'choose'" class="mt-6 flex flex-col gap-3">
        <button type="button" class="btn-primary min-h-14 w-full" @click="inputMode = 'photo'">
          Take photo
        </button>
        <button type="button" class="btn-secondary min-h-14 w-full" @click="inputMode = 'name'">
          Name &amp; sign
        </button>
      </div>

      <div v-else-if="inputMode === 'name'" class="flex flex-col gap-3">
        <label class="game-label" for="flow-partner-name">Their name</label>
        <input
          id="flow-partner-name"
          v-model="partnerName"
          type="text"
          maxlength="120"
          class="input"
          placeholder="Who did you meet?"
        />
        <label class="game-label" id="flow-partner-sign-label">
          Sign <span class="font-normal text-slate-400">(optional)</span>
        </label>
        <SignaturePad aria-labelledby="flow-partner-sign-label" ref="signPadRef" />
        <button
          type="button"
          class="btn-primary mt-2 min-h-12 w-full"
          :disabled="!canSubmitName"
          @click="submitName"
        >
          Submit
        </button>
      </div>

      <SelfieCamera
        v-else
        @capture="onSelfieCapture"
        @error="(m) => (error = m)"
      />
    </div>

    <!-- Non-selfie fallback (rare) -->
    <div v-else-if="step === 'select' && task" class="flex flex-1 flex-col justify-center gap-4">
      <p class="game-muted text-center text-sm">This task is not available on mobile yet.</p>
      <button type="button" class="btn-secondary w-full" @click="goBack">Back to tasks</button>
    </div>

    <!-- Uploading -->
    <div v-else-if="step === 'uploading'" class="flex flex-1 flex-col items-center justify-center gap-3">
      <div class="game-spinner h-10 w-10 animate-spin rounded-full border-2 border-t-transparent" />
      <p class="game-muted text-sm">Saving…</p>
    </div>

    <!-- Complete -->
    <div v-else-if="step === 'complete'" class="flex flex-1 flex-col items-center justify-center gap-4 text-center">
      <div class="game-complete-card w-full max-w-sm">
        <p class="text-5xl">🎉</p>
        <h2 class="mt-2 text-xl font-black text-amber-950">Done!</h2>
        <p v-if="completionSummary && showTaskPoints" class="game-points mt-2">
          +{{ completionSummary.points }} pts
          <span v-if="completionSummary.speedBonus > 0" class="block text-sm font-normal opacity-80">
            includes {{ completionSummary.speedBonus }} speed bonus
          </span>
        </p>
        <button type="button" class="btn-primary mt-4 min-h-12 w-full" @click="router.push({ name: 'tasks' })">
          Back to tasks
        </button>
      </div>
    </div>

    <!-- Error terminal -->
    <div v-else-if="step === 'error'" class="flex flex-1 flex-col justify-center gap-4 text-center">
      <button type="button" class="btn-secondary w-full" @click="router.push({ name: 'tasks' })">
        Back to tasks
      </button>
    </div>
  </div>
</template>
