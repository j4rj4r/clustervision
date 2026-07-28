import client from './client'
import type { AuditLogPage, AuditLogQuery } from '../types/audit'

export const auditApi = {
  list: (query: AuditLogQuery): Promise<AuditLogPage> =>
    client.get('/audit', { params: query }).then((r) => r.data),
}
