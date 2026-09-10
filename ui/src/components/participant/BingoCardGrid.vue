<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ParticipantTask } from '@/types'
import type { BingoCardSlot, BingoSection } from '@/utils/bingoTasks'
import { mergeShuffledBingoCards } from '@/utils/bingoTasks'
import { isTaskCompleted } from '@/utils/taskStatus'
import { selfieDisplayUrl } from '@/utils/selfieMedia'
import { prewarmCamera } from '@/utils/cameraPrewarm'
import SignaturePad from '@/components/participant/SignaturePad.vue'
import { useTaskFlowStore } from '@/stores/taskFlow'
import { useEventStore } from '@/stores/event'
import { getErrorMessage } from '@/utils/errors'

const props = defineProps<{
  sections: BingoSection[]
  completedCount: number
  totalCount: number
  canToggle: boolean
  showPoints?: boolean
  showLeaderboard?: boolean
  profileOpen?: boolean
}>()

const emit = defineEmits<{
  select: [task: ParticipantTask, mode: 'photo' | 'name', emblem?: string]
  completed: [
    payload: {
      taskId: number
      imageUrl: string
      thumbnailUrl: string | null
    },
  ]
  'nav-rank': []
  'nav-you': []
}>()

const cardSlots = ref<BingoCardSlot[]>([])
const expandedSlot = ref<BingoCardSlot | null>(null)
const detailView = ref<'prompt' | 'name'>('prompt')
const partnerName = ref('')
const signPadRef = ref<InstanceType<typeof SignaturePad> | null>(null)
const nameError = ref('')
const nameSubmitting = ref(false)
const flowStore = useTaskFlowStore()
const eventStore = useEventStore()

const canSubmitName = computed(
  () => partnerName.value.trim().length >= 2 && !nameSubmitting.value
)

watch(
  () => props.sections,
  (sections) => {
    cardSlots.value = mergeShuffledBingoCards(cardSlots.value, sections)
    if (expandedSlot.value) {
      const updated = cardSlots.value.find((s) => s.key === expandedSlot.value!.key)
      expandedSlot.value = updated ?? null
    }
  },
  { immediate: true, deep: true }
)

function taskPrompt(task: ParticipantTask): string {
  if (task.description?.trim()) return task.description.trim()
  return `Find someone who matches “${task.title}”, then take a selfie together.`
}

function taskSelfieUrl(task: ParticipantTask): string {
  return selfieDisplayUrl(task)
}

function isExpanded(slot: BingoCardSlot): boolean {
  return expandedSlot.value?.key === slot.key
}

function onCellClick(slot: BingoCardSlot) {
  const { task } = slot
  const done = isTaskCompleted(task.status)
  const locked = !props.canToggle || task.id < 0

  if (done) {
    detailView.value = 'prompt'
    expandedSlot.value = slot
    return
  }
  if (locked) return

  void prewarmCamera()
  detailView.value = 'prompt'
  partnerName.value = ''
  nameError.value = ''
  expandedSlot.value = slot
}

function closeDetail() {
  expandedSlot.value = null
  detailView.value = 'prompt'
  partnerName.value = ''
  nameError.value = ''
  signPadRef.value?.clear()
}

function openNameSign() {
  if (!expandedSlot.value) return
  const task = expandedSlot.value.task
  if (isTaskCompleted(task.status) || !props.canToggle || task.id < 0) return
  nameError.value = ''
  partnerName.value = ''
  detailView.value = 'name'
}

function backToPrompt() {
  detailView.value = 'prompt'
  partnerName.value = ''
  nameError.value = ''
  signPadRef.value?.clear()
}

async function submitNameSign() {
  const slot = expandedSlot.value
  if (!slot || !canSubmitName.value) return
  const task = slot.task
  if (task.id < 0) {
    nameError.value = 'Challenges are still syncing. Close and try again.'
    return
  }
  nameSubmitting.value = true
  nameError.value = ''
  try {
    await flowStore.completeTask(task.id, {
      partner_name: partnerName.value.trim(),
      partner_sign: signPadRef.value?.toDataURL() || undefined,
    })
    emit('completed', {
      taskId: task.id,
      imageUrl: '',
      thumbnailUrl: null,
    })
    await eventStore.fetchMe()
    closeDetail()
  } catch (e) {
    nameError.value = getErrorMessage(e)
  } finally {
    nameSubmitting.value = false
  }
}

