<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import SelfieCamera from '@/components/participant/SelfieCamera.vue'
import SignaturePad from '@/components/participant/SignaturePad.vue'
import { useRouter } from 'vue-router'
import { useEventMode } from '@/composables/useEventMode'
import { useEventStore } from '@/stores/event'
import { useTaskFlowStore } from '@/stores/taskFlow'
import type { ParticipantTask } from '@/types'
import { getErrorMessage } from '@/utils/errors'
import { prewarmCamera } from '@/utils/cameraPrewarm'
import { randomCardEmblem } from '@/utils/bingoTasks'

type ModalStep = 'camera' | 'uploading' | 'complete' | 'error'
type InputMode = 'choose' | 'photo' | 'name'

const props = defineProps<{
  open: boolean
  task: ParticipantTask | null
  startMode?: InputMode
  emblem?: string
}>()

const emit = defineEmits<{
  close: []
  completed: [
    payload: {
      taskId: number
      imageUrl: string
      thumbnailUrl: string | null
    },
  ]
}>()

const router = useRouter()
const eventStore = useEventStore()
const { canCompleteTasks, showTaskPoints } = useEventMode()
const flowStore = useTaskFlowStore()
const lastPoints = ref<{ total: number; speed: number } | null>(null)
const showLeaderboardPrompt = ref(false)

const step = ref<ModalStep>('camera')
const inputMode = ref<InputMode>('choose')
const partnerName = ref('')
const signPadRef = ref<InstanceType<typeof SignaturePad> | null>(null)
const error = ref('')
const processing = ref(false)

const canSubmit = canCompleteTasks
const canSubmitName = computed(
  () => partnerName.value.trim().length >= 2 && !processing.value
)
const cardEmblem = computed(() => {
  if (props.emblem) return props.emblem
  if (!props.task) return '🦋'
  return randomCardEmblem(props.task)
})
const taskPrompt = computed(() => {
  const task = props.task
  if (!task) return ''
  if (task.description?.trim()) return task.description.trim()
  return `Find someone who matches “${task.title}”, then take a selfie together.`
})
const cardMaxClass = computed(() =>
  inputMode.value === 'photo' ? 'max-w-md' : 'max-w-[320px]'
)

const capturedBlob = ref<Blob | null>(null)
const capturedUrl = ref<string | null>(null)
const cameraRef = ref<InstanceType<typeof SelfieCamera> | null>(null)

function onSelfieCapture(blob: Blob) {
  capturedBlob.value = blob
  capturedUrl.value = URL.createObjectURL(blob)
}

function handleGoBack() {
  if (capturedBlob.value) {
    if (capturedUrl.value) {
      URL.revokeObjectURL(capturedUrl.value)
    }
    capturedBlob.value = null
    capturedUrl.value = null
    cameraRef.value?.retake()
    return
  }
  if (inputMode.value !== 'choose') {
    if (props.startMode && props.startMode !== 'choose') {
      close()
      return
    }
    inputMode.value = 'choose'
    return
  }
  close()
}

function triggerGallery() {
  cameraRef.value?.openGallery()
}

async function submitCapturedSelfie() {
  if (!capturedBlob.value) return
  await submitSelfie(capturedBlob.value)
}

watch(
  () => props.open,
  (open) => {
    if (open) void prewarmCamera()
  }
)

watch(
  () => [props.open, props.task?.id] as const,
  ([open, taskId]) => {
    if (!open || !taskId || !props.task) return
    error.value = ''
    processing.value = false
    capturedBlob.value = null
    capturedUrl.value = null
    inputMode.value = props.startMode ?? 'choose'
    partnerName.value = ''
    signPadRef.value?.clear()
    flowStore.reset()

    if (props.task.status === 'completed') {
      step.value = 'complete'
      return
    }
    if (!canSubmit.value) {
      const s = eventStore.event?.status
      error.value =
        s === 'ended'
          ? 'This event has been finished by the admin.'
          : 'This event is not open yet. Ask the host to go live.'
      step.value = 'error'
      return
    }

    step.value = 'camera'

    void flowStore.fetchState(taskId).then((remote) => {
      if (remote.status === 'completed') {
        step.value = 'complete'
      }
    }).catch((e) => {
      error.value = getErrorMessage(e)
      step.value = 'error'
    })
  }
)

