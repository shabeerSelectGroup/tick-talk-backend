<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'

const route = useRoute()

const back = computed<{ to: RouteLocationRaw; label: string } | null>(() => {
  const rawId = route.params.id
  const eventId = typeof rawId === 'string' ? Number(rawId) : Number(rawId?.[0])
  const hasEventId = Number.isFinite(eventId) && eventId > 0

  switch (route.name) {
    case 'admin-dashboard':
      return null
    case 'admin-events':
      return { to: { name: 'admin-dashboard' }, label: 'Dashboard' }
    case 'admin-events-create':
      return { to: { name: 'admin-events' }, label: 'Events' }
    case 'admin-event-detail':
      return { to: { name: 'admin-events' }, label: 'Events' }
    case 'admin-event-tasks':
    case 'admin-event-participants':
    case 'admin-event-gallery':
    case 'admin-event-reports':
    case 'admin-event-leaderboard':
      return hasEventId
        ? { to: { name: 'admin-event-detail', params: { id: eventId } }, label: 'Event' }
        : { to: { name: 'admin-events' }, label: 'Events' }
    default:
      return { to: { name: 'admin-dashboard' }, label: 'Dashboard' }
  }
})
</script>

<template>
  <nav v-if="back" class="mb-4">
    <RouterLink
      :to="back.to"
      class="inline-flex min-h-10 items-center gap-1 text-sm font-medium text-brand-500"
    >
      <span aria-hidden="true">←</span>
      Back to {{ back.label }}
    </RouterLink>
  </nav>
</template>
