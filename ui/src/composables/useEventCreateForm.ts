import { computed, reactive, ref } from 'vue'
import type { EventCreatePayload, EventSettingsInput } from '@/types/event'
import type { EventMode } from '@/types'

/** Default event length when creating (not shown in admin UI). */
const DEFAULT_DURATION_MINUTES = 60

export function useEventCreateForm() {
  const form = reactive({
    name: '',
    duration_minutes: DEFAULT_DURATION_MINUTES,
    task_count: 30,
    mode: 'networking' as EventMode,
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

  const errors = ref<Record<string, string>>({})

  const isCompetition = computed(() => form.mode === 'competition')

  function applyModeDefaults(mode: EventMode) {
    form.mode = mode
    if (mode === 'networking') {
      form.task_count = 30
      form.settings.leaderboard_enabled = false
      form.settings.enable_awards = false
      form.settings.show_live_ranking = false
      form.settings.show_ranking_only_at_end = false
    } else {
      form.task_count = 30
      form.settings.leaderboard_enabled = true
      form.settings.show_live_ranking = true
      form.settings.show_ranking_only_at_end = false
      form.settings.enable_awards = true
      form.settings.task_completion_points = 100
      form.settings.speed_bonus_enabled = true
      form.settings.speed_bonus_max_points = 25 // variable slice of the 100 mark (75–100 pts)
      form.settings.speed_bonus_window_seconds = 300
    }
  }

  function validate(): boolean {
    const e: Record<string, string> = {}
    if (!form.name.trim() || form.name.trim().length < 2) {
      e.name = 'Event name must be at least 2 characters'
    }
    if (form.mode === 'networking') {
      if (form.task_count !== 30) {
        form.task_count = 30
      }
    } else if (form.task_count !== 30) {
      form.task_count = 30
    }
    if (form.settings.show_live_ranking && form.settings.show_ranking_only_at_end) {
      e.settings = 'Choose either live ranking or end-only ranking, not both'
    }
    if (
      isCompetition.value &&
      !form.settings.leaderboard_enabled &&
      (form.settings.show_live_ranking || form.settings.show_ranking_only_at_end)
    ) {
      e.settings = 'Enable leaderboard for ranking display options'
    }
    errors.value = e
    return Object.keys(e).length === 0
  }

  function toPayload(): EventCreatePayload {
    return {
      name: form.name.trim(),
      description: null,
      duration_minutes: form.duration_minutes,
      task_count: form.task_count,
      mode: form.mode,
      settings: { ...form.settings },
    }
  }

  return {
    form,
    errors,
    isCompetition,
    applyModeDefaults,
    validate,
    toPayload,
  }
}
