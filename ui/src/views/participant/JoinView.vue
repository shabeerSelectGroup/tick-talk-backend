<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { setSessionToken } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useEventStore } from '@/stores/event'
import { useJoinStore } from '@/stores/join'
import { getErrorMessage } from '@/utils/errors'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const eventStore = useEventStore()
const joinStore = useJoinStore()

const eventCode = ref('')
const displayName = ref('')
const submitting = ref(false)
const error = ref('')
const previewLoading = ref(false)
const step = ref<'splash' | 'form'>('splash')
const codeInputRef = ref<HTMLInputElement | null>(null)

type RoomState = 'idle' | 'loading' | 'open' | 'closed'
const roomState = ref<RoomState>('idle')

const preview = computed(() => joinStore.preview)
const normalizedCode = computed(() => eventCode.value.trim().toUpperCase())
const canSubmit = computed(
  () =>
    roomState.value === 'open' &&
    normalizedCode.value.length > 0 &&
    displayName.value.trim().length >= 2 &&
    !submitting.value &&
    !previewLoading.value
)

let previewTimer: ReturnType<typeof setTimeout> | null = null
let previewRequest = 0

async function loadPreview(code: string) {
  if (!code) {
    roomState.value = 'idle'
    joinStore.preview = null
    return
  }

  const requestId = ++previewRequest
  previewLoading.value = true
  error.value = ''
  roomState.value = 'loading'

  try {
    await Promise.race([
      joinStore.fetchPreview(code),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Could not load event. Is the backend running?')), 8000)
      ),
    ])
    if (requestId !== previewRequest) return

    roomState.value = preview.value?.can_join ? 'open' : 'closed'
  } catch (e) {
    if (requestId !== previewRequest) return
    error.value = getErrorMessage(e)
    roomState.value = 'closed'
  } finally {
    if (requestId === previewRequest) {
      previewLoading.value = false
    }
  }
}

function schedulePreviewLoad(code: string) {
  if (previewTimer) clearTimeout(previewTimer)
  if (!code.trim()) {
    previewRequest++
    previewLoading.value = false
    roomState.value = 'idle'
    joinStore.preview = null
    error.value = ''
    return
  }
  previewTimer = setTimeout(() => {
    void loadPreview(code.trim().toUpperCase())
  }, 400)
}

async function openForm(focusCode = false) {
  step.value = 'form'
  if (focusCode) {
    await nextTick()
    codeInputRef.value?.focus()
  }
}

onMounted(async () => {
  if ('serviceWorker' in navigator) {
    const regs = await navigator.serviceWorker.getRegistrations()
    await Promise.all(regs.map((r) => r.unregister()))
  }

  auth.clearSession()
  eventStore.$reset()
  setSessionToken(null)

  const fromRoute = (route.params.eventCode as string | undefined)?.trim()
  eventCode.value = (fromRoute || '').toUpperCase()
  if (normalizedCode.value) {
    step.value = 'form'
    await loadPreview(normalizedCode.value)
  }
})

watch(eventCode, (value) => {
  schedulePreviewLoad(value)
})

function applyJoinResult(result: import('@/types/join').JoinResult) {
  const p = preview.value
  const event =
    result.event ??
    (p
      ? {
          id: result.event_id,
          code: p.code,
          name: p.name,
          description: p.description,
          mode: p.mode,
          status: p.status,
          starts_at: null,
          ends_at: null,
          capabilities: p.capabilities ?? undefined,
          public_wall_url: p.public_wall_url ?? undefined,
        }
      : null)
  if (!event) {
    throw new Error('Could not load event details. Refresh and try again.')
  }
  eventStore.applySessionPayload({
    participant: result.participant,
    event,
    capabilities: result.capabilities ?? p?.capabilities ?? undefined,
  })
}

