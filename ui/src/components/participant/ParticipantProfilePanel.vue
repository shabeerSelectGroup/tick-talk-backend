<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useEventStore } from '@/stores/event'

const router = useRouter()
const auth = useAuthStore()
const eventStore = useEventStore()

function leave() {
  auth.clearSession()
  router.replace({ name: 'join' })
}
</script>

<template>
  <aside
    class="game-aside flex shrink-0 flex-col gap-4 border-slate-800 p-4 md:w-64 md:border-l md:py-6 lg:w-72"
  >
    <h2 class="text-sm font-bold uppercase tracking-wider text-amber-500/80">Profile</h2>

    <div class="card space-y-3">
      <div>
        <p class="game-stat-label">Name</p>
        <p class="text-lg font-bold">{{ eventStore.participant?.display_name }}</p>
      </div>
      <div>
        <p class="game-stat-label">Event</p>
        <p class="text-sm leading-snug">
          {{ eventStore.event?.name }}
          <span v-if="eventStore.event?.code" class="font-mono font-bold text-amber-800">
            ({{ eventStore.event.code }})
          </span>
        </p>
      </div>
      <div>
        <p class="game-stat-label">Participant ID</p>
        <p class="game-stat font-mono text-base">#{{ auth.participantId }}</p>
      </div>
    </div>

    <button type="button" class="btn-secondary w-full min-h-12 text-sm" @click="leave">
      Leave event (let someone else use this device)
    </button>
  </aside>
</template>
