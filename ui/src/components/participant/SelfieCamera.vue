<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import {
  cameraErrorMessage,
  isCameraSupported,
  queryCameraPermission,
} from '@/utils/camera'
import {
  CAMERA_PREVIEW_CONSTRAINTS,
  hasPrewarmedCamera,
  prewarmCamera,
  returnStreamToPrewarm,
  takePrewarmedStream,
} from '@/utils/cameraPrewarm'

const emit = defineEmits<{
  capture: [blob: Blob]
  error: [message: string]
  ready: []
}>()

type Phase = 'prompt' | 'requesting' | 'active' | 'blocked'

const videoRef = ref<HTMLVideoElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const previewUrl = ref<string | null>(null)
const stream = ref<MediaStream | null>(null)
const busy = ref(false)
const phase = ref<Phase>(hasPrewarmedCamera() ? 'active' : 'requesting')
const previewReady = ref(false)
const localError = ref('')
const permissionDenied = ref(false)

async function waitForVideoFrame(video: HTMLVideoElement, maxMs = 350): Promise<boolean> {
  if (video.videoWidth > 0 && video.videoHeight > 0) return true

  return new Promise((resolve) => {
    const started = performance.now()
    const tick = () => {
      if (video.videoWidth > 0 && video.videoHeight > 0) {
        resolve(true)
        return
      }
      if (performance.now() - started >= maxMs) {
        resolve(video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA)
        return
      }
      requestAnimationFrame(tick)
    }
    const onReady = () => {
      video.removeEventListener('loadeddata', onReady)
      resolve(true)
    }
    video.addEventListener('loadeddata', onReady, { once: true })
    requestAnimationFrame(tick)
  })
}

async function attachStreamToVideo(media: MediaStream, warm = false): Promise<boolean> {
  await nextTick()

  let video = videoRef.value
  if (!video) {
    await nextTick()
    video = videoRef.value
  }
  if (!video) return false

  video.srcObject = media
  video.muted = true
  video.playsInline = true
  video.setAttribute('playsinline', 'true')
  video.setAttribute('webkit-playsinline', 'true')

  await video.play().catch(() => undefined)
  const ready = await waitForVideoFrame(video, warm ? 150 : 400)
  previewReady.value = ready
  return ready
}

async function startCamera() {
  localError.value = ''

  if (!isCameraSupported()) {
    const msg =
      typeof window !== 'undefined' && !window.isSecureContext
        ? 'Camera needs https:// (or localhost). You can upload a photo below.'
        : 'Camera is not supported in this browser. Upload a photo below.'
    localError.value = msg
    phase.value = 'blocked'
    emit('error', msg)
    return false
  }

  const prewarmed = takePrewarmedStream()
  if (prewarmed) {
    stream.value = prewarmed
    phase.value = 'active'
    previewReady.value = false
    const attached = await attachStreamToVideo(prewarmed, true)
    if (!attached) {
      localError.value = 'Could not start camera preview. Tap Try again or upload a photo.'
      phase.value = 'blocked'
      emit('error', localError.value)
      return false
    }
    emit('ready')
    return true
  }

  if (stream.value) {
    stream.value.getTracks().forEach((t) => t.stop())
    stream.value = null
  }
  previewReady.value = false
  phase.value = 'requesting'
  await nextTick()

  try {
    const media = await navigator.mediaDevices.getUserMedia(CAMERA_PREVIEW_CONSTRAINTS)
    stream.value = media
    phase.value = 'active'
    permissionDenied.value = false

    const attached = await attachStreamToVideo(media)
    if (!attached) {
      localError.value = 'Could not start camera preview. Tap Try again or upload a photo.'
      phase.value = 'blocked'
      emit('error', localError.value)
      return false
    }

    emit('ready')
    return true
  } catch (e) {
    phase.value = 'blocked'
    permissionDenied.value = true
    const msg = cameraErrorMessage(e)
    localError.value = msg
    emit('error', msg)
    return false
  }
}

async function requestCameraAccess() {
  await startCamera()
}

function releaseStream() {
  stream.value?.getTracks().forEach((t) => t.stop())
  stream.value = null
  previewReady.value = false
  const video = videoRef.value
  if (video) {
    video.srcObject = null
  }
}

function capture() {
  const video = videoRef.value
  if (!video || busy.value || phase.value !== 'active' || !previewReady.value) return
  busy.value = true
  try {
    const w = video.videoWidth
    const h = video.videoHeight
    if (!w || !h) {
      busy.value = false
      localError.value = 'Camera is still loading. Wait a moment and try again.'
      emit('error', localError.value)
      return
    }
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('Canvas unavailable')
    ctx.drawImage(video, 0, 0, w, h)
    canvas.toBlob(
      (blob) => {
        busy.value = false
        if (!blob) {
          const msg = 'Could not capture image. Try again or upload from gallery.'
          localError.value = msg
          emit('error', msg)
          return
        }
        if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
        previewUrl.value = URL.createObjectURL(blob)
        const active = stream.value
        stream.value = null
        previewReady.value = false
        if (video) video.srcObject = null
        if (active?.active) returnStreamToPrewarm(active)
        emit('capture', blob)
      },
      'image/jpeg',
      0.92
    )
  } catch (e) {
    busy.value = false
    const msg = e instanceof Error ? e.message : 'Capture failed'
    localError.value = msg
    emit('error', msg)
  }
}

function onFileChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) {
    localError.value = 'Please choose an image file.'
    emit('error', localError.value)
    return
  }
  localError.value = ''
  permissionDenied.value = false
  emit('capture', file)
}

function openGallery() {
  fileInputRef.value?.click()
}

function retake() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = null
  void startCamera()
}

onMounted(() => {
  if (!isCameraSupported()) {
    phase.value = 'blocked'
    localError.value = 'Camera is not supported in this browser. Upload a photo below.'
    return
  }

  void (async () => {
    await prewarmCamera()

    if (hasPrewarmedCamera()) {
      await startCamera()
      return
    }

    const perm = await queryCameraPermission()
    if (perm === 'denied') {
      phase.value = 'blocked'
      permissionDenied.value = true
      localError.value =
        'Camera access is blocked for this site. Allow it in browser settings, or upload a photo below.'
      return
    }
    if (perm === 'granted') {
      await startCamera()
      return
    }
    phase.value = 'prompt'
  })()
})

onUnmounted(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  if (stream.value?.active) {
    returnStreamToPrewarm(stream.value)
    stream.value = null
  } else {
    releaseStream()
  }
  void prewarmCamera()
})

defineExpose({ retake, retryCamera: requestCameraAccess, openGallery })
</script>

<template>
  <div class="camera-container">
    <div v-if="phase === 'prompt'" class="game-camera-prompt">
      <span class="game-camera-prompt__icon" aria-hidden="true">📷</span>
      <div>
        <h3 class="text-lg font-bold">Allow camera access</h3>
        <p class="mt-2 text-sm opacity-85">
          Tick Talk uses your camera only while you take a selfie. Tap below to allow the camera.
        </p>
      </div>
      <button
        type="button"
        class="btn-primary min-h-12 w-full max-w-sm text-base mt-2"
        @click="requestCameraAccess"
      >
        Allow camera access
      </button>
    </div>

    <template v-else>
      <div
        v-if="localError && phase === 'blocked'"
        class="game-alert px-3 py-3 text-sm mb-3"
        role="alert"
      >
        <p class="font-bold">Camera not allowed</p>
        <p class="mt-1 opacity-90">{{ localError }}</p>
      </div>

      <div class="game-camera-frame">
        <video
          ref="videoRef"
          class="h-full w-full scale-x-[-1] object-cover transition-opacity duration-150"
          :class="phase === 'active' && !previewUrl ? 'opacity-100' : 'opacity-0'"
          playsinline
          muted
          autoplay
        />

        <div
          v-if="phase === 'requesting'"
          class="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-gradient-to-b from-slate-900 to-slate-950"
        >
          <div class="game-spinner h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
          <p class="text-xs text-slate-300">Opening camera…</p>
        </div>

        <div
          v-else-if="phase === 'blocked' && !previewUrl"
          class="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-slate-900 px-4 text-center text-slate-400"
        >
          <span class="text-4xl" aria-hidden="true">📷</span>
          <p class="text-sm">No live preview</p>
        </div>

        <img
          v-if="previewUrl"
          :src="previewUrl"
          alt="Selfie preview"
          class="absolute inset-0 h-full w-full object-cover"
        />

        <!-- Shutter Button Overlay -->
        <button
          v-if="phase === 'active' && !previewUrl"
          type="button"
          class="shutter-overlay-btn"
          :disabled="busy || !previewReady"
          @click="capture"
          aria-label="Capture photo"
        >
          <svg viewBox="0 0 24 24" class="shutter-svg" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M14.31 8l5.74 9.94M9.69 8h11.48M7.38 12l5.74-9.94M9.69 16L3.95 6.06M14.31 16H2.83M16.62 12l-5.74 9.94" />
          </svg>
        </button>
      </div>
    </template>

    <input
      ref="fileInputRef"
      type="file"
      accept="image/*"
      class="sr-only"
      aria-hidden="true"
      @change="onFileChange"
    />
  </div>
</template>

<style scoped>
.camera-container {
  width: 100%;
}
.game-camera-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 1rem;
  padding: 1.5rem;
}
.game-camera-frame {
  position: relative;
  margin-left: auto;
  margin-right: auto;
  aspect-ratio: 3 / 4;
  width: 100%;
  overflow: hidden;
  border-radius: 1.5rem; /* Clean rounded camera box */
  border: 4px solid #ffffff;
  background: #000;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
}
.shutter-overlay-btn {
  position: absolute;
  bottom: 1.25rem;
  left: 50%;
  transform: translateX(-50%);
  width: 3.75rem;
  height: 3.75rem;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.25);
  border: 4px solid #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  transition: all 0.2s ease;
  z-index: 10;
}
.shutter-overlay-btn:active {
  transform: translateX(-50%) scale(0.9);
  background-color: rgba(255, 255, 255, 0.45);
}
.shutter-svg {
  width: 2.2rem;
  height: 2.2rem;
}
</style>
