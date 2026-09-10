<script setup lang="ts">
import { RouterLink, useRouter } from 'vue-router'
import AdminIcon from '@/components/admin/AdminIcon.vue'
import { useAdminNav } from '@/composables/useAdminNav'
import { useAdminAuthStore } from '@/stores/adminAuth'

defineEmits<{ toggleSidebar: [] }>()

const router = useRouter()
const adminAuth = useAdminAuthStore()
const { breadcrumbs } = useAdminNav()

async function logout() {
  await router.push({ name: 'admin-logout' })
}
</script>

<template>
  <header class="admin-topbar">
    <div class="flex min-w-0 items-center gap-3">
      <button
        type="button"
        class="admin-btn-secondary !min-h-9 !px-2.5 lg:hidden"
        aria-label="Open menu"
        @click="$emit('toggleSidebar')"
      >
        <AdminIcon name="menu" />
      </button>
      <nav class="admin-breadcrumb" aria-label="Breadcrumb">
        <template v-for="(crumb, i) in breadcrumbs" :key="i">
          <span v-if="i > 0" class="admin-breadcrumb__sep">/</span>
          <RouterLink v-if="crumb.to" :to="crumb.to">{{ crumb.label }}</RouterLink>
          <span v-else class="font-medium text-slate-700">{{ crumb.label }}</span>
        </template>
      </nav>
    </div>

    <div class="flex items-center gap-3">
      <div v-if="adminAuth.admin" class="hidden text-right sm:block">
        <p class="text-sm font-semibold text-slate-800">{{ adminAuth.admin.name }}</p>
        <p class="text-xs text-slate-500">{{ adminAuth.roleLabel }}</p>
      </div>
      <button type="button" class="admin-btn-secondary text-sm" @click="logout">
        Sign out
      </button>
    </div>
  </header>
</template>
