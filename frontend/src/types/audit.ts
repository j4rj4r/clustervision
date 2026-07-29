export interface AuditLogEntry {
  id: string
  timestamp: string
  actor: string | null
  actor_role: string | null
  method: string
  path: string
  status_code: number
  payload: Record<string, unknown> | null
}

export interface AuditLogPage {
  items: AuditLogEntry[]
  total: number
}

export interface AuditLogQuery {
  limit: number
  offset: number
  actor?: string
  path_contains?: string
}

export interface AuditLogExportQuery {
  from?: string
  to?: string
  actor?: string
  path_contains?: string
}
