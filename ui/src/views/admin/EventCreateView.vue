<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AdminPageHeader from '@/components/admin/AdminPageHeader.vue'
import { useEventCreateForm } from '@/composables/useEventCreateForm'
import { useAdminStore } from '@/stores/admin'
import { getErrorMessage } from '@/utils/errors'

const router = useRouter()
const admin = useAdminStore()
const { form, errors, isCompetition, applyModeDefaults, validate, toPayload } =
  useEventCreateForm()

const loading = ref(false)
const submitError = ref('')
const createdCode = ref('')

async function submit() {
  submitError.value = ''
  if (!validate()) return

  loading.value = true
  try {
    const result = await admin.createEvent(toPayload())
    createdCode.value = result.event.code
    router.push({ name: 'admin-event-detail', params: { id: result.event.id } })
  } catch (e) {
    submitError.value = getErrorMessage(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-3xl">
    <AdminPageHeader
      title="Create event"
      subtitle="Event code, join URL, and QR code are generated automatically."
    />

    <form class="space-y-6" @submit.prevent="submit">
      <section class="admin-panel">
        <div class="admin-panel-header">
          <h2 class="admin-panel-title">Event details</h2>
        </div>
        <div class="admin-panel-body space-y-4">
        <div>
          <label for="name" class="admin-label">Event name *</label>
          <input id="name" v-model="form.name" class="admin-input" placeholder="Annual Team Summit" required />
          <p v-if="errors.name" class="mt-1 text-sm text-red-600">{{ errors.name }}</p>
        </div>

        <div>
          <label class="admin-label">Event mode *</label>
          <div class="mt-2 grid grid-cols-2 gap-3">
            <button
              type="button"
              class="mode-button"
              :class="{ 'is-active': form.mode === 'networking' }"
              @click="applyModeDefaults('networking')"
            >
              <span class="mode-title">Networking</span>
              <span class="mode-desc">No scores or leaderboard</span>
            </button>
            <button
              type="button"
              class="mode-button"
              :class="{ 'is-active': form.mode === 'competition' }"
              @click="applyModeDefaults('competition')"
            >
              <span class="mode-title">Competition</span>
              <span class="mode-desc">Scores, rankings & awards</span>
            </button>
          </div>
        </div>
        </div>
      </section>

      <section class="admin-panel">
        <div class="admin-panel-header">
          <h2 class="admin-panel-title">Settings</h2>
        </div>
        <div class="admin-panel-body space-y-4">
        <p v-if="errors.settings" class="admin-alert admin-alert--error">{{ errors.settings }}</p>

        <label
          class="flex items-center justify-between gap-4"
          :class="{ 'opacity-50': !isCompetition }"
        >
          <span class="text-sm">Enable leaderboard</span>
          <input
            v-model="form.settings.leaderboard_enabled"
            type="checkbox"
            class="h-5 w-5 rounded border-slate-600"
            :disabled="!isCompetition"
          />
        </label>

        <label class="flex items-center justify-between gap-4" :class="{ 'opacity-50': !isCompetition }">
          <span class="text-sm">Enable awards</span>
          <input
            v-model="form.settings.enable_awards"
            type="checkbox"
            class="h-5 w-5 rounded border-slate-600"
            :disabled="!isCompetition"
          />
        </label>

        <label
          class="flex items-center justify-between gap-4"
          :class="{ 'opacity-50': !isCompetition || !form.settings.leaderboard_enabled }"
        >
          <span class="text-sm">Show live ranking</span>
          <input
            v-model="form.settings.show_live_ranking"
            type="checkbox"
            class="h-5 w-5 rounded border-slate-600"
            :disabled="!isCompetition || !form.settings.leaderboard_enabled"
            @change="form.settings.show_ranking_only_at_end = false"
          />
        </label>

        <label
          class="flex items-center justify-between gap-4"
          :class="{ 'opacity-50': !isCompetition || !form.settings.leaderboard_enabled }"
        >
          <span class="text-sm">Show ranking only at end</span>
          <input
            v-model="form.settings.show_ranking_only_at_end"
            type="checkbox"
            class="h-5 w-5 rounded border-slate-600"
            :disabled="!isCompetition || !form.settings.leaderboard_enabled"
            @change="form.settings.show_live_ranking = false"
          />
        </label>

        <label class="flex items-center justify-between gap-4">
          <span class="text-sm">Enable selfie verification</span>
          <input
            v-model="form.settings.enable_selfie_verification"
            type="checkbox"
            class="h-5 w-5 rounded border-slate-600"
          />
        </label>

        <label class="flex items-center justify-between gap-4">
          <span class="text-sm">Enable public wall</span>
          <input
            v-model="form.settings.enable_public_wall"
            type="checkbox"
            class="h-5 w-5 rounded border-slate-600"
          />
        </label>

        <template v-if="isCompetition">
          <div>
            <label for="task_pts" class="admin-label">Mark per task (max)</label>
            <input
              id="task_pts"
              v-model.number="form.settings.task_completion_points"
              type="number"
              min="1"
              max="100"
              class="admin-input w-32"
            />
            <p class="mt-1 text-xs text-slate-500">100 = full marks per challenge (speed adjusts within this cap)</p>
          </div>
          <div>
            <label for="points" class="admin-label">Bonus points per standalone scan</label>
            <input
              id="points"
              v-model.number="form.settings.scan_match_points"
              type="number"
              min="0"
              max="1000"
              class="admin-input w-32"
            />
          </div>
          <label class="flex items-center justify-between gap-4">
            <span class="text-sm">Enable speed bonus</span>
            <input
              v-model="form.settings.speed_bonus_enabled"
              type="checkbox"
              class="h-5 w-5 rounded border-slate-600"
            />
          </label>
          <div v-if="form.settings.speed_bonus_enabled" class="grid gap-3 sm:grid-cols-2">
            <div>
              <label class="admin-label">Speed range (pts within mark)</label>
              <input
                v-model.number="form.settings.speed_bonus_max_points"
                type="number"
                min="0"
                :max="(form.settings.task_completion_points ?? 100) - 1"
                class="admin-input w-full"
              />
            </div>
            <div>
              <label class="admin-label">Bonus window (seconds)</label>
              <input
                v-model.number="form.settings.speed_bonus_window_seconds"
                type="number"
                min="30"
                max="3600"
                class="admin-input w-full"
              />
            </div>
          </div>
        </template>
        </div>
      </section>

      <p v-if="submitError" class="admin-alert admin-alert--error" role="alert">{{ submitError }}</p>

      <div class="flex gap-3">
        <button type="button" class="admin-btn-secondary flex-1" @click="router.push({ name: 'admin-events' })">
          Cancel
        </button>
        <button type="submit" class="admin-btn-primary flex-1" :disabled="loading">
          {{ loading ? 'Creating…' : 'Create event' }}
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.mode-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 1.25rem 1rem;
  border-radius: 1rem;
  border: 2px solid #e2e8f0;
  background-color: #f8fafc;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease-in-out;
  font-family: inherit;
  width: 100%;
}

.mode-button:hover {
  background-color: #f1f5f9;
  border-color: #cbd5e1;
  color: #1e293b;
}

/* Active State */
.mode-button.is-active {
  background-color: #6366f1;
  border-color: #6366f1;
  color: #ffffff !important;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
}

.mode-title {
  font-size: 1rem;
  font-weight: 800;
  margin: 0;
  transition: color 0.2s;
  color: inherit;
}

.mode-button.is-active .mode-title {
  color: #ffffff !important;
}

.mode-desc {
  font-size: 0.75rem;
  margin-top: 0.25rem;
  font-weight: 400;
  opacity: 0.85;
  color: inherit;
}

.mode-button.is-active .mode-desc {
  color: rgba(255, 255, 255, 0.9) !important;
}
</style>
