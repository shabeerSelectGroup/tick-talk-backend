export type EventMode = 'networking' | 'competition'
export type EventStatus = 'draft' | 'scheduled' | 'live' | 'ended'

export interface ApiResponse<T> {
  success: boolean
  data: T | null
  error: { code: string; message: string } | null
  meta?: { page?: number; per_page?: number; total?: number }
}

export interface EventPublic {
  id: number
  code: string
  name: string
  description: string | null
  mode: EventMode
  status: EventStatus
  starts_at: string | null
  ends_at: string | null
  capabilities?: import('@/types/eventMode').EventCapabilities
  public_wall_url?: string | null
}

export interface Participant {
  id: number
  event_id: number
  display_name: string
  email: string | null
  company: string | null
  title: string | null
  avatar_url: string | null
  score?: number
  rank?: number | null
  matches_count?: number
  tasks_completed_count?: number
  progress_percent?: number
  all_tasks_completed?: boolean
  leaderboard_available?: boolean
}

export interface ParticipantTask {
  id: number
  task_id: number
  slug?: string | null
  bingo?: boolean
  category?: string | null
  title: string
  description: string | null
  /** Challenge heading for first task in a meet-N group */
  group_label?: string | null
  meet_group_total?: number | null
  meet_group_index?: number | null
  /** Short instruction for the task flow screen */
  instruction?: string | null
  type: string
  target_count?: number
  progress_count?: number
  status: string
  points: number
  completed_at: string | null
  selfie_image_url?: string | null
  selfie_thumbnail_url?: string | null
}

export interface LeaderboardEntry {
  rank: number
  participant_id: number
  display_name: string
  score: number
  company: string | null
  tasks_completed?: number
  matches_count?: number
  finished_at?: string | null
  is_finished?: boolean
}

export interface AwardEntry {
  id: number
  place: number
  award_type: string
  participant_id: number
  display_name: string
  company: string | null
  score: number
  tasks_completed: number
  finished_at: string | null
}

export type { AdminEventDetail as AdminEvent } from '@/types/event'