async function submit() {
  if (!normalizedCode.value) {
    error.value = 'Enter the event code for your room'
    step.value = 'form'
    return
  }
  if (displayName.value.trim().length < 2) {
    error.value = 'Please enter your name (at least 2 characters)'
    step.value = 'form'
    return
  }
  if (roomState.value !== 'open') {
    error.value = preview.value?.message || 'This event is not open for joining right now'
    step.value = 'form'
    return
  }
  if (submitting.value) return

  submitting.value = true
  error.value = ''

  try {
    auth.clearSession()
    setSessionToken(null)
    eventStore.$reset()

    const result = await joinStore.join(normalizedCode.value, {
      display_name: displayName.value.trim(),
    })
    auth.setSession(result.session_token, result.event_code, result.participant_id)
    setSessionToken(result.session_token)
    applyJoinResult(result)
    await router.replace({ name: 'tasks' })
  } catch (e) {
    error.value = getErrorMessage(e)
    step.value = 'form'
  } finally {
    submitting.value = false
  }
}

async function onGetStarted() {
  if (canSubmit.value) {
    await submit()
    return
  }
  if (normalizedCode.value && roomState.value === 'open' && displayName.value.trim().length >= 2) {
    await submit()
    return
  }
  await openForm(true)
}
</script>

<template>
  <div class="join-splash">
    <!-- Decorative shapes -->
    <div class="join-splash__decor" aria-hidden="true">
      <span class="join-splash__shape join-splash__shape--circle" />
      <span class="join-splash__shape join-splash__shape--square" />
      <span class="join-splash__shape join-splash__shape--triangle" />
      <span class="join-splash__shape join-splash__shape--squiggle" />
      <span class="join-splash__shape join-splash__shape--arc" />
    </div>

    <!-- Logo -->
    <header class="join-splash__header tt-animate-fade-in">
      <div class="join-splash__logo" aria-label="TickTalk">
        <span class="join-splash__bubbles" aria-hidden="true">
          <span class="join-splash__bubble join-splash__bubble--main">
            <span class="join-splash__dots"><i /><i /><i /></span>
          </span>
          <span class="join-splash__bubble join-splash__bubble--back" />
        </span>
        <span class="join-splash__wordmark">TickTalk</span>
      </div>
    </header>

    <!-- Hero -->
    <div class="join-splash__hero tt-animate-fade-in-up">
      <img
        src="/hero-character.png"
        alt=""
        class="join-splash__character"
        width="284"
        height="877"
        fetchpriority="high"
      />
    </div>

    <!-- Splash actions (visible when form closed) -->
    <div v-if="step === 'splash'" class="join-splash__actions tt-animate-fade-in-up tt-animate-delay-2">
      <button type="button" class="join-splash__cta" @click="onGetStarted">
        Get Started
      </button>
      <button type="button" class="join-splash__select" aria-label="Select event" @click="openForm(true)">
        <img
          src="/select-logo.png"
          alt="Select"
          class="join-splash__select-logo"
          width="769"
          height="324"
        />
      </button>
    </div>

    <!-- Join form sheet -->
    <Teleport to="body">
      <Transition name="join-backdrop">
        <button
          v-if="step === 'form'"
          type="button"
          class="join-sheet-backdrop"
          aria-label="Close"
          @click="step = 'splash'"
        />
      </Transition>
      <Transition name="join-sheet">
        <form
          v-if="step === 'form'"
          class="join-sheet"
          novalidate
          @submit.prevent="submit"
        >
          <button type="button" class="join-sheet__back" aria-label="Back" @click="step = 'splash'">
            ←
          </button>

          <h2 class="join-sheet__title">Join your event</h2>

          <label for="event-code" class="join-sheet__label">Event code</label>
          <input
            id="event-code"
            ref="codeInputRef"
            v-model="eventCode"
            type="text"
            autocomplete="off"
            autocapitalize="characters"
            class="join-sheet__input uppercase"
            placeholder="e.g. DEMO2026"
          />
          <p v-if="previewLoading" class="join-sheet__hint">Checking room…</p>

          <div v-if="preview && (roomState === 'open' || roomState === 'closed')" class="join-sheet__room">
            <p class="join-sheet__room-label">Join game room</p>
            <p class="join-sheet__room-name">{{ preview.name }}</p>
            <p class="join-sheet__room-code">{{ preview.code }}</p>
          </div>

          <p v-if="roomState === 'closed'" class="join-sheet__error" role="alert">
            {{ preview?.message || error || 'This event is unavailable.' }}
          </p>

          <label for="name" class="join-sheet__label">Your name</label>
          <input
            id="name"
            v-model="displayName"
            type="text"
            autocomplete="name"
            class="join-sheet__input"
            placeholder="Your full name"
            required
          />

          <p v-if="error && roomState !== 'closed'" class="join-sheet__error" role="alert">
            {{ error }}
          </p>

          <button type="submit" class="join-splash__cta join-sheet__submit" :disabled="!canSubmit">
            {{ submitting ? 'Joining…' : 'Get Started' }}
          </button>
        </form>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.join-splash {
  position: relative;
  display: flex;
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: 100svh;
  min-height: 100dvh;
  flex-direction: column;
  overflow: hidden;
  background-color: #ff4757;
  padding:
    max(0.75rem, env(safe-area-inset-top))
    max(1rem, env(safe-area-inset-left))
    max(1rem, env(safe-area-inset-bottom))
    max(1rem, env(safe-area-inset-right));
  font-family: 'Nunito', system-ui, -apple-system, sans-serif;
}

