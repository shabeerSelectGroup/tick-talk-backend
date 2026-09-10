export interface ParticipantBadge {
  participant_id: number
  event_id: number
  event_code: string
  display_name: string
  company: string | null
  secure_token: string
  qr_token: string
  qr_payload: string
  qr_code_data_url: string
  version: string
}

export interface BadgeValidation {
  valid: boolean
  participant_id: number | null
  event_id: number | null
  display_name: string | null
  company: string | null
  error_code: string | null
  message: string | null
}
