<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { AdminEventDetail, EventSettingsInput, EventUpdatePayload } from '@/types/event'

const props = defineProps<{
  open: boolean
  event: AdminEventDetail | null
  saving?: boolean
}>()

const emit = defineEmits<{
  close: []
  save: [payload: EventUpdatePayload]
}>()

const form = reactive({
  name: '',
  description: '',
  duration_minutes: 60,
  max_participants: null as number | null,
  settings: {
    leaderboard_enabled: false,
    enable_awards: false,
    show_live_ranking: false,
    show_ranking_only_at_end: false,
    enable_selfie_verification: true,
    enable_public_wall: true,
    scan_match_points: 10,
    task_completion_points: 100,
    speed_bonus_enabled: false,
    speed_bonus_max_points: 25,
    speed_bonus_window_seconds: 300,
  } as EventSettingsInput,
})

const error = ref('')
const isCompetition = computed(() => props.event?.mode === 'competition')

function loadFromEvent(ev: AdminEventDetail) {
  form.name = ev.name
  form.description = ev.description ?? ''
  form.duration_minutes = ev.settings?.duration_minutes ?? 60
  form.max_participants = ev.max_participants
  if (ev.settings) {
    form.settings = {
      leaderboard_enabled: ev.settings.leaderboard_enabled,
      enable_awards: ev.settings.enable_awards,
      show_live_ranking: ev.settings.show_live_ranking,
      show_ranking_only_at_end: ev.settings.show_ranking_only_at_end,
      enable_selfie_verification: ev.settings.enable_selfie_verification,
      enable_public_wall: ev.settings.enable_public_wall,
      scan_match_points: ev.settings.scan_match_points ?? 10,
      task_completion_points: ev.settings.task_completion_points ?? 100,
      speed_bonus_enabled: ev.settings.speed_bonus_enabled ?? false,
      speed_bonus_max_points: ev.settings.speed_bonus_max_points ?? 25,
      speed_bonus_window_seconds: ev.settings.speed_bonus_window_seconds ?? 300,
    }
  }
}

watch(
  () => [props.open, props.event] as const,
  ([open, ev]) => {
    if (!open || !ev) return
    error.value = ''
    loadFromEvent(ev)
  }
)

function validate(): boolean {
  if (!form.name.trim() || form.name.trim().length < 2) {
    error.value = 'Event name must be at least 2 characters'
    return false
  }
  if (form.settings.show_live_ranking && form.settings.show_ranking_only_at_end) {
    error.value = 'Choose either live ranking or end-only ranking, not both'
    return false
  }
  if (
    isCompetition.value &&
    !form.settings.leaderboard_enabled &&
    (form.settings.show_live_ranking || form.settings.show_ranking_only_at_end)
  ) {
    error.value = 'Enable leaderboard for ranking display options'
    return false
  }
  error.value = ''
  return true
}

