<script setup lang="ts">
import type { WallStats } from '@/types/wall'

defineProps<{
  stats: WallStats
  large?: boolean
}>()
</script>

<template>
  <div
    class="grid gap-3"
    :class="large ? 'grid-cols-2 gap-4 sm:grid-cols-4' : 'grid-cols-2 sm:grid-cols-4'"
  >
    <div class="game-wall-stat px-3 py-3 text-center">
      <p class="game-stat" :class="large ? 'text-4xl' : 'text-2xl'">{{ stats.participants }}</p>
      <p class="game-stat-label uppercase tracking-wide" :class="large ? 'text-sm' : ''">Participants</p>
    </div>
    <div class="game-wall-stat px-3 py-3 text-center">
      <p class="game-stat" :class="large ? 'text-4xl' : 'text-2xl'">
        {{ stats.mode === 'networking' ? stats.connections : stats.tasks_completed }}
      </p>
      <p class="game-stat-label uppercase tracking-wide" :class="large ? 'text-sm' : ''">
        {{ stats.mode === 'networking' ? 'Connections' : 'Tasks done' }}
      </p>
    </div>
    <div class="game-wall-stat px-3 py-3 text-center">
      <p class="game-stat" :class="large ? 'text-4xl' : 'text-2xl'">{{ stats.selfies }}</p>
      <p class="game-stat-label uppercase tracking-wide" :class="large ? 'text-sm' : ''">Selfies</p>
    </div>
    <div class="game-wall-stat px-3 py-3 text-center">
      <p class="game-stat capitalize" :class="large ? 'text-2xl' : 'text-lg'">{{ stats.status }}</p>
      <p class="game-stat-label uppercase tracking-wide" :class="large ? 'text-sm' : ''">Status</p>
    </div>
  </div>
</template>
