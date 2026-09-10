import type { EventMode, EventPublic, EventStatus, LeaderboardEntry } from '@/types'

export interface WallTimer {
  status: EventStatus
  starts_at: string | null
  ends_at: string | null
  remaining_seconds: number | null
}

export interface WallStats {
  mode: EventMode
  status: EventStatus
  participants: number
  connections: number
  tasks_completed: number
  task_total: number
  selfies: number
  leaderboard_enabled: boolean
  leaderboard_visible?: boolean
  finisher_count?: number
  show_scores: boolean
}

export interface WallTask {
  id: number
  slug: string
  title: string
  description: string | null
  type: string
  selfie_count: number
  bingo?: boolean
  category?: string | null
}

export interface WallSelfie {
  id: number
  participant_id: number
  display_name: string
  company: string | null
  task_id: number | null
  task_title: string | null
  image_url: string
  thumbnail_url: string
  uploaded_at: string | null
  status: string
  partner_name?: string | null
  partner_sign?: string | null
  completion_method?: string | null
}

export interface WallPayload {
  event: EventPublic
  timer: WallTimer
  stats: WallStats
  selfies: WallSelfie[]
  leaderboard: LeaderboardEntry[]
}
