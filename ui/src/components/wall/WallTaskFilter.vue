<script setup lang="ts">
import type { WallTask } from '@/types/wall'

defineProps<{
  tasks: WallTask[]
  selectedTaskId: number | null
  large?: boolean
}>()

const emit = defineEmits<{
  select: [taskId: number | null]
}>()
</script>

<template>
  <div class="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
    <button
      type="button"
      class="game-filter-pill shrink-0 px-3 py-1.5 text-sm"
      :class="{ 'game-filter-pill--active': selectedTaskId === null }"
      @click="emit('select', null)"
    >
      All tasks
    </button>
    <button
      v-for="t in tasks"
      :key="t.id"
      type="button"
      class="game-filter-pill shrink-0 px-3 py-1.5 text-sm"
      :class="{ 'game-filter-pill--active': selectedTaskId === t.id }"
      @click="emit('select', t.id)"
    >
      {{ t.title }}
      <span v-if="t.selfie_count" class="ml-1 opacity-70">({{ t.selfie_count }})</span>
    </button>
  </div>
</template>
