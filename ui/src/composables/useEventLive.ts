import { computed, type Ref } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import type {
  WsEnvelope,
  WsEventLifecycle,
  WsLeaderboardUpdated,
  WsParticipantJoined,
  WsSelfieUploaded,
  WsTaskCompleted,
} from '@/types/ws'

export type EventChannelRole = 'feed' | 'wall' | 'leaderboard' | 'participants'

export function eventChannel(eventId: number, role: EventChannelRole) {
  return `event:${eventId}:${role}`
}

/**
 * Subscribe to live updates for an event (admin feed, wall, participant app).
 */
export function useEventLive(
  eventId: Ref<number | null | undefined>,
  role: EventChannelRole = 'feed',
  options?: {
    extraChannels?: Ref<string[]> | (() => string[])
    onParticipantJoined?: (p: WsParticipantJoined, msg: WsEnvelope) => void
    onTaskCompleted?: (p: WsTaskCompleted, msg: WsEnvelope) => void
    onSelfieUploaded?: (p: WsSelfieUploaded, msg: WsEnvelope) => void
    onLeaderboardUpdated?: (p: WsLeaderboardUpdated, msg: WsEnvelope) => void
    onEventStarted?: (p: WsEventLifecycle, msg: WsEnvelope) => void
    onEventPaused?: (p: WsEventLifecycle, msg: WsEnvelope) => void
    onEventEnded?: (p: WsEventLifecycle, msg: WsEnvelope) => void
    /** Legacy activity envelope from log_activity */
    onActivity?: (payload: unknown, msg: WsEnvelope) => void
  }
) {
  const primary = computed(() => {
    const id = eventId.value
    return id ? eventChannel(id, role) : ''
  })

  const extra = () => {
    const ex = options?.extraChannels
    if (!ex) return [] as string[]
    return typeof ex === 'function' ? ex() : ex.value
  }

  const ws = useWebSocket(() => primary.value, {
    channels: extra,
    onMessage(msg) {
      if (msg.type === 'activity' && options?.onActivity) {
        options.onActivity(msg.payload, msg)
        return
      }
      const p = msg.payload
      switch (msg.type) {
        case 'participant_joined':
          options?.onParticipantJoined?.(p as unknown as WsParticipantJoined, msg)
          break
        case 'task_completed':
          options?.onTaskCompleted?.(p as unknown as WsTaskCompleted, msg)
          break
        case 'selfie_uploaded':
          options?.onSelfieUploaded?.(p as unknown as WsSelfieUploaded, msg)
          break
        case 'leaderboard_updated':
          options?.onLeaderboardUpdated?.(p as unknown as WsLeaderboardUpdated, msg)
          break
        case 'event_started':
          options?.onEventStarted?.(p as unknown as WsEventLifecycle, msg)
          break
        case 'event_paused':
          options?.onEventPaused?.(p as unknown as WsEventLifecycle, msg)
          break
        case 'event_ended':
          options?.onEventEnded?.(p as unknown as WsEventLifecycle, msg)
          break
      }
    },
  })

  return ws
}
