<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AdminPageHeader from '@/components/admin/AdminPageHeader.vue'
import AdminStatusBadge from '@/components/admin/AdminStatusBadge.vue'
import { useAdminStore } from '@/stores/admin'

const admin = useAdminStore()
const router = useRouter()

onMounted(() => admin.fetchEvents())
</script>

<template>
  <div>
    <AdminPageHeader title="Events" subtitle="Manage all TickTalk events">
      <template #actions>
        <button type="button" class="admin-btn-primary" @click="router.push({ name: 'admin-events-create' })">
          Create event
        </button>
      </template>
    </AdminPageHeader>

    <div class="admin-table-wrap">
      <table class="admin-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Code</th>
            <th>Mode</th>
            <th>Status</th>
            <th>Tasks</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="ev in admin.events"
            :key="ev.id"
            class="admin-table-row--clickable"
            @click="router.push({ name: 'admin-event-detail', params: { id: ev.id } })"
          >
            <td>
              <p class="font-semibold">{{ ev.name }}</p>
            </td>
            <td class="font-mono text-slate-500">{{ ev.code }}</td>
            <td><AdminStatusBadge :status="ev.mode" type="mode" /></td>
            <td><AdminStatusBadge :status="ev.status" /></td>
            <td class="text-slate-600">{{ ev.task_count }}</td>
          </tr>
          <tr v-if="!admin.events.length">
            <td colspan="5" class="admin-empty">No events yet.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