function close() {
  if (processing.value) return
  if (capturedUrl.value) {
    URL.revokeObjectURL(capturedUrl.value)
  }
  capturedBlob.value = null
  capturedUrl.value = null
  inputMode.value = 'choose'
  partnerName.value = ''
  signPadRef.value?.clear()
  flowStore.reset()
  emit('close')
}

function choosePhoto() {
  error.value = ''
  inputMode.value = 'photo'
}

function chooseName() {
  error.value = ''
  inputMode.value = 'name'
}

async function submitName() {
  if (!props.task || !canSubmitName.value) return
  if (props.task.id < 0) {
    error.value = 'Challenges are still syncing. Close this dialog, wait a moment, and tap the item again.'
    step.value = 'error'
    return
  }
  step.value = 'uploading'
  processing.value = true
  error.value = ''
  try {
    const result = await flowStore.completeTask(props.task.id, {
      partner_name: partnerName.value.trim(),
      partner_sign: signPadRef.value?.toDataURL() || undefined,
    })
    if (showTaskPoints.value && result.points_awarded > 0) {
      lastPoints.value = {
        total: result.points_awarded,
        speed: result.speed_bonus ?? 0,
      }
    } else {
      lastPoints.value = null
    }
    showLeaderboardPrompt.value = Boolean(
      result.all_tasks_completed || result.leaderboard_unlocked
    )
    step.value = 'complete'
    emit('completed', {
      taskId: props.task.id,
      imageUrl: '',
      thumbnailUrl: null,
    })
    if (!showLeaderboardPrompt.value) {
      window.setTimeout(() => close(), 1400)
    }
  } catch (e) {
    const msg = getErrorMessage(e)
    if (
      (msg.toLowerCase().includes('event') && msg.toLowerCase().includes('ended')) ||
      msg.toLowerCase().includes('finished') ||
      (e as { response?: { data?: { detail?: { code?: string } } } })?.response?.data?.detail
        ?.code === 'EVENT_ENDED'
    ) {
      error.value = 'This event has been finished by the admin.'
      step.value = 'error'
    } else {
      error.value = msg
      step.value = 'camera'
      inputMode.value = 'name'
    }
  } finally {
    processing.value = false
  }
}

async function submitSelfie(blob: Blob) {
  if (!props.task) return
  if (props.task.id < 0) {
    error.value = 'Challenges are still syncing. Close this dialog, wait a moment, and tap the item again.'
    step.value = 'error'
    return
  }
  step.value = 'uploading'
  processing.value = true
  error.value = ''
  try {
    const uploadInfo = await flowStore.uploadSelfie(props.task.id, blob)
    const result = await flowStore.completeTask(props.task.id, {
      selfie_id: uploadInfo.selfie_id,
    })
    if (showTaskPoints.value && result.points_awarded > 0) {
      lastPoints.value = {
        total: result.points_awarded,
        speed: result.speed_bonus ?? 0,
      }
    } else {
      lastPoints.value = null
    }
    showLeaderboardPrompt.value = Boolean(
      result.all_tasks_completed || result.leaderboard_unlocked
    )
    step.value = 'complete'
    emit('completed', {
      taskId: props.task.id,
      imageUrl: uploadInfo.image_url,
      thumbnailUrl: uploadInfo.thumbnail_url,
    })
    if (!showLeaderboardPrompt.value) {
      window.setTimeout(() => close(), 1400)
    }
  } catch (e) {
    const msg = getErrorMessage(e)
    // Treat any event-ended signal as a clear user-facing message
    if (
      msg.toLowerCase().includes('event') && msg.toLowerCase().includes('ended') ||
      msg.toLowerCase().includes('finished') ||
      (e as any)?.response?.data?.detail?.code === 'EVENT_ENDED'
    ) {
      error.value = 'This event has been finished by the admin.'
      step.value = 'error'
    } else {
      error.value = msg
      step.value = 'camera'
    }
    capturedBlob.value = null
    capturedUrl.value = null
  } finally {
    processing.value = false
  }
}

