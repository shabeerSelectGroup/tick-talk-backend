import type { EventMode, EventPublic, EventStatus, Participant } from '@/types'
import type { EventCapabilities } from '@/types/eventMode'

export interface JoinPreview {
  code: string
  name: string
  description: string | null
  mode: EventMode
  status: EventStatus
  can_join: boolean
  message: string | null
  participant_count: number
  max_participants: number | null
  capabilities?: EventCapabilities | null
  public_wall_url?: string | null
}

export interface JoinResult {
  session_token: string
  event_code: string
  event_id: number
  participant_id: number
  qr_code: string
  qr_payload: string
  qr_code_data_url: string
  resumed: boolean
  participant: Participant
  event?: EventPublic
  capabilities?: EventCapabilities
}