function startSelfie(mode: 'photo' | 'name' = 'photo') {
  if (!expandedSlot.value) return
  const task = expandedSlot.value.task
  const emblem = expandedSlot.value.emblem
  if (isTaskCompleted(task.status) || !props.canToggle || task.id < 0) return
  if (mode === 'name') {
    openNameSign()
    return
  }
  closeDetail()
  emit('select', task, mode, emblem)
}

// Background color configurations for task cards
const colors = [
  { bg: '#0d9488', border: '#14b8a6' }, // Teal
  { bg: '#2563eb', border: '#3b82f6' }, // Blue
  { bg: '#db2777', border: '#ec4899' }, // Pink
  { bg: '#7c3aed', border: '#8b5cf6' }, // Purple
  { bg: '#ea580c', border: '#f97316' }, // Orange
  { bg: '#16a34a', border: '#22c55e' }  // Green
]

function getSlotColor(index: number) {
  return colors[index % colors.length]
}

function getExpandedSlotIndex(): number {
  if (!expandedSlot.value) return 0
  return cardSlots.value.findIndex((s) => s.key === expandedSlot.value!.key)
}
</script>

<template>
  <div class="bingo-board tt-animate-fade-in">
    <!-- Top bar: Rank | Logo | You -->
    <div class="bingo-topbar">
      <button
        type="button"
        class="bingo-topbar-btn"
        @click="emit('nav-rank')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5">
          <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path>
          <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path>
          <path d="M4 22h16"></path>
          <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"></path>
          <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"></path>
          <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"></path>
        </svg>
        <span>{{ showLeaderboard ? 'Rank' : 'Players' }}</span>
      </button>

      <!-- Centered Logo -->
      <div class="ticktalk-logo" aria-label="TickTalk">
        <span class="logo-bubbles" aria-hidden="true">
          <span class="logo-bubble logo-bubble--main">
            <span class="logo-dots"><i /><i /><i /></span>
          </span>
          <span class="logo-bubble logo-bubble--back" />
        </span>
        <span class="logo-wordmark">TickTalk</span>
      </div>

      <!-- You button -->
      <button
        type="button"
        class="bingo-topbar-btn"
        @click="emit('nav-you')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5">
          <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
        <span>You</span>
      </button>
    </div>

    <!-- Completion Banner -->
    <div class="completion-banner">
      <div class="completed-pill">
        <span class="emoji">🏆</span> Completed
      </div>
      <div class="progress-text">
        {{ completedCount }} of {{ totalCount }}
      </div>
      <div class="tasks-label">
        TASKS
      </div>
    </div>

    <!-- 2-Column Task Cards Deck -->
    <div class="bingo-board__deck">
      <div class="bingo-board__grid tt-stagger" role="list" aria-label="Bingo challenges">
        <button
          v-for="(slot, index) in cardSlots"
          :key="slot.key"
          type="button"
          role="listitem"
          class="task-card"
          :class="{ 'has-photo': taskSelfieUrl(slot.task) }"
          :style="taskSelfieUrl(slot.task)
            ? { border: `4px solid ${index % 2 === 0 ? '#a16207' : '#64748b'}` }
            : { backgroundColor: getSlotColor(index).bg, borderColor: '#ffffff' }"
          :disabled="slot.task.id < 0 || (!canToggle && !isTaskCompleted(slot.task.status))"
          :aria-expanded="isExpanded(slot)"
          :aria-label="`${slot.task.title}, tap to view`"
          @click="onCellClick(slot)"
        >
          <!-- Completed Selfie Background -->
          <template v-if="taskSelfieUrl(slot.task)">
            <img
              :src="taskSelfieUrl(slot.task)"
              :alt="`Selfie for ${slot.task.title}`"
              class="task-card-photo"
              loading="lazy"
              decoding="async"
            />
            <div class="task-card-overlay"></div>
            <div class="task-card-completed-text">
              {{ slot.task.title }}
            </div>
          </template>
          <!-- Task Text -->
          <template v-else>
            <div class="task-card-text">
              {{ slot.task.title }}
            </div>
          </template>
        </button>
      </div>
    </div>

    <!-- Modal (Teleport details view) -->
    <Teleport to="body">
      <Transition name="tt-modal">
        <div
          v-if="expandedSlot"
          class="custom-modal-backdrop fixed inset-0 z-[100] flex items-center justify-center p-4"
          role="presentation"
          @click.self="closeDetail"
        >
          <!-- Modal Card -->
          <div
            class="custom-modal-card w-full max-w-[320px] max-h-[96dvh] overflow-y-auto rounded-3xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="bingo-task-title"
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

            <!-- Dynamic Color Task Card -->
            <div
              class="task-header-card"
              :style="{ backgroundColor: getSlotColor(getExpandedSlotIndex()).bg }"
            >
              <div class="task-header-title">{{ expandedSlot.task.title }}</div>
            </div>

            <!-- Detail Modal Body -->
            <div class="detail-body-container">
              <!-- Name & sign form -->
              <div v-if="detailView === 'name'" class="name-form">
                <p v-if="nameError" class="name-error" role="alert">{{ nameError }}</p>
                <label class="name-label" for="bingo-grid-partner-name">Their name</label>
                <input
                  id="bingo-grid-partner-name"
                  v-model="partnerName"
                  type="text"
                  class="name-input"
                  maxlength="120"
                  autocomplete="name"
                  placeholder="Who did you meet?"
                />
                <label class="name-label">
                  Sign <span class="name-optional">(optional)</span>
                </label>
                <SignaturePad ref="signPadRef" />
                <div class="action-buttons-grid">
                  <button
                    type="button"
                    class="btn-back"
                    :disabled="nameSubmitting"
                    @click="backToPrompt"
                  >
                    Back
                  </button>
                  <button
                    type="button"
                    class="btn-submit"
                    :disabled="!canSubmitName"
                    @click="submitNameSign"
                  >
                    {{ nameSubmitting ? 'Saving…' : 'Submit' }}
                  </button>
                </div>
              </div>

              <template v-else>
              <!-- Points/Marks badge if not completed -->
              <div
                v-if="showPoints && (expandedSlot.task.points || 100) && !isTaskCompleted(expandedSlot.task.status)"
                class="points-badge-row"
              >
                <span class="points-badge">{{ expandedSlot.task.points || 100 }} marks</span>
              </div>

              <!-- Selfie display if completed -->
              <div v-if="taskSelfieUrl(expandedSlot.task)" class="completed-preview-wrapper">
                <img
                  :src="taskSelfieUrl(expandedSlot.task)"
                  :alt="`Selfie for ${expandedSlot.task.title}`"
                  class="completed-preview-img"
                />
                <div class="preview-overlay"></div>
                <div class="completed-tag">Completed ✓</div>
              </div>

              <!-- Prompt/Description block if not completed -->
              <div v-else class="prompt-text-block">
                <div class="prompt-emblem">{{ expandedSlot.emblem }}</div>
                <p class="prompt-description">
                  {{ taskPrompt(expandedSlot.task) }}
                </p>
              </div>

              <!-- Action Buttons -->
              <div
                class="action-buttons-grid"
                :class="{ 'single-button': isTaskCompleted(expandedSlot.task.status) || !canToggle || expandedSlot.task.id < 0 }"
              >
                <button
                  type="button"
                  class="btn-back"
                  @click="closeDetail"
                >
                  Close
                </button>
                <button
                  v-if="!isTaskCompleted(expandedSlot.task.status) && canToggle && expandedSlot.task.id >= 0"
                  type="button"
                  class="btn-submit"
                  @click="startSelfie('photo')"
                >
                  Take selfie
                </button>
                <button
                  v-if="!isTaskCompleted(expandedSlot.task.status) && canToggle && expandedSlot.task.id >= 0"
                  type="button"
                  class="btn-gallery choose-btn-full"
                  @click="openNameSign"
                >
                  Name &amp; sign
                </button>
              </div>
              </template>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.bingo-board {
  box-sizing: border-box;
  width: 100%;
  max-width: none;
  overflow: hidden;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}

