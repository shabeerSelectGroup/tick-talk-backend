<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AdminPageHeader from '@/components/admin/AdminPageHeader.vue'
import AdminStatusBadge from '@/components/admin/AdminStatusBadge.vue'
import { useAdminStore } from '@/stores/admin'
import { useAdminAuthStore } from '@/stores/adminAuth'

const admin = useAdminStore()
const adminAuth = useAdminAuthStore()
const router = useRouter()

onMounted(() => admin.fetchEvents())
</script>

<template>
  <div>
    <AdminPageHeader
      title="Dashboard"
      :subtitle="adminAuth.admin ? `Welcome back, ${adminAuth.admin.name}` : undefined"
    >
      <template #actions>
        <button type="button" class="admin-btn-primary" @click="router.push({ name: 'admin-events-create' })">
          New event
        </button>
      </template>
    </AdminPageHeader>

    <div class="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <button
        type="button"
        class="admin-stat-card admin-stat-card--clickable text-left"
        @click="router.push({ name: 'admin-events' })"
      >
        <p class="admin-stat-value">{{ admin.events.length }}</p>
        <p class="admin-stat-label">Total events</p>
      </button>
      <div class="admin-stat-card">
        <p class="admin-stat-value">{{ admin.events.filter((e) => e.status === 'live').length }}</p>
        <p class="admin-stat-label">Live now</p>
      </div>
      <div class="admin-stat-card">
        <p class="admin-stat-value">{{ admin.events.filter((e) => e.status === 'ended').length }}</p>
        <p class="admin-stat-label">Completed</p>
      </div>
    </div>

    <section class="admin-panel">
      <div class="admin-panel-header">
        <h2 class="admin-panel-title">Recent events</h2>
        <button type="button" class="admin-btn-ghost" @click="router.push({ name: 'admin-events' })">
          View all
        </button>
      </div>
      <div class="admin-table-wrap border-0 shadow-none">
        <table class="admin-table">
          <thead>
            <tr>
              <th>Event</th>
              <th>Code</th>
              <th>Mode</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="ev in admin.events.slice(0, 8)"
              :key="ev.id"
              class="admin-table-row--clickable"
              @click="router.push({ name: 'admin-event-detail', params: { id: ev.id } })"
            >
              <td class="font-semibold">{{ ev.name }}</td>
              <td class="font-mono text-slate-500">{{ ev.code }}</td>
              <td><AdminStatusBadge :status="ev.mode" type="mode" /></td>
              <td><AdminStatusBadge :status="ev.status" /></td>
            </tr>
            <tr v-if="!admin.events.length">
              <td colspan="4" class="admin-empty">No events yet. Create your first event.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
