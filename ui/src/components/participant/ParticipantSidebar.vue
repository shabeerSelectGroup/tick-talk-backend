<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import EventModeBadge from '@/components/EventModeBadge.vue'
import EventTimer from '@/components/EventTimer.vue'
import { useEventMode } from '@/composables/useEventMode'
import { useEventStore } from '@/stores/event'
import { useTasksStore } from '@/stores/tasks'

const router = useRouter()
const eventStore = useEventStore()
const tasksStore = useTasksStore()
const { isNetworking, showPublicWall, publicWallUrl } = useEventMode()

onMounted(async () => {
  if (!eventStore.event || !eventStore.participant) {
    await eventStore.fetchMe()
  }
  await eventStore.fetchTimer()
  await tasksStore.fetchTasks()
})

function openWall() {
  if (publicWallUrl.value) window.open(publicWallUrl.value, '_blank')
}
</script>

<template>
  <aside
    class="game-aside flex shrink-0 flex-col gap-4 border-slate-800 p-4 md:w-72 md:border-r md:py-6"
  >
    <header class="space-y-1">
      <div class="flex flex-wrap items-center gap-2">
        <p class="text-sm font-medium text-amber-100/80">{{ eventStore.event?.name }}</p>
        <EventModeBadge />
      </div>
      <h1 class="text-xl font-bold leading-tight text-amber-50 md:text-2xl">
        Hi, {{ eventStore.participant?.display_name ?? 'there' }} 👋
      </h1>
      <p v-if="isNetworking" class="text-sm leading-snug text-amber-400/90">
        Find people who match each bingo prompt — 30 challenges
      </p>
    </header>

    <EventTimer :remaining-seconds="eventStore.remainingSeconds" />

    <div class="grid grid-cols-2 gap-2">
      <button
        type="button"
        class="card py-3 text-left active:scale-[0.98]"
        @click="router.push({ name: 'tasks' })"
      >
        <p class="game-stat">{{ tasksStore.completedCount }}</p>
        <p class="game-stat-label">Tasks done</p>
      </button>
      <button
        type="button"
        class="card py-3 text-left active:scale-[0.98]"
        @click="router.push({ name: 'tasks' })"
      >
        <p class="game-stat">
          {{ tasksStore.tasks.length - tasksStore.completedCount }}
        </p>
        <p class="game-stat-label">Tasks left</p>
      </button>
    </div>

    <div v-if="isNetworking && showPublicWall" class="card">
      <p class="text-sm font-bold">Live wall</p>
      <p class="game-stat-label mt-1">See joins, tasks, and selfies as they happen</p>
      <button type="button" class="btn-secondary mt-3 w-full min-h-11 text-sm" @click="openWall">
        Open live wall
      </button>
    </div>
  </aside>
</template>