/* --- Top Bar (Rank | Logo | You) --- */
.bingo-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.5rem 0.75rem;
  gap: 0.5rem;
}
.bingo-topbar-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  min-width: 3rem;
  min-height: 2.75rem;
  padding: 0.35rem 0.5rem;
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 0.65rem;
  font-weight: 700;
  cursor: pointer;
  border-radius: 0.75rem;
  transition: color 0.15s, background 0.15s;
}
.bingo-topbar-btn:hover {
  color: #0f172a;
  background: rgba(0, 0, 0, 0.04);
}
.bingo-topbar-spacer {
  min-width: 3rem;
}
.ticktalk-logo {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  flex: 1;
  justify-content: center;
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
  background-color: #2ec4b6; /* Teal back bubble */
}
.logo-bubble--main {
  right: 0;
  top: 0;
  width: 1.68rem;
  height: 1.45rem;
  border-radius: 0.55rem 0.55rem 0.55rem 0.12rem;
  background-color: #ff5252; /* Coral front bubble */
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
  font-style: normal;
}
.logo-wordmark {
  font-size: 1.75rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #1e293b;
}

/* --- Completion Banner --- */
.completion-banner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: #ffffff;
  border-radius: 1rem;
  padding: 1rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
  margin-bottom: 1rem;
}
.completed-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  background-color: #ffeef2;
  color: #ff3366;
  font-size: 0.8rem;
  font-weight: 800;
  padding: 0.35rem 1.25rem;
  border-radius: 9999px;
}
.progress-text {
  font-size: 1.75rem;
  font-weight: 900;
  color: #0f172a;
  margin-top: 0.5rem;
  line-height: 1;
}
.tasks-label {
  font-size: 0.65rem;
  font-weight: 800;
  color: #94a3b8;
  letter-spacing: 0.1em;
  margin-top: 0.25rem;
}

