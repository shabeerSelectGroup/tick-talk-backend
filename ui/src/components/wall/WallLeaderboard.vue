<script setup lang="ts">
import type { LeaderboardEntry } from '@/types'

defineProps<{
  entries: LeaderboardEntry[]
  showScores: boolean
  large?: boolean
}>()

function medal(rank: number) {
  if (rank === 1) return '🥇'
  if (rank === 2) return '🥈'
  if (rank === 3) return '🥉'
  return null
}
</script>

<template>
  <ol class="space-y-2">
    <li
      v-for="entry in entries"
      :key="entry.participant_id"
      class="game-leaderboard-row flex items-center gap-3"
      :class="large ? 'p-4' : 'p-3'"
    >
      <span class="game-leaderboard-rank shrink-0" :class="large ? 'h-12 w-12 text-lg' : ''">
        <span v-if="medal(entry.rank)">{{ medal(entry.rank) }}</span>
        <span v-else>{{ entry.rank }}</span>
      </span>
      <div class="min-w-0 flex-1">
        <p class="truncate font-bold" :class="large ? 'text-lg' : ''">{{ entry.display_name }}</p>
        <p v-if="entry.company" class="truncate text-xs opacity-75">{{ entry.company }}</p>
        <p v-if="entry.tasks_completed != null" class="text-xs opacity-70">
          {{ entry.tasks_completed }} tasks
          <span v-if="entry.is_finished" class="font-semibold text-amber-800"> · finished</span>
        </p>
      </div>
      <span
        v-if="showScores"
        class="shrink-0 font-black text-amber-800"
        :class="large ? 'text-2xl' : 'text-lg'"
      >
        {{ entry.score }}
      </span>
    </li>
    <li v-if="!entries.length" class="game-empty-state py-8 text-center text-sm">
      Rankings appear after someone completes all challenges
    </li>
  </ol>
</template>