function onKeydown(ev: KeyboardEvent) {
  if (ev.key === 'Escape' && !processing.value) close()
}

// Solid color definitions matching the main grid
const colors = [
  { bg: '#0d9488', border: '#14b8a6' },
  { bg: '#2563eb', border: '#3b82f6' },
  { bg: '#db2777', border: '#ec4899' },
  { bg: '#7c3aed', border: '#8b5cf6' },
  { bg: '#ea580c', border: '#f97316' },
  { bg: '#16a34a', border: '#22c55e' }
]

function getTaskColor(title: string) {
  let hash = 0
  for (let i = 0; i < title.length; i++) {
    hash = title.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
}
</script>

<template>
  <Teleport to="body">
    <Transition name="tt-modal">
      <div
        v-if="open && task"
        class="custom-modal-backdrop fixed inset-0 z-[60] flex items-center justify-center p-4"
        role="presentation"
        @click.self="close"
        @keydown="onKeydown"
      >
        <!-- Modal Card -->
        <div
          class="custom-modal-card w-full max-h-[96dvh] overflow-y-auto rounded-3xl"
          :class="cardMaxClass"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="'bingo-modal-title-' + task.id"
        >
          <!-- Centered Logo -->
          <div class="logo-container">
            <div class="ticktalk-logo" aria-label="TickTalk">
              <span class="logo-bubbles" aria-hidden="true">
                <span class="logo-bubble logo-bubble--main">
                  <span class="logo-dots"><i /><i /><i /></span>
                </span>
                <span class="logo-bubble logo-bubble--back" />
              </span>
              <span class="logo-wordmark">TickTalk</span>
            </div>
          </div>

          <!-- Step 1: Choose photo or name, then capture / form -->
          <div v-if="step === 'camera'" class="modal-content-container">
            <!-- Dynamic Color Task Card -->
            <div
              class="task-header-card"
              :style="{ backgroundColor: getTaskColor(task.title).bg }"
            >
              <div class="task-header-title">{{ task.title }}</div>
            </div>

            <!-- Error message if any -->
            <p v-if="error" class="error-banner px-3 py-2 text-sm text-center mb-3" role="alert">
              {{ error }}
            </p>

            <div v-if="inputMode === 'choose'" class="detail-body-container">
              <div
                v-if="showTaskPoints && (task.points || 100)"
                class="points-badge-row"
              >
                <span class="points-badge">{{ task.points || 100 }} marks</span>
              </div>
              <div class="prompt-text-block">
                <div class="prompt-emblem">{{ cardEmblem }}</div>
                <p class="prompt-description">{{ taskPrompt }}</p>
              </div>
              <div class="action-buttons-grid">
                <button type="button" class="btn-back" @click="close">
                  Close
                </button>
                <button type="button" class="btn-submit" @click="choosePhoto">
                  Take selfie
                </button>
                <button type="button" class="btn-gallery choose-btn-full" @click="chooseName">
                  Name &amp; sign
                </button>
              </div>
            </div>

            <template v-else-if="inputMode === 'name'">
              <label class="name-label" for="bingo-partner-name">Their name</label>
              <input
                id="bingo-partner-name"
                v-model="partnerName"
                type="text"
                class="name-input"
                maxlength="120"
                autocomplete="name"
                placeholder="Who did you meet?"
              />
              <label class="name-label" for="bingo-partner-sign">
                Sign <span class="name-optional">(optional)</span>
              </label>
              <SignaturePad id="bingo-partner-sign" ref="signPadRef" />
              <div class="action-buttons-grid">
                <button type="button" class="btn-back" :disabled="processing" @click="handleGoBack">
                  Go Back
                </button>
                <button
                  type="button"
                  class="btn-submit"
                  :disabled="!canSubmitName"
                  @click="submitName"
                >
                  Submit
                </button>
              </div>
            </template>

            <template v-else>
              <!-- Live Camera (if no capture blob) -->
              <div v-if="!capturedBlob" class="camera-wrapper">
                <SelfieCamera
                  ref="cameraRef"
                  @capture="onSelfieCapture"
                  @error="(m) => { error = m }"
                />
              </div>

              <!-- Captured Image Preview -->
              <div v-else class="preview-wrapper">
                <img
                  :src="capturedUrl!"
                  alt="Captured selfie preview"
                  class="captured-preview-img"
                />
                <div class="preview-overlay"></div>
              </div>

              <!-- Action Buttons Grid -->
              <div class="action-buttons-grid">
                <button
                  type="button"
                  class="btn-back"
                  :disabled="processing"
                  @click="handleGoBack"
                >
                  Go Back
                </button>

                <button
                  v-if="capturedBlob"
                  type="button"
                  class="btn-submit"
                  :disabled="processing"
                  @click="submitCapturedSelfie"
                >
                  Submit
                </button>
                <button
                  v-else
                  type="button"
                  class="btn-gallery"
                  :disabled="processing"
                  @click="triggerGallery"
                >
                  Gallery
                </button>
              </div>
            </template>
          </div>

          <!-- Step 2: Uploading state -->
          <div
            v-else-if="step === 'uploading'"
            class="flex flex-col items-center justify-center gap-3 py-16 text-center"
          >
            <div class="spinner h-10 w-10 animate-spin rounded-full border-4" />
            <p class="text-base font-bold text-slate-800">Uploading & completing…</p>
          </div>

          <!-- Step 3: Complete state -->
          <div
            v-else-if="step === 'complete'"
            class="flex flex-col items-center justify-center gap-4 py-12 text-center px-4"
          >
            <span
              class="success-checkmark flex h-16 w-16 items-center justify-center rounded-full text-3xl font-black text-white shadow-lg animate-bounce"
              aria-hidden="true"
            >
              ✓
            </span>
            <h3 class="text-2xl font-black text-slate-900">Challenge complete!</h3>
            <p v-if="lastPoints" class="font-extrabold text-emerald-600 text-lg">
              +{{ lastPoints.total }} / 100 marks
              <span v-if="lastPoints.speed > 0" class="text-sm font-normal text-slate-500">
                ({{ lastPoints.speed }} speed)
              </span>
            </p>
            <p v-else class="text-sm text-slate-500">Your list is updated with a checkmark.</p>

            <div v-if="showLeaderboardPrompt" class="w-full mt-4 space-y-2">
              <p class="text-sm font-semibold text-slate-600">You finished all challenges! See how you rank.</p>
              <button
                type="button"
                class="btn-submit w-full py-3"
                @click="router.push({ name: 'leaderboard' }); close()"
              >
                View leaderboard
              </button>
              <button type="button" class="btn-back w-full py-3" @click="close">
                Back to challenges
              </button>
            </div>
          </div>

          <!-- Step 4: Error state -->
          <div v-else-if="step === 'error'" class="flex flex-col items-center justify-center gap-4 py-12 text-center px-6">
            <p class="error-banner px-4 py-3 text-sm" role="alert">
              {{ error || 'An error occurred during submission.' }}
            </p>
            <button type="button" class="btn-back w-full" @click="close">Close</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.custom-modal-backdrop {
  background-color: rgba(241, 245, 249, 0.95);
  backdrop-filter: blur(8px);
}

.custom-modal-card {
  background-color: #f8fafc;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.08);
  padding: 1.5rem;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

/* --- Centered Logo --- */
.logo-container {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 1.25rem;
}
.ticktalk-logo {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
}
.logo-bubbles {
  position: relative;
  width: 2.5rem;
  height: 2.1rem;
}
.logo-bubble {
  position: absolute;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}
.logo-bubble--back {
  left: 0;
  bottom: 0;
  width: 1.35rem;
  height: 1.2rem;
  border-radius: 0.5rem 0.5rem 0.5rem 0.12rem;
  background-color: #2ec4b6;
}
.logo-bubble--main {
  right: 0;
  top: 0;
  width: 1.68rem;
  height: 1.45rem;
  border-radius: 0.55rem 0.55rem 0.55rem 0.12rem;
  background-color: #ff5252;
  display: flex;
  align-items: center;
  justify-content: center;
}
.logo-dots {
  display: flex;
  gap: 0.15rem;
}
.logo-dots i {
  display: block;
  width: 0.2rem;
  height: 0.2rem;
  border-radius: 50%;
  background-color: #ffffff;
}
.logo-wordmark {
  font-size: 1.75rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #1e293b;
}

/* --- Task Header Card --- */
.task-header-card {
  width: 100%;
  border-radius: 1.25rem;
  padding: 1.25rem;
  text-align: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
  margin-bottom: 1.25rem;
  min-height: 4.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
.task-header-title {
  color: #ffffff !important;
  font-size: 1.05rem;
  font-weight: 800;
  line-height: 1.4;
}

.detail-body-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  gap: 1.25rem;
}
.points-badge-row {
  display: flex;
  justify-content: center;
  width: 100%;
}
.points-badge {
  display: inline-flex;
  padding: 0.35rem 1rem;
  border-radius: 9999px;
  background-color: #f1f5f9;
  border: 1.5px solid #cbd5e1;
  font-size: 0.875rem;
  font-weight: 800;
  color: #475569;
}
.prompt-text-block {
  width: 100%;
  background-color: #ffffff;
  border-radius: 1.25rem;
  padding: 1.5rem;
  text-align: center;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}
.prompt-emblem {
  font-size: 2.5rem;
  line-height: 1;
}
.prompt-description {
  font-size: 1rem;
  font-weight: 600;
  color: #334155;
  line-height: 1.5;
}

.choose-btn-full {
  grid-column: 1 / -1;
}
.name-label {
  display: block;
  margin-bottom: 0.4rem;
  font-size: 0.8rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #475569;
}
.name-optional {
  font-weight: 600;
  text-transform: none;
  color: #94a3b8;
}
.name-input {
  width: 100%;
  margin-bottom: 1rem;
  border-radius: 1rem;
  border: 2px solid #e2e8f0;
  background: #ffffff;
  padding: 0.9rem 1rem;
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
  box-sizing: border-box;
}
.name-input:focus {
  outline: none;
  border-color: #14b8a6;
}

/* --- Camera & Preview wrappers --- */
.camera-wrapper, .preview-wrapper {
  width: 100%;
  margin-bottom: 1.5rem;
}
.preview-wrapper {
  position: relative;
  aspect-ratio: 3 / 4;
  width: 100%;
  overflow: hidden;
  border-radius: 1.5rem;
  border: 4px solid #ffffff;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
}
.captured-preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.preview-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.12), transparent);
  pointer-events: none;
}

