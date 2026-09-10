import type { EventMode } from '@/types'

export interface EventCapabilities {
  mode: EventMode
  scores_enabled: boolean
  rankings_enabled: boolean
  leaderboard_enabled: boolean
  shared_tasks_enabled: boolean
  selfie_verification_enabled: boolean
  public_wall_enabled: boolean
  analytics_enabled: boolean
  show_task_points: boolean
  show_match_points: boolean
  public_wall_url: string | null
}

export const DEFAULT_NETWORKING_CAPABILITIES: EventCapabilities = {
  mode: 'networking',
  scores_enabled: false,
  rankings_enabled: false,
  leaderboard_enabled: false,
  shared_tasks_enabled: true,
  selfie_verification_enabled: true,
  public_wall_enabled: true,
  analytics_enabled: true,
  show_task_points: false,
  show_match_points: false,
  public_wall_url: null,
}
