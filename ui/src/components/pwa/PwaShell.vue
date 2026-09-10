<script setup lang="ts">
import { usePwa } from '@/composables/usePwa'

const { needRefresh, offline, applyUpdate } = usePwa()
</script>

<template>
  <div
    v-if="offline"
    class="fixed left-0 right-0 top-0 z-[100] bg-amber-600/95 px-4 py-2 text-center text-sm font-medium text-slate-950"
    role="status"
  >
    You're offline — cached pages still work; live data updates when reconnected.
  </div>

  <div
    v-if="needRefresh"
    class="fixed bottom-20 left-4 right-4 z-[100] mx-auto max-w-lg rounded-xl border border-brand-500/40 bg-slate-900 p-4 shadow-xl sm:bottom-6"
  >
    <p class="text-sm font-medium">A new version is available</p>
    <button type="button" class="btn-primary mt-3 w-full min-h-11" @click="applyUpdate">
      Update now
    </button>
  </div>
</template>