.bingo-board__deck {
  padding: 0;
  background: transparent !important;
}

.bingo-board__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: 1rem !important;
}

/* --- Task Cards --- */
.task-card {
  position: relative;
  aspect-ratio: 1 / 1;
  width: 100%;
  border-radius: 1.75rem; /* Matches smooth rounded card look */
  border: 4px solid #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.25rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.05);
  outline: none;
  overflow: hidden;
}

.task-card:hover {
  transform: translateY(-2px) scale(1.01);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.09);
}

.task-card:active {
  transform: scale(0.98);
}

.task-card-text {
  color: #ffffff !important;
  font-size: 0.95rem;
  font-weight: 800;
  line-height: 1.4;
  word-wrap: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.task-card-photo {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 1.5rem;
}

.task-card-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.6) 0%, rgba(0, 0, 0, 0) 50%);
  border-radius: 1.5rem;
  pointer-events: none;
}

.task-card-completed-text {
  position: absolute;
  bottom: 0.75rem;
  left: 0.5rem;
  right: 0.5rem;
  color: #ffffff;
  font-size: 0.85rem;
  font-weight: 800;
  line-height: 1.2;
  text-align: center;
  z-index: 10;
  text-shadow: 0 1px 4px rgba(0,0,0,0.8);
  word-wrap: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* --- Modal Styles --- */
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
  margin-top: 0.5rem;
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
  font-style: normal;
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

/* --- Detail Body Container --- */
.detail-body-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  gap: 1.25rem;
}

/* --- Points Badge --- */
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

/* --- Completed Selfie Display --- */
.completed-preview-wrapper {
  position: relative;
  aspect-ratio: 3 / 4;
  width: 100%;
  overflow: hidden;
  border-radius: 1.5rem;
  border: 4px solid #ffffff;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
}
.completed-preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.preview-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.12), transparent);
  pointer-events: none;
}
.completed-tag {
  position: absolute;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  background-color: #10b981;
  color: #ffffff;
  font-weight: 800;
  font-size: 0.9rem;
  padding: 0.45rem 1.25rem;
  border-radius: 9999px;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
  z-index: 10;
}

/* --- Prompt Text Block --- */
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

/* --- Action Buttons --- */
.action-buttons-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  width: 100%;
  margin-top: 0.5rem;
}
.btn-back, .btn-submit {
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

.action-buttons-grid.single-button {
  grid-template-columns: 1fr;
}
.choose-btn-full {
  grid-column: 1 / -1;
}
.btn-gallery {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 3.25rem;
  border-radius: 1rem;
  font-size: 1rem;
  font-weight: 800;
  cursor: pointer;
  width: 100%;
  background-color: #ffffff;
  border: 2px solid #e2e8f0;
  color: #475569 !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
}
.btn-gallery:active {
  transform: scale(0.98);
  background-color: #f1f5f9;
}

.name-form {
  width: 100%;
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
.name-error {
  margin: 0 0 0.75rem;
  padding: 0.65rem 0.85rem;
  border-radius: 0.75rem;
  background: #fee2e2;
  color: #ef4444;
  font-size: 0.85rem;
  font-weight: 700;
  text-align: center;
}
</style>
