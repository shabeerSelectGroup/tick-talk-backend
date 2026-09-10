import { computed } from 'vue'
import { useEventStore } from '@/stores/event'
import {
  DEFAULT_NETWORKING_CAPABILITIES,
  type EventCapabilities,
} from '@/types/eventMode'

export function useEventMode() {
  const eventStore = useEventStore()

  const capabilities = computed<EventCapabilities>(() => {
    const c = eventStore.event?.capabilities
    if (c) return c
    if (eventStore.event?.mode === 'networking') return DEFAULT_NETWORKING_CAPABILITIES
    return {
      ...DEFAULT_NETWORKING_CAPABILITIES,
      mode: 'competition',
      scores_enabled: true,
      rankings_enabled: true,
      leaderboard_enabled: true,
      show_task_points: true,
      show_match_points: true,
    }
  })

  const isNetworking = computed(
    () => eventStore.isNetworking || capabilities.value.mode === 'networking'
  )
  const isCompetition = computed(() => !isNetworking.value)
  const showLeaderboard = computed(
    () => capabilities.value.leaderboard_enabled && eventStore.event?.mode === 'competition'
  )
  const showScores = computed(() => capabilities.value.scores_enabled)
  const showTaskPoints = computed(() => capabilities.value.show_task_points)
  const showMatchPoints = computed(() => capabilities.value.show_match_points)
  const showPublicWall = computed(() => capabilities.value.public_wall_enabled)
  const showSelfieVerification = computed(() => capabilities.value.selfie_verification_enabled)
  const publicWallUrl = computed(
    () => capabilities.value.public_wall_url ?? eventStore.event?.public_wall_url ?? null
  )

  /** Scheduled and live events allow task completion (matches join + manual tasks). */
  const canCompleteTasks = computed(() => {
    const s = eventStore.event?.status
    return s === 'live' || s === 'scheduled'
  })

  return {
    capabilities,
    isNetworking,
    isCompetition,
    showLeaderboard,
    showScores,
    showTaskPoints,
    showMatchPoints,
    showPublicWall,
    showSelfieVerification,
    publicWallUrl,
    canCompleteTasks,
  }
}