/* --- Action Buttons --- */
.action-buttons-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  width: 100%;
}
.btn-back, .btn-submit, .btn-gallery {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 3.25rem;
  border-radius: 1rem;
  font-size: 1rem;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
}
.btn-back {
  background-color: #ffffff;
  border: 2px solid #ffeb3b;
  color: #1a1a1a !important;
}
.btn-back:active {
  transform: scale(0.98);
  background-color: #f8fafc;
}
.btn-submit {
  background-color: #ffeb3b;
  border: none;
  color: #1a1a1a !important;
  box-shadow: 0 6px 18px rgba(255, 235, 59, 0.25);
}
.btn-submit:active {
  transform: scale(0.98);
  background-color: #fff176;
}
.btn-gallery {
  background-color: #ffffff;
  border: 2px solid #e2e8f0;
  color: #475569 !important;
}
.btn-gallery:active {
  transform: scale(0.98);
  background-color: #f1f5f9;
}

/* --- Complete & Success --- */
.success-checkmark {
  background: linear-gradient(135deg, #10b981, #059669);
  box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3);
}
.spinner {
  border-color: #e2e8f0;
  border-top-color: #ffeb3b;
}
.error-banner {
  background-color: #fee2e2;
  color: #ef4444;
  border-radius: 0.75rem;
  width: 100%;
  box-sizing: border-box;
}
</style>
