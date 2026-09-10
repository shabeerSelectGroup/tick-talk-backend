/** WebSocket event types (mirror backend WsEventType). */
export type WsEventType =
  | 'participant_joined'
  | 'task_completed'
  | 'selfie_uploaded'
  | 'leaderboard_updated'
  | 'event_started'
  | 'event_paused'
  | 'event_ended'
  | 'ping'
  | 'pong'
  | 'subscribed'
  | 'error'

export interface WsEnvelope<T = Record<string, unknown>> {
  id: string
  type: WsEventType | string
  event_id: number
  timestamp: string
  payload: T
}

export interface WsParticipantJoined {
  participant_id: number
  display_name: string
  company: string | null
}

export interface WsTaskCompleted {
  participant_id: number
  task_id: number
  task_title: string
  points: number
  partner_name: string | null
}

export interface WsSelfieUploaded {
  participant_id: number
  selfie_id: number
  task_id: number | null
  match_id: number | null
  thumbnail_url: string | null
  image_url?: string | null
  display_name?: string | null
  task_title?: string | null
}

export interface WsLeaderboardUpdated {
  top: Array<{
    rank: number
    participant_id: number
    display_name: string
    score: number
    company: string | null
    tasks_completed?: number
    finished_at?: string | null
    is_finished?: boolean
  }>
  trigger_participant_id: number | null
}

export interface WsEventLifecycle {
  event_name: string
  mode?: string
  reason?: string | null
  winner?: Record<string, unknown> | null
}
