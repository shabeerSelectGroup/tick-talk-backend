import type { EventMode, EventStatus } from '@/types'

export interface EventSettingsInput {
  leaderboard_enabled: boolean
  enable_awards: boolean
  show_live_ranking: boolean
  show_ranking_only_at_end: boolean
  enable_selfie_verification: boolean
  enable_public_wall: boolean
  scan_match_points?: number
  task_completion_points?: number
  speed_bonus_enabled?: boolean
  speed_bonus_max_points?: number
  speed_bonus_window_seconds?: number
}

export interface EventSettings extends EventSettingsInput {
  duration_minutes: number | null
  leaderboard_size: number
  task_completion_points?: number
  speed_bonus_enabled?: boolean
  speed_bonus_max_points?: number
  speed_bonus_window_seconds?: number
  selfie_requires_approval: boolean
}

export interface EventCreatePayload {
  name: string
  description?: string | null
  duration_minutes: number
  task_count: number
  mode: EventMode
  timezone?: string
  max_participants?: number | null
  settings: EventSettingsInput
}

export interface EventUpdatePayload {
  name?: string
  description?: string | null
  duration_minutes?: number
  max_participants?: number | null
  settings?: EventSettingsInput
}

export interface AdminEventDetail {
  id: number
  code: string
  name: string
  description: string | null
  mode: EventMode
  status: EventStatus
  starts_at: string | null
  ends_at: string | null
  timezone: string
  max_participants: number | null
  task_count: number
  settings: EventSettings | null
  join_url: string | null
  qr_code_data_url: string | null
  participant_count?: number
  tasks_count?: number
}

export interface EventCreateResult {
  event: AdminEventDetail
  settings: EventSettings
  join_url: string
  qr_code_data_url: string
  tasks_created: number
}
