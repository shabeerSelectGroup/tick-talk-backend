import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api, unwrap } from '@/api/client'
import type { EventPublic, Participant } from '@/types'
import type { EventCapabilities } from '@/types/eventMode'
import { DEFAULT_NETWORKING_CAPABILITIES } from '@/types/eventMode'

export const useEventStore = defineStore('event', () => {
  const event = ref<EventPublic | null>(null)
  const participant = ref<Participant | null>(null)
  const capabilities = ref<EventCapabilities | null>(null)
  const remainingSeconds = ref<number | null>(null)

  const isNetworking = computed(() => event.value?.mode === 'networking')
  const isCompetition = computed(() => event.value?.mode === 'competition')
  const isLive = computed(() => event.value?.status === 'live')

  function inferLeaderboardAvailable(
    ev: EventPublic,
    caps: EventCapabilities | null,
    participantData?: Participant | null
  ): boolean {
    if (participantData?.leaderboard_available !== undefined) {
      return participantData.leaderboard_available
    }
    return ev.mode === 'competition' && (caps?.leaderboard_enabled ?? false)
  }

  const showLeaderboard = computed(() => {
    if (!event.value) return false
    return inferLeaderboardAvailable(event.value, capabilities.value, participant.value)
  })
  const showScores = computed(() => capabilities.value?.scores_enabled ?? isCompetition.value)
  const showTaskPoints = computed(() => capabilities.value?.show_task_points ?? isCompetition.value)
  const showMatchPoints = computed(() => capabilities.value?.show_match_points ?? isCompetition.value)
  const showPublicWall = computed(() => capabilities.value?.public_wall_enabled ?? true)
  const showSelfieVerification = computed(
    () => capabilities.value?.selfie_verification_enabled ?? true
  )
  const publicWallUrl = computed(
    () => capabilities.value?.public_wall_url ?? event.value?.public_wall_url ?? null
  )

  function applySessionPayload(data: {
    participant: Participant
    event: EventPublic
    capabilities?: EventCapabilities
  }) {
    const caps =
      data.capabilities ?? data.event.capabilities ?? inferCapabilities(data.event)
    capabilities.value = caps
    event.value = data.event
    participant.value = {
      ...data.participant,
      leaderboard_available: inferLeaderboardAvailable(data.event, caps, data.participant),
    }
  }

  function inferCapabilities(ev: EventPublic): EventCapabilities {
    if (ev.capabilities) return ev.capabilities
    if (ev.mode === 'networking') return { ...DEFAULT_NETWORKING_CAPABILITIES }
    return {
      ...DEFAULT_NETWORKING_CAPABILITIES,
      mode: 'competition',
      scores_enabled: true,
      rankings_enabled: true,
      leaderboard_enabled: true,
      show_task_points: true,
      show_match_points: true,
    }
  }

  async function fetchPublicEvent(code: string) {
    const data = await unwrap<EventPublic>(await api.get(`/participant/events/${code}`))
    event.value = data
    capabilities.value = inferCapabilities(data)
  }

  async function join(eventCode: string, profile: { display_name: string; email?: string; company?: string }) {
    const { useJoinStore } = await import('@/stores/join')
    return useJoinStore().join(eventCode, profile)
  }

  async function fetchMe() {
    const data = await unwrap<{
      participant: Participant
      event: EventPublic
      capabilities: EventCapabilities
    }>(await api.get('/participant/me'))
    applySessionPayload(data)
  }

  async function fetchTimer() {
    const data = await unwrap<{ remaining_seconds: number | null; status: string }>(
      await api.get('/participant/timer')
    )
    remainingSeconds.value = data.remaining_seconds
  }

  function $reset() {
    event.value = null
    participant.value = null
    capabilities.value = null
    remainingSeconds.value = null
  }

  return {
    event,
    participant,
    capabilities,
    remainingSeconds,
    isNetworking,
    isCompetition,
    isLive,
    showLeaderboard,
    showScores,
    showTaskPoints,
    showMatchPoints,
    showPublicWall,
    showSelfieVerification,
    publicWallUrl,
    fetchPublicEvent,
    applySessionPayload,
    join,
    fetchMe,
    fetchTimer,
    $reset,
  }
})
