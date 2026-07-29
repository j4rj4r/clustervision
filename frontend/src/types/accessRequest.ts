export type AccessRequestStatus = 'pending' | 'approved' | 'denied' | 'revoked' | 'expired'

export interface AccessRequest {
  id: string
  requester: string
  target_username: string
  user_kind: 'User' | 'ServiceAccount'
  sa_namespace?: string
  role_name: string
  role_kind: 'ClusterRole' | 'Role'
  namespace?: string
  ttl_minutes: number
  reason: string
  status: AccessRequestStatus
  requested_at: string
  reviewed_by?: string
  reviewed_at?: string
  expires_at?: string
  binding_name?: string
}

export interface AccessRequestCreatePayload {
  target_username: string
  user_kind: 'User' | 'ServiceAccount'
  sa_namespace?: string
  role_name: string
  role_kind: 'ClusterRole' | 'Role'
  namespace?: string
  ttl_minutes: number
  reason: string
}

export interface JitRolePolicy {
  role_kind: 'ClusterRole' | 'Role'
  role_name: string
  eligible: boolean
  max_ttl_minutes: number | null
}

export interface JitRolePolicySetPayload {
  eligible: boolean
  max_ttl_minutes: number | null
}

export interface AccessRequestExportQuery {
  from?: string
  to?: string
}