function submit() {
  if (!validate()) return
  const payload: EventUpdatePayload = {
    name: form.name.trim(),
    description: form.description.trim() || null,
    duration_minutes: form.duration_minutes,
    max_participants:
      form.max_participants != null && form.max_participants > 0
        ? form.max_participants
        : null,
    settings: { ...form.settings },
  }
  emit('save', payload)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open && event" class="admin-shell">
      <div class="admin-modal-backdrop" @click.self="emit('close')">
        <div class="admin-modal max-h-[90vh] max-w-2xl overflow-y-auto p-0" role="dialog">
          <header class="sticky top-0 z-10 border-b border-slate-200 bg-white px-5 py-4">
            <h2 class="text-lg font-bold">Edit event</h2>
            <p class="admin-muted mt-0.5">
              Code <span class="font-mono font-semibold">{{ event.code }}</span> cannot be changed.
            </p>
          </header>

          <form class="space-y-0 p-5" @submit.prevent="submit">
            <div class="space-y-4">
              <div>
                <label for="edit-name" class="admin-label">Event name *</label>
                <input id="edit-name" v-model="form.name" class="admin-input" required />
              </div>
              <div>
                <label for="edit-desc" class="admin-label">Description</label>
                <textarea
                  id="edit-desc"
                  v-model="form.description"
                  class="admin-input min-h-20 resize-none"
                  placeholder="Optional description for participants"
                />
              </div>
              <div class="grid gap-4 sm:grid-cols-2">
                <div>
                  <label for="edit-duration" class="admin-label">Duration (minutes)</label>
                  <input
                    id="edit-duration"
                    v-model.number="form.duration_minutes"
                    type="number"
                    min="15"
                    max="10080"
                    class="admin-input"
                  />
                </div>
                <div>
                  <label for="edit-max" class="admin-label">Max participants</label>
                  <input
                    id="edit-max"
                    v-model.number="form.max_participants"
                    type="number"
                    min="1"
                    class="admin-input"
                    placeholder="No limit"
                  />
                </div>
              </div>
            </div>

            <section class="mt-6 border-t border-slate-200 pt-5">
              <h3 class="mb-4 font-semibold">Settings</h3>
              <div class="space-y-3">
                <label
                  class="flex items-center justify-between gap-4"
                  :class="{ 'opacity-50': !isCompetition }"
                >
                  <span class="text-sm">Enable leaderboard</span>
                  <input
                    v-model="form.settings.leaderboard_enabled"
                    type="checkbox"
                    class="h-5 w-5 rounded"
                    :disabled="!isCompetition"
                  />
                </label>
                <label
                  class="flex items-center justify-between gap-4"
                  :class="{ 'opacity-50': !isCompetition }"
                >
                  <span class="text-sm">Enable awards</span>
                  <input
                    v-model="form.settings.enable_awards"
                    type="checkbox"
                    class="h-5 w-5 rounded"
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
                    class="h-5 w-5 rounded"
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
                    class="h-5 w-5 rounded"
                    :disabled="!isCompetition || !form.settings.leaderboard_enabled"
                    @change="form.settings.show_live_ranking = false"
                  />
                </label>
                <label class="flex items-center justify-between gap-4">
                  <span class="text-sm">Enable selfie verification</span>
                  <input
                    v-model="form.settings.enable_selfie_verification"
                    type="checkbox"
                    class="h-5 w-5 rounded"
                  />
                </label>
                <label class="flex items-center justify-between gap-4">
                  <span class="text-sm">Enable public wall</span>
                  <input
                    v-model="form.settings.enable_public_wall"
                    type="checkbox"
                    class="h-5 w-5 rounded"
                  />
                </label>

                <template v-if="isCompetition">
                  <div>
                    <label class="admin-label">Mark per task (max)</label>
                    <input
                      v-model.number="form.settings.task_completion_points"
                      type="number"
                      min="1"
                      max="100"
                      class="admin-input w-32"
                    />
                  </div>
                  <div>
                    <label class="admin-label">Bonus points per standalone scan</label>
                    <input
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
                      class="h-5 w-5 rounded"
                    />
                  </label>
                  <div
                    v-if="form.settings.speed_bonus_enabled"
                    class="grid gap-3 sm:grid-cols-2"
                  >
                    <div>
                      <label class="admin-label">Speed range (pts)</label>
                      <input
                        v-model.number="form.settings.speed_bonus_max_points"
                        type="number"
                        min="0"
                        :max="(form.settings.task_completion_points ?? 100) - 1"
                        class="admin-input"
                      />
                    </div>
                    <div>
                      <label class="admin-label">Bonus window (seconds)</label>
                      <input
                        v-model.number="form.settings.speed_bonus_window_seconds"
                        type="number"
                        min="30"
                        max="3600"
                        class="admin-input"
                      />
                    </div>
                  </div>
                </template>
              </div>
            </section>

            <p v-if="error" class="admin-alert admin-alert--error mt-4">{{ error }}</p>

            <div class="mt-6 flex gap-2 border-t border-slate-200 pt-4">
              <button type="button" class="admin-btn-secondary flex-1" @click="emit('close')">
                Cancel
              </button>
              <button type="submit" class="admin-btn-primary flex-1" :disabled="saving">
                {{ saving ? 'Saving…' : 'Save changes' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </Teleport>
</template>
