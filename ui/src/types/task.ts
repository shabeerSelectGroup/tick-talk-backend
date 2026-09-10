export type TaskType = 'scan' | 'selfie' | 'manual' | 'quiz'

export interface EventTask {
  id: number
  event_id: number
  slug: string
  title: string
  description: string | null
  type: TaskType
  points: number
  sort_order: number
  is_required: boolean
  is_active: boolean
  assigned_count: number
  completed_count: number
  selfie_count: number
}

export interface TaskCreatePayload {
  title: string
  description?: string | null
  type?: TaskType
  points?: number
  is_required?: boolean
  is_active?: boolean
}

export interface BulkImportResult {
  created: number
  skipped_duplicates: number
  tasks: EventTask[]
  errors: string[]
}
