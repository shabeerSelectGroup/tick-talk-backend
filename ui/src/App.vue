<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import PwaShell from '@/components/pwa/PwaShell.vue'
import ParticipantLayout from '@/layouts/ParticipantLayout.vue'
import AdminLayout from '@/layouts/AdminLayout.vue'

const route = useRoute()
const layout = computed(() => route.meta.layout as string | undefined)
</script>

<template>
  <PwaShell />
  <ParticipantLayout v-if="layout === 'participant'" />
  <AdminLayout v-else-if="layout === 'admin'" />
  <RouterView v-else v-slot="{ Component }">
    <Transition name="tt-page" mode="out-in">
      <component :is="Component" />
    </Transition>
  </RouterView>
</template>
