<script setup lang="ts">
import { Html5Qrcode } from 'html5-qrcode'
import { onMounted, onUnmounted, ref } from 'vue'

const emit = defineEmits<{
  scan: [payload: string]
  error: [message: string]
}>()

const props = withDefaults(
  defineProps<{
    active?: boolean
  }>(),
  { active: true }
)

const scannerId = `qr-reader-${Math.random().toString(36).slice(2, 9)}`
const scanning = ref(false)
const manualInput = ref('')
let html5Qr: Html5Qrcode | null = null

async function startCamera() {
  if (!props.active || scanning.value) return
  try {
    html5Qr = new Html5Qrcode(scannerId)
    await html5Qr.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 240, height: 240 }, aspectRatio: 1 },
      (decoded) => {
        emit('scan', decoded)
        stopCamera()
      },
      () => {}
    )
    scanning.value = true
  } catch (e) {
    emit('error', e instanceof Error ? e.message : 'Camera access denied')
  }
}

async function stopCamera() {
  if (html5Qr?.isScanning) {
    try {
      await html5Qr.stop()
    } catch {
      /* ignore */
    }
  }
  scanning.value = false
}

function submitManual() {
  const v = manualInput.value.trim()
  if (v) emit('scan', v)
}

onMounted(() => {
  if (props.active) startCamera()
})

onUnmounted(() => {
  stopCamera()
})

defineExpose({ startCamera, stopCamera })
</script>

<template>
  <div class="space-y-4">
    <div
      :id="scannerId"
      class="mx-auto min-h-[260px] w-full max-w-sm overflow-hidden rounded-xl bg-slate-900"
    />
    <p v-if="!scanning" class="text-center text-sm text-slate-400">
      <button type="button" class="text-brand-500 underline" @click="startCamera">
        Enable camera
      </button>
    </p>
    <div class="space-y-2">
      <p class="text-xs text-slate-500">Or paste badge payload</p>
      <input
        v-model="manualInput"
        class="input font-mono text-xs"
        placeholder="ticktalk://badge/v1/..."
        autocomplete="off"
      />
      <button type="button" class="btn-secondary w-full min-h-11" @click="submitManual">
        Use pasted code
      </button>
    </div>
  </div>
</template>