.join-splash__decor {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.join-splash__shape {
  position: absolute;
  opacity: 0.45;
  background: rgba(255, 255, 255, 0.35);
}

.join-splash__shape--circle {
  top: 11%;
  left: 8%;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 50%;
}

.join-splash__shape--square {
  top: 38%;
  left: 6%;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 0.2rem;
  transform: rotate(12deg);
}

.join-splash__shape--triangle {
  top: 22%;
  right: 10%;
  width: 0;
  height: 0;
  background: transparent;
  border-left: 0.65rem solid transparent;
  border-right: 0.65rem solid transparent;
  border-bottom: 1.1rem solid rgba(255, 255, 255, 0.35);
}

.join-splash__shape--squiggle {
  bottom: 28%;
  left: 10%;
  width: 2rem;
  height: 0.35rem;
  border-radius: 999px;
  transform: rotate(-25deg);
}

.join-splash__shape--arc {
  bottom: 18%;
  right: 8%;
  width: 1.5rem;
  height: 1.5rem;
  border: 3px solid rgba(255, 255, 255, 0.35);
  border-color: transparent rgba(255, 255, 255, 0.35) rgba(255, 255, 255, 0.35) transparent;
  border-radius: 50%;
  background: transparent;
  transform: rotate(40deg);
}

.join-splash__header {
  position: relative;
  z-index: 2;
  padding-top: 2.5rem; /* Increased to move the logo down slightly */
  text-align: center;
}

.join-splash__logo {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
}

.join-splash__bubbles {
  position: relative;
  width: 2.75rem;
  height: 2.25rem;
}

.join-splash__bubble {
  position: absolute;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.join-splash__bubble--back {
  left: 0;
  bottom: 0;
  width: 1.5rem;
  height: 1.35rem;
  border-radius: 0.55rem 0.55rem 0.55rem 0.15rem;
  opacity: 0.92;
}

.join-splash__bubble--main {
  right: 0;
  top: 0;
  width: 1.85rem;
  height: 1.55rem;
  border-radius: 0.6rem 0.6rem 0.6rem 0.15rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.join-splash__dots {
  display: flex;
  gap: 0.15rem;
}

.join-splash__dots i {
  display: block;
  width: 0.22rem;
  height: 0.22rem;
  border-radius: 50%;
  background: #ff6b6b;
  font-style: normal;
}

.join-splash__wordmark {
  font-size: 1.65rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #fff;
}

.join-splash__hero {
  position: relative;
  z-index: 1;
  flex: 1 1 auto;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  min-height: 0;
  padding: 0.25rem 0 3rem; /* Increased bottom padding to move image up */
}

.join-splash__character {
  width: auto;
  height: auto;
  max-width: min(85vw, 18rem);
  max-height: min(62svh, 30rem);
  object-fit: contain;
  object-position: center bottom;
  filter: drop-shadow(0 16px 28px rgba(0, 0, 0, 0.15));
  transform: translateY(0); /* Moved down normally */
}

.join-splash__actions {
  position: relative;
  z-index: 2;
  flex-shrink: 0;
  margin-top: auto;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 1rem;
  width: 100%;
  padding-top: 0.75rem;
  padding-bottom: 2rem;
}

.join-splash__cta {
  width: 100%;
  min-height: 3.25rem;
  border: none;
  border-radius: 1rem;
  background: #ffeb3b;
  color: #1a1a1a;
  font-size: 1.125rem;
  font-weight: 800;
  letter-spacing: -0.01em;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.18);
  transition: transform 0.15s ease, background 0.15s ease;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.join-splash__cta:active:not(:disabled) {
  transform: scale(0.98);
  background: #fff176;
}

.join-splash__cta:disabled {
  opacity: 0.55;
}

.join-splash__select {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 2.75rem;
  padding: 0.25rem 0;
  border: none;
  background: transparent;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.join-splash__select:active {
  opacity: 0.85;
  transform: scale(0.98);
}

.join-splash__select-logo {
  display: block;
  width: auto;
  height: 2.75rem;
  max-width: min(80vw, 14rem);
  object-fit: contain;
}

/* Bottom sheet form — matches 430px mobile app column */
.join-sheet {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 50;
  width: 100%;
  max-width: 430px;
  margin-left: auto;
  margin-right: auto;
  max-height: min(88dvh, 560px);
  overflow-y: auto;
  overscroll-behavior: contain;
  box-sizing: border-box;
  padding:
    0.75rem max(1rem, env(safe-area-inset-left))
    max(1.25rem, env(safe-area-inset-bottom))
    max(1rem, env(safe-area-inset-right));
  border-radius: 1.25rem 1.25rem 0 0;
  background: rgba(255, 255, 255, 0.98);
  color: #2d3436;
  box-shadow: 0 -8px 40px rgba(0, 0, 0, 0.15);
}

.join-sheet::before {
  content: '';
  display: block;
  width: 2.5rem;
  height: 0.25rem;
  margin: 0 auto 1rem;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.12);
}

.join-sheet__back {
  border: none;
  background: transparent;
  color: #636e72;
  font-size: 1.25rem;
  line-height: 1;
  padding: 0.25rem 0;
  margin-bottom: 0.5rem;
}

.join-sheet__title {
  font-size: 1.25rem;
  font-weight: 800;
  color: #2d3436;
  margin-bottom: 1rem;
}

.join-sheet__label {
  display: block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #636e72;
  margin-bottom: 0.35rem;
}

.join-sheet__input {
  width: 100%;
  min-height: 3rem;
  margin-bottom: 0.85rem;
  padding: 0 0.875rem;
  border: 2px solid rgba(255, 71, 87, 0.2);
  border-radius: 0.75rem;
  background: #fff;
  font-size: 16px;
  color: #2d3436;
}

.join-sheet__input:focus {
  outline: none;
  border-color: #ff4757;
  box-shadow: 0 0 0 3px rgba(255, 71, 87, 0.2);
}

.join-sheet__hint {
  margin: -0.5rem 0 0.75rem;
  font-size: 0.8125rem;
  color: #636e72;
}

.join-sheet__room {
  margin-bottom: 0.85rem;
  padding: 0.75rem;
  border-radius: 0.75rem;
  background: rgba(255, 107, 107, 0.08);
  text-align: center;
}

.join-sheet__room-label {
  font-size: 0.6875rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #ff4757;
}

.join-sheet__room-name {
  margin-top: 0.25rem;
  font-size: 1.125rem;
  font-weight: 800;
  color: #2d3436;
}

.join-sheet__room-code {
  margin-top: 0.15rem;
  font-family: ui-monospace, monospace;
  font-size: 0.875rem;
  color: #636e72;
}

.join-sheet__error {
  margin-bottom: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  background: #ffeaea;
  color: #c0392b;
  font-size: 0.875rem;
}

.join-sheet__submit {
  margin-top: 0.5rem;
  width: 100%;
}

.join-sheet-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  border: none;
  background: rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(2px);
}

.join-backdrop-enter-active,
.join-backdrop-leave-active {
  transition: opacity 0.3s ease;
}

.join-backdrop-enter-from,
.join-backdrop-leave-to {
  opacity: 0;
}

.join-sheet-enter-active {
  transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}

.join-sheet-leave-active {
  transition: transform 0.25s ease;
}

.join-sheet-enter-from,
.join-sheet-leave-to {
  transform: translateY(100%);
}
</style>
