<script setup lang="ts">
import { RouterLink } from 'vue-router'
import AdminIcon from '@/components/admin/AdminIcon.vue'
import { useAdminNav } from '@/composables/useAdminNav'
import { useAdminStore } from '@/stores/admin'

defineProps<{ open: boolean }>()
defineEmits<{ close: [] }>()

const { isEventRoute, mainNav, eventNav, isActive } = useAdminNav()
const admin = useAdminStore()
</script>

<template>
  <aside class="admin-sidebar" aria-label="Admin navigation">
    <div class="admin-sidebar__brand">
      <img src="/select-logo.png" alt="" class="h-7 brightness-0 invert opacity-90" />
      <div>
        <p class="text-sm font-bold text-white">TickTalk</p>
        <p class="text-[0.65rem] text-slate-400">Admin console</p>
      </div>
    </div>

    <nav class="admin-sidebar__nav">
      <div class="admin-sidebar__section">
        <p class="admin-sidebar__section-label">Main</p>
        <RouterLink
          v-for="item in mainNav"
          :key="item.name"
          :to="{ name: item.name }"
          class="admin-sidebar__link"
          :class="{ 'is-active': isActive(item) }"
          @click="$emit('close')"
        >
          <span class="admin-sidebar__icon"><AdminIcon :name="item.icon" /></span>
          {{ item.label }}
        </RouterLink>
      </div>

      <div v-if="isEventRoute" class="admin-sidebar__section">
        <p class="admin-sidebar__section-label">
          {{ admin.currentEvent?.name ?? 'Event' }}
        </p>
        <RouterLink
          v-for="item in eventNav"
          :key="item.name"
          :to="{ name: item.name, params: item.params }"
          class="admin-sidebar__link"
          :class="{ 'is-active': isActive(item) }"
          @click="$emit('close')"
        >
          <span class="admin-sidebar__icon"><AdminIcon :name="item.icon" /></span>
          {{ item.label }}
        </RouterLink>
      </div>
    </nav>
  </aside>
</template>
