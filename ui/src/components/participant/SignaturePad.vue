<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

const canvasRef = ref<HTMLCanvasElement | null>(null)
const empty = ref(true)

let ctx: CanvasRenderingContext2D | null = null
let drawing = false
let lastX = 0
let lastY = 0
let observer: ResizeObserver | null = null

function cssSize() {
  const canvas = canvasRef.value
  if (!canvas) return { w: 0, h: 0 }
  const rect = canvas.getBoundingClientRect()
  return { w: rect.width, h: rect.height }
}

function fillBackground() {
  const canvas = canvasRef.value
  if (!canvas || !ctx) return
  ctx.save()
  ctx.setTransform(1, 0, 0, 1, 0, 0)
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.restore()
}

function setupContext() {
  const canvas = canvasRef.value
  if (!canvas) return
  ctx = canvas.getContext('2d')
  if (!ctx) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  fillBackground()
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.lineWidth = 2.75
  ctx.strokeStyle = '#0f172a'
}

function resize() {
  const canvas = canvasRef.value
  if (!canvas) return
  const { w, h } = cssSize()
  if (w < 8 || h < 8) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const nextW = Math.floor(w * dpr)
  const nextH = Math.floor(h * dpr)
  if (canvas.width === nextW && canvas.height === nextH) return
  canvas.width = nextW
  canvas.height = nextH
  setupContext()
  empty.value = true
}

function pos(ev: PointerEvent) {
  const canvas = canvasRef.value
  if (!canvas) return { x: 0, y: 0 }
  const rect = canvas.getBoundingClientRect()
  return { x: ev.clientX - rect.left, y: ev.clientY - rect.top }
}

function pointerDown(ev: PointerEvent) {
  if (ev.button !== undefined && ev.button !== 0) return
  ev.preventDefault()
  canvasRef.value?.setPointerCapture(ev.pointerId)
  drawing = true
  const p = pos(ev)
  lastX = p.x
  lastY = p.y
}

function pointerMove(ev: PointerEvent) {
  if (!drawing || !ctx) return
  ev.preventDefault()
  const p = pos(ev)
  ctx.beginPath()
  ctx.moveTo(lastX, lastY)
  ctx.lineTo(p.x, p.y)
  ctx.stroke()
  lastX = p.x
  lastY = p.y
  empty.value = false
}

function pointerUp(ev: PointerEvent) {
  drawing = false
  try {
    canvasRef.value?.releasePointerCapture(ev.pointerId)
  } catch {
    /* already released */
  }
}

function clear() {
  setupContext()
  empty.value = true
}

function toDataURL(): string | null {
  if (empty.value || !canvasRef.value) return null
  return canvasRef.value.toDataURL('image/png')
}

defineExpose({
  clear,
  isEmpty: () => empty.value,
  toDataURL,
})

onMounted(() => {
  resize()
  if (canvasRef.value) {
    observer = new ResizeObserver(() => resize())
    observer.observe(canvasRef.value)
  }
})

onUnmounted(() => {
  observer?.disconnect()
  observer = null
})
</script>

<template>
  <div class="sign-pad">
    <canvas
      ref="canvasRef"
      class="sign-pad__canvas"
      aria-label="Draw a signature"
      @pointerdown="pointerDown"
      @pointermove="pointerMove"
      @pointerup="pointerUp"
      @pointercancel="pointerUp"
      @pointerleave="pointerUp"
    />
    <p v-if="empty" class="sign-pad__hint">Draw signature here</p>
    <button type="button" class="sign-pad__clear" @click="clear">Clear</button>
  </div>
</template>

<style scoped>
.sign-pad {
  position: relative;
  width: 100%;
  margin-bottom: 1rem;
  overflow: hidden;
  border: 2px solid #e2e8f0;
  border-radius: 1rem;
  background: #ffffff;
  box-sizing: border-box;
}
.sign-pad__canvas {
  display: block;
  width: 100%;
  height: 8.5rem;
  touch-action: none;
  cursor: crosshair;
}
.sign-pad__hint {
  position: absolute;
  top: 0.55rem;
  left: 0.85rem;
  margin: 0;
  pointer-events: none;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #94a3b8;
}
.sign-pad__clear {
  position: absolute;
  right: 0.6rem;
  bottom: 0.5rem;
  border: 0;
  background: #f1f5f9;
  border-radius: 999px;
  padding: 0.35rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 800;
  color: #475569;
  cursor: pointer;
}
.sign-pad__clear:active {
  background: #e2e8f0;
}
</style>
