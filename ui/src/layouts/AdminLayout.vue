<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'
import { computed, ref, watch } from 'vue'
import AdminSidebar from '@/components/admin/AdminSidebar.vue'
import AdminTopbar from '@/components/admin/AdminTopbar.vue'
import { useAdminStore } from '@/stores/admin'
import { useAdminAuthStore } from '@/stores/adminAuth'
import { useAdminNav } from '@/composables/useAdminNav'

const route = useRoute()
const adminAuth = useAdminAuthStore()
const admin = useAdminStore()
const { eventId, isEventRoute } = useAdminNav()

const sidebarOpen = ref(false)

const isAuthPage = computed(() =>
  route.name === 'admin-login' || route.name === 'admin-logout'
)

watch(
  () => route.fullPath,
  () => {
    sidebarOpen.value = false
  }
)

watch(
  [isEventRoute, eventId],
  ([onEvent, id]) => {
    if (onEvent && id && admin.currentEvent?.id !== id) {
      void admin.fetchEvent(id)
    }
  },
  { immediate: true }
)
</script>

<template>
  <!-- Login / logout — centered card, no shell -->
  <div v-if="isAuthPage" class="admin-shell min-h-dvh">
    <main class="flex min-h-dvh items-center justify-center p-4">
      <RouterView v-slot="{ Component }">
        <Transition name="tt-page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
  </div>

  <!-- Sakai-style app shell -->
  <div
    v-else-if="adminAuth.isAuthenticated"
    class="admin-shell"
    :class="{ 'admin-shell--sidebar-open': sidebarOpen }"
  >
    <div
      v-if="sidebarOpen"
      class="admin-overlay lg:hidden"
      aria-hidden="true"
      @click="sidebarOpen = false"
    />
    <AdminSidebar :open="sidebarOpen" @close="sidebarOpen = false" />
    <div class="admin-main">
      <AdminTopbar @toggle-sidebar="sidebarOpen = !sidebarOpen" />
      <main class="admin-content">
        <RouterView v-slot="{ Component }">
          <Transition name="tt-page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>
