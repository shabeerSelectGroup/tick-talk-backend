<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps<{
  remainingSeconds: number | null
  compact?: boolean
}>()

let interval: ReturnType<typeof setInterval> | null = null
const localRemaining = ref(props.remainingSeconds ?? 0)

const formatted = computed(() => {
  const s = Math.max(0, localRemaining.value)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  return `${m}:${String(sec).padStart(2, '0')}`
})

onMounted(() => {
  if (props.remainingSeconds == null) return
  localRemaining.value = props.remainingSeconds
  interval = setInterval(() => {
    if (localRemaining.value > 0) localRemaining.value--
  }, 1000)
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<template>
  <div
    v-if="remainingSeconds != null"
    :class="compact ? 'inline-flex items-center gap-1.5' : 'card flex items-center justify-between'"
  >
    <span :class="compact ? 'text-[0.65rem] font-bold uppercase tracking-wide text-white/70' : 'game-stat-label'">
      {{ compact ? 'Time' : 'Time remaining' }}
    </span>
    <span :class="compact ? 'font-mono text-sm font-bold text-white' : 'game-timer-value'">{{ formatted }}</span>
  </div>
</template>
