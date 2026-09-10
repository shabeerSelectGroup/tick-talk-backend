<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
  type?: 'status' | 'mode'
}>()

const badgeClass = computed(() => {
  const s = props.status.toLowerCase()
  if (props.type === 'mode') {
    return s === 'competition' ? 'admin-badge--competition' : 'admin-badge--networking'
  }
  if (s === 'live') return 'admin-badge--live'
  if (s === 'ended') return 'admin-badge--ended'
  if (s === 'draft') return 'admin-badge--draft'
  return 'admin-badge--scheduled'
})
</script>

<template>
  <span class="admin-badge" :class="badgeClass">{{ status }}</span>
</template>
