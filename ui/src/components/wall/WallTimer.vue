<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import type { EventStatus } from '@/types'

const props = defineProps<{
  remainingSeconds: number | null
  status: EventStatus
  large?: boolean
}>()

const local = ref(props.remainingSeconds ?? 0)
let tick: ReturnType<typeof setInterval> | null = null

watch(
  () => props.remainingSeconds,
  (v) => {
    if (v != null) local.value = v
  }
)

const formatted = computed(() => {
  const s = Math.max(0, local.value)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  }
  return `${m}:${String(sec).padStart(2, '0')}`
})

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    live: 'Live',
    scheduled: 'Starting soon',
    ended: 'Ended',
    draft: 'Not started',
  }
  return map[props.status] ?? props.status
})

onMounted(() => {
  if (props.remainingSeconds == null) return
  local.value = props.remainingSeconds
  tick = setInterval(() => {
    if (local.value > 0) local.value--
  }, 1000)
})

onUnmounted(() => {
  if (tick) clearInterval(tick)
})
</script>

<template>
  <div
    class="game-wall-timer flex flex-col items-center px-4 py-3"
    :class="large ? 'py-6' : ''"
  >
    <span
      class="font-bold uppercase tracking-widest"
      :class="[
        large ? 'text-sm' : 'text-xs',
        status === 'live' ? 'text-emerald-400' : 'game-muted',
      ]"
    >
      {{ statusLabel }}
    </span>
    <span
      v-if="remainingSeconds != null"
      class="game-timer-value mt-1 tabular-nums text-brand-400"
      :class="large ? 'text-5xl sm:text-7xl' : 'text-2xl sm:text-3xl'"
    >
      {{ formatted }}
    </span>
    <span v-else class="game-muted mt-1 text-sm">No timer</span>
  </div>
</template>
