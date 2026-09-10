export type AdminRole = 'super_admin'

export interface AdminUser {
  id: number
  email: string
  name: string
  role: AdminRole
  is_active: boolean
  last_login_at: string | null
}

export interface AdminLoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  admin: AdminUser
}

export interface AdminRefreshResponse {
  access_token: string
  refresh_token: string
  token_type: string
}
