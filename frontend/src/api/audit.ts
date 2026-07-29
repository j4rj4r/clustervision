import client from './client'
import type { AuditLogExportQuery, AuditLogPage, AuditLogQuery } from '../types/audit'

export const auditApi = {
  list: (query: AuditLogQuery): Promise<AuditLogPage> =>
    client.get('/audit', { params: query }).then((r) => r.data),

  export: (query: AuditLogExportQuery): Promise<Blob> =>
    client.get('/audit/export', { params: query, responseType: 'blob' }).then((r) => r.data),
}
