<script setup lang="ts">
import { useEventMode } from '@/composables/useEventMode'

const { isNetworking, isCompetition } = useEventMode()
</script>

<template>
  <span
    class="inline-flex items-center rounded-full border border-amber-500/40 bg-amber-500/20 px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide text-amber-200"
  >
    {{ isNetworking ? 'Networking' : isCompetition ? 'Competition' : 'Event' }}
  </span>
</template>
