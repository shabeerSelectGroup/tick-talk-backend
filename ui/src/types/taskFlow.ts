export type TaskFlowStep =
  | 'select'
  | 'scan'
  | 'validated'
  | 'camera'
  | 'uploading'
  | 'progress'
  | 'complete'
  | 'error'

export interface TaskFlowState {
  participant_task_id: number
  task_id: number
  task_type: string
  status: string
  step: string
  partner_id: number | null
  partner_name: string | null
  match_id: number | null
  selfie_id: number | null
  target_count?: number
  progress_count?: number
}

export interface ScanValidation {
  valid: boolean
  partner_id: number
  partner_name: string
  partner_company: string | null
  message: string
}

export interface ScanResult extends ScanValidation {
  match_id: number
  participant_task_id: number
  task_id: number
  requires_selfie: boolean
}

export interface SelfieUploadInfo {
  upload_url: string | null
  storage_key: string
  image_url: string
  thumbnail_url: string | null
  selfie_id: number
  direct_upload: boolean
  match_id: number | null
  metadata?: Record<string, unknown> | null
}

export interface TaskCompleteResult {
  participant_task_id: number
  task_id: number
  status: string
  task_finished?: boolean
  progress_count?: number
  target_count?: number
  message?: string
  points_awarded: number
  base_points?: number
  speed_bonus?: number
  match_id: number | null
  selfie_id: number
  partner_name: string | null
  partner_sign?: string | null
  all_tasks_completed?: boolean
  leaderboard_unlocked?: boolean
}
